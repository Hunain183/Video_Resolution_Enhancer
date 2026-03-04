"""
Video Processing Pipeline
Main orchestrator for AI video enhancement
"""

import os
import shutil
import time
import uuid
from pathlib import Path
from typing import Optional, Callable, Dict, Any, Tuple
import logging

from .ffmpeg_utils import (
    get_video_info,
    extract_frames,
    extract_audio,
    reassemble_video,
    apply_filters,
    optimize_for_loop
)
from .upscaler import create_upscaler
from .interpolator import create_interpolator, FFmpegInterpolator

logger = logging.getLogger(__name__)


# Resolution presets
RESOLUTION_PRESETS = {
    "original": None,
    "1080p": (1920, 1080),
    "1440p": (2560, 1440),
    "4k": (3840, 2160)
}

# Bitrate presets
BITRATE_PRESETS = {
    "1080p": "18M",
    "1440p": "28M",
    "4k": "45M"
}

# FPS presets
FPS_PRESETS = {
    "original": None,
    "60": 60.0,
    "120": 120.0
}


class VideoPipeline:
    """
    Main video enhancement pipeline.
    
    Orchestrates:
    1. Frame extraction
    2. AI upscaling (Real-ESRGAN)
    3. Frame interpolation (RIFE)
    4. Video reassembly with filters
    5. Loop optimization
    """
    
    def __init__(
        self,
        job_id: str,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        models_dir: str = "./models",
        temp_dir: str = "./temp"
    ):
        """
        Initialize pipeline.
        
        Args:
            job_id: Unique job identifier
            progress_callback: Callback(progress, step_name) for updates
            models_dir: Directory for AI models
            temp_dir: Directory for temporary files
        """
        self.job_id = job_id
        self.progress_callback = progress_callback
        self.models_dir = models_dir
        self.temp_dir = Path(temp_dir)
        
        # Create job-specific temp directory
        self.job_temp_dir = self.temp_dir / f"job_{job_id}"
        self.job_temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Processing stages
        self.stages = {
            "extract": {"weight": 10, "name": "Extracting frames"},
            "upscale": {"weight": 50, "name": "AI upscaling"},
            "interpolate": {"weight": 25, "name": "Frame interpolation"},
            "reassemble": {"weight": 10, "name": "Reassembling video"},
            "filters": {"weight": 3, "name": "Applying filters"},
            "optimize": {"weight": 2, "name": "Loop optimization"}
        }
        
        self.current_stage = None
        self.stage_progress = 0
        
    def _update_progress(self, stage_progress: float):
        """Update progress for current stage."""
        if not self.progress_callback or not self.current_stage:
            return
        
        self.stage_progress = stage_progress
        
        # Calculate weighted progress
        completed_weight = 0
        for stage, info in self.stages.items():
            if stage == self.current_stage:
                break
            completed_weight += info["weight"]
        
        current_weight = self.stages[self.current_stage]["weight"]
        overall_progress = completed_weight + (current_weight * stage_progress / 100)
        
        # Normalize to 100
        total_weight = sum(s["weight"] for s in self.stages.values())
        overall_progress = (overall_progress / total_weight) * 100
        
        self.progress_callback(overall_progress, self.stages[self.current_stage]["name"])
    
    def _set_stage(self, stage: str):
        """Set current processing stage."""
        self.current_stage = stage
        self.stage_progress = 0
        
        if self.progress_callback:
            self.progress_callback(self.stage_progress, self.stages[stage]["name"])
        
        logger.info(f"Pipeline stage: {stage}")
    
    def process(
        self,
        input_path: str,
        output_dir: str,
        resolution: str = "original",
        upscale_factor: int = 2,
        upscaler_algorithm: str = "realesrgan",
        target_fps: str = "original",
        denoise: bool = False,
        sharpen: bool = False,
        loop_optimize: bool = False
    ) -> Dict[str, Any]:
        """
        Process video through the enhancement pipeline.
        
        Args:
            input_path: Path to input video
            output_dir: Directory for output video
            resolution: Target resolution preset
            upscale_factor: Upscale factor (2 or 4)
            upscaler_algorithm: Upscaling algorithm (realesrgan or lanczos)
            target_fps: Target FPS preset
            denoise: Enable denoising
            sharpen: Enable sharpening
            loop_optimize: Optimize for seamless looping
        
        Returns:
            Dictionary with processing results
        """
        start_time = time.time()
        
        try:
            # Get input video info
            video_info = get_video_info(input_path)
            logger.info(f"Input: {video_info['width']}x{video_info['height']} @ {video_info['fps']}fps")
            
            # Determine target resolution
            target_resolution = RESOLUTION_PRESETS.get(resolution)
            if target_resolution is None and resolution != "original":
                target_resolution = RESOLUTION_PRESETS.get("1080p")
            
            # Determine target FPS
            target_fps_value = FPS_PRESETS.get(target_fps)
            needs_interpolation = target_fps_value is not None and target_fps_value > video_info["fps"]
            
            # Determine if upscaling is needed
            needs_upscaling = upscale_factor > 1
            use_ai_upscaling = needs_upscaling and upscaler_algorithm == "realesrgan"

            # Lanczos target resolution when user picks upscale factor with "original" resolution
            direct_target_resolution = target_resolution
            if upscaler_algorithm == "lanczos" and needs_upscaling and target_resolution is None:
                direct_target_resolution = (
                    int(video_info["width"] * upscale_factor),
                    int(video_info["height"] * upscale_factor)
                )
            
            # Create temp directories
            frames_dir = self.job_temp_dir / "frames"
            upscaled_dir = self.job_temp_dir / "upscaled"
            interpolated_dir = self.job_temp_dir / "interpolated"
            
            # Extract audio
            audio_path = self.job_temp_dir / "audio.aac"
            has_audio = extract_audio(input_path, str(audio_path))
            
            current_frames_dir = None
            current_fps = video_info["fps"]
            
            # Stage 1: Extract frames (only if doing frame-level processing)
            if use_ai_upscaling:
                self._set_stage("extract")
                extract_frames(
                    input_path,
                    str(frames_dir),
                    None,  # Keep original FPS
                    lambda p: self._update_progress(p)
                )
                current_frames_dir = frames_dir
            
            # Stage 2: AI Upscaling
            if use_ai_upscaling:
                self._set_stage("upscale")
                
                upscaler = create_upscaler(
                    model_name="realesrgan-x4plus-anime",
                    models_dir=self.models_dir,
                    use_gpu=True
                )
                
                try:
                    upscaler.upscale_frames(
                        str(current_frames_dir),
                        str(upscaled_dir),
                        target_factor=upscale_factor,
                        progress_callback=lambda p: self._update_progress(p)
                    )
                    current_frames_dir = upscaled_dir
                finally:
                    upscaler.cleanup()
            
            # Stage 3: Frame Interpolation
            if needs_interpolation:
                self._set_stage("interpolate")
                
                if use_ai_upscaling and current_frames_dir:
                    # Frame-based interpolation
                    interpolator = create_interpolator(
                        models_dir=self.models_dir,
                        use_gpu=True,
                        use_ffmpeg=False
                    )
                    
                    fps_multiplier = target_fps_value / current_fps
                    
                    try:
                        frame_count, actual_mult = interpolator.interpolate_frames(
                            str(current_frames_dir),
                            str(interpolated_dir),
                            target_fps_multiplier=fps_multiplier,
                            progress_callback=lambda p: self._update_progress(p)
                        )
                        current_frames_dir = interpolated_dir
                        current_fps = current_fps * actual_mult
                    finally:
                        interpolator.cleanup()
            
            # Stage 4: Reassemble video
            self._set_stage("reassemble")
            
            # Generate output filename
            output_filename = f"enhanced_{self.job_id}_{uuid.uuid4().hex[:8]}.mp4"
            output_path = Path(output_dir) / output_filename
            
            # Determine bitrate
            bitrate = "15M"
            if target_resolution:
                for preset, res in RESOLUTION_PRESETS.items():
                    if res == target_resolution and preset in BITRATE_PRESETS:
                        bitrate = BITRATE_PRESETS[preset]
                        break
            
            if needs_upscaling and current_frames_dir:
                # Reassemble from processed frames
                reassemble_video(
                    str(current_frames_dir),
                    str(output_path),
                    current_fps if needs_interpolation else video_info["fps"],
                    str(audio_path) if has_audio else None,
                    target_resolution,
                    bitrate,
                    "libx265",
                    lambda p: self._update_progress(p)
                )
            else:
                # Direct FFmpeg processing (no frame extraction needed)
                self._process_direct(
                    input_path,
                    str(output_path),
                    direct_target_resolution,
                    target_fps_value if needs_interpolation else None,
                    bitrate
                )
            
            # Stage 5: Apply filters
            if denoise or sharpen:
                self._set_stage("filters")
                
                filtered_path = str(output_path).replace(".mp4", "_filtered.mp4")
                apply_filters(
                    str(output_path),
                    filtered_path,
                    denoise,
                    sharpen,
                    lambda p: self._update_progress(p)
                )
                
                # Replace original with filtered
                os.remove(output_path)
                shutil.move(filtered_path, output_path)
            
            # Stage 6: Loop optimization
            if loop_optimize:
                self._set_stage("optimize")
                
                optimized_path = str(output_path).replace(".mp4", "_looped.mp4")
                optimize_for_loop(str(output_path), optimized_path)
                
                # Replace original with optimized
                os.remove(output_path)
                shutil.move(optimized_path, output_path)
            
            # Get output info
            output_info = get_video_info(str(output_path))
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            result = {
                "success": True,
                "output_path": str(output_path),
                "input": {
                    "width": video_info["width"],
                    "height": video_info["height"],
                    "fps": video_info["fps"],
                    "duration": video_info["duration"]
                },
                "output": {
                    "width": output_info["width"],
                    "height": output_info["height"],
                    "fps": output_info["fps"],
                    "duration": output_info["duration"],
                    "file_size": os.path.getsize(output_path)
                },
                "settings": {
                    "resolution": resolution,
                    "upscale_factor": upscale_factor,
                    "upscaler_algorithm": upscaler_algorithm,
                    "target_fps": target_fps,
                    "denoise": denoise,
                    "sharpen": sharpen,
                    "loop_optimize": loop_optimize
                },
                "processing_time": round(processing_time, 2)
            }
            
            logger.info(f"Pipeline completed in {processing_time:.2f}s")
            
            return result
            
        finally:
            # Cleanup temp files
            self._cleanup()
    
    def _process_direct(
        self,
        input_path: str,
        output_path: str,
        resolution: Optional[Tuple[int, int]],
        target_fps: Optional[float],
        bitrate: str
    ):
        """
        Process video directly with FFmpeg (no frame extraction).
        Used when only interpolation or resolution change is needed.
        """
        from .ffmpeg_utils import get_ffmpeg_path, get_video_info
        
        info = get_video_info(input_path)
        
        cmd = [get_ffmpeg_path(), "-i", input_path]
        
        filters = []
        
        # Add interpolation filter if needed
        if target_fps:
            filters.append(f"minterpolate=fps={target_fps}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1")
        
        # Add scale filter if needed
        if resolution:
            filters.append(f"scale={resolution[0]}:{resolution[1]}:flags=lanczos")
        
        # Format for encoding
        filters.append("format=yuv420p")
        
        if filters:
            cmd.extend(["-vf", ",".join(filters)])
        
        cmd.extend([
            "-c:v", "libx265",
            "-preset", "slow",
            "-crf", "18",
            "-b:v", bitrate,
            "-maxrate", bitrate,
            "-bufsize", str(int(bitrate.replace("M", "")) * 2) + "M",
            "-tag:v", "hvc1",
            "-c:a", "aac",
            "-b:a", "192k",
            "-y",
            output_path
        ])
        
        import subprocess
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        expected_duration = info["duration"]
        expected_fps = target_fps or info["fps"]
        expected_frames = int(expected_duration * expected_fps)
        
        for line in process.stderr:
            if "frame=" in line:
                try:
                    frame_str = line.split("frame=")[1].split()[0]
                    current_frame = int(frame_str)
                    progress = min(100, (current_frame / expected_frames) * 100)
                    self._update_progress(progress)
                except (IndexError, ValueError):
                    pass
        
        process.wait()
        
        if process.returncode != 0:
            raise RuntimeError("Direct processing failed")
    
    def _cleanup(self):
        """Clean up temporary files."""
        try:
            if self.job_temp_dir.exists():
                shutil.rmtree(self.job_temp_dir)
                logger.info(f"Cleaned up temp dir: {self.job_temp_dir}")
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
