"""
RIFE Frame Interpolator
Real-Time Intermediate Flow Estimation for frame interpolation
"""

import os
import glob
import shutil
import torch
import numpy as np
from PIL import Image
from pathlib import Path
from typing import Optional, Callable, Tuple
import logging
import subprocess

logger = logging.getLogger(__name__)


class RIFEInterpolator:
    """
    RIFE-based frame interpolator.
    Generates intermediate frames for FPS increase.
    """
    
    MODEL_URL = "https://github.com/hzwer/Practical-RIFE/releases/download/model/flownet.pkl"
    
    def __init__(
        self,
        models_dir: str = "./models",
        device: Optional[str] = None
    ):
        """
        Initialize RIFE interpolator.
        
        Args:
            models_dir: Directory for model storage
            device: Device to use (cuda, cpu, or None for auto)
        """
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        if device:
            self.device = device
        else:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        self.model = None
        self._rife_available = self._check_rife_available()
        
        logger.info(f"RIFE Interpolator: device={self.device}, available={self._rife_available}")
    
    def _check_rife_available(self) -> bool:
        """Check if RIFE model is available."""
        try:
            # Try importing RIFE
            import importlib.util
            spec = importlib.util.find_spec("model.RIFE")
            return spec is not None
        except:
            return False
    
    def interpolate_frames(
        self,
        input_dir: str,
        output_dir: str,
        target_fps_multiplier: float = 2.0,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> Tuple[int, float]:
        """
        Interpolate frames to increase FPS.
        
        Args:
            input_dir: Directory with input frames
            output_dir: Directory for interpolated frames
            target_fps_multiplier: FPS multiplier (2.0 = double FPS)
            progress_callback: Callback for progress updates
        
        Returns:
            Tuple of (output_frame_count, effective_multiplier)
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Get frame files
        frame_files = sorted(glob.glob(os.path.join(input_dir, "frame_*.png")))
        total_frames = len(frame_files)
        
        if total_frames < 2:
            raise ValueError("Need at least 2 frames for interpolation")
        
        # Calculate interpolation factor
        # For 2x FPS, we need 1 intermediate frame between each pair
        # For 4x FPS, we need 3 intermediate frames between each pair
        interp_factor = int(target_fps_multiplier)
        intermediate_frames = interp_factor - 1
        
        logger.info(f"Interpolating {total_frames} frames with {intermediate_frames} intermediates each")
        
        output_frame_idx = 0
        processed_pairs = 0
        total_pairs = total_frames - 1
        
        for i in range(total_frames - 1):
            frame1_path = frame_files[i]
            frame2_path = frame_files[i + 1]
            
            # Copy first frame
            output_path = os.path.join(output_dir, f"frame_{output_frame_idx:06d}.png")
            shutil.copy(frame1_path, output_path)
            output_frame_idx += 1
            
            # Generate intermediate frames
            for j in range(intermediate_frames):
                t = (j + 1) / interp_factor  # Interpolation factor (0 to 1)
                
                intermediate = self._interpolate_pair(frame1_path, frame2_path, t)
                
                output_path = os.path.join(output_dir, f"frame_{output_frame_idx:06d}.png")
                intermediate.save(output_path, quality=95)
                output_frame_idx += 1
            
            processed_pairs += 1
            
            if progress_callback:
                progress_callback((processed_pairs / total_pairs) * 100)
        
        # Copy last frame
        output_path = os.path.join(output_dir, f"frame_{output_frame_idx:06d}.png")
        shutil.copy(frame_files[-1], output_path)
        output_frame_idx += 1
        
        logger.info(f"Interpolation complete: {total_frames} -> {output_frame_idx} frames")
        
        return output_frame_idx, interp_factor
    
    def _interpolate_pair(
        self,
        frame1_path: str,
        frame2_path: str,
        t: float
    ) -> Image.Image:
        """
        Interpolate between two frames.
        
        Args:
            frame1_path: Path to first frame
            frame2_path: Path to second frame
            t: Interpolation factor (0.0 = frame1, 1.0 = frame2)
        
        Returns:
            Interpolated frame as PIL Image
        """
        # Try RIFE if available
        if self._rife_available and self.model is not None:
            return self._rife_interpolate(frame1_path, frame2_path, t)
        
        # Fallback to frame blending
        return self._blend_interpolate(frame1_path, frame2_path, t)
    
    def _blend_interpolate(
        self,
        frame1_path: str,
        frame2_path: str,
        t: float
    ) -> Image.Image:
        """
        Simple frame blending interpolation (fallback).
        """
        img1 = np.array(Image.open(frame1_path).convert("RGB")).astype(np.float32)
        img2 = np.array(Image.open(frame2_path).convert("RGB")).astype(np.float32)
        
        # Linear blend
        blended = (1 - t) * img1 + t * img2
        blended = np.clip(blended, 0, 255).astype(np.uint8)
        
        return Image.fromarray(blended)
    
    def _rife_interpolate(
        self,
        frame1_path: str,
        frame2_path: str,
        t: float
    ) -> Image.Image:
        """
        RIFE optical flow interpolation.
        """
        # This would use the actual RIFE model
        # For now, fall back to blending
        return self._blend_interpolate(frame1_path, frame2_path, t)
    
    def cleanup(self):
        """Release model resources."""
        if self.model is not None:
            del self.model
            self.model = None
            
            if self.device == "cuda":
                torch.cuda.empty_cache()


class FFmpegInterpolator:
    """
    FFmpeg-based frame interpolation using minterpolate filter.
    More reliable fallback that uses optical flow.
    """
    
    def __init__(self):
        logger.info("Using FFmpeg minterpolate for frame interpolation")
    
    def interpolate_video(
        self,
        input_path: str,
        output_path: str,
        target_fps: float,
        progress_callback: Optional[Callable[[float], None]] = None
    ) -> str:
        """
        Interpolate video directly using FFmpeg minterpolate.
        
        Args:
            input_path: Input video path
            output_path: Output video path
            target_fps: Target frame rate
            progress_callback: Progress callback
        
        Returns:
            Path to interpolated video
        """
        from .ffmpeg_utils import get_video_info, get_ffmpeg_path
        
        info = get_video_info(input_path)
        
        cmd = [
            get_ffmpeg_path(),
            "-i", input_path,
            "-vf", f"minterpolate=fps={target_fps}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1",
            "-c:v", "libx265",
            "-preset", "slow",
            "-crf", "18",
            "-c:a", "copy",
            "-y",
            output_path
        ]
        
        logger.info(f"FFmpeg interpolation: {info['fps']} -> {target_fps} FPS")
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        expected_frames = int(info["duration"] * target_fps)
        
        for line in process.stderr:
            if "frame=" in line and progress_callback:
                try:
                    frame_str = line.split("frame=")[1].split()[0]
                    current_frame = int(frame_str)
                    progress = min(100, (current_frame / expected_frames) * 100)
                    progress_callback(progress)
                except (IndexError, ValueError):
                    pass
        
        process.wait()
        
        if process.returncode != 0:
            raise RuntimeError("FFmpeg interpolation failed")
        
        return output_path
    
    def cleanup(self):
        pass


def create_interpolator(
    models_dir: str = "./models",
    use_gpu: bool = True,
    use_ffmpeg: bool = True
) -> "RIFEInterpolator | FFmpegInterpolator":
    """
    Factory function to create appropriate interpolator.
    """
    if use_ffmpeg:
        return FFmpegInterpolator()
    
    device = "cuda" if use_gpu and torch.cuda.is_available() else "cpu"
    return RIFEInterpolator(models_dir=models_dir, device=device)
