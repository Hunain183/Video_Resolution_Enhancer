"""
FFmpeg Utilities
Video manipulation functions using FFmpeg
"""

import os
import subprocess
import json
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import logging

# Optional imports for fallback metadata extraction
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

logger = logging.getLogger(__name__)


def get_ffmpeg_path() -> str:
    """Get FFmpeg executable path."""
    path = shutil.which("ffmpeg")
    if not path:
        raise RuntimeError("FFmpeg not found. Please install FFmpeg.")
    return path


def get_ffprobe_path() -> str:
    """Get FFprobe executable path."""
    path = shutil.which("ffprobe")
    if not path:
        raise RuntimeError("FFprobe not found. Please install FFmpeg.")
    return path


def get_video_info(video_path: str) -> Dict[str, Any]:
    """
    Extract video metadata using FFprobe.
    
    Returns:
        Dictionary with video information including:
        - width, height: Video dimensions
        - fps: Frame rate
        - duration: Duration in seconds
        - total_frames: Total frame count
        - codec: Video codec
        - bitrate: Video bitrate
        - has_audio: Whether audio track exists
    """
    try:
        cmd = [
            get_ffprobe_path(),
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            video_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
    except Exception as error:
        logger.warning(f"FFprobe unavailable for {video_path}, using fallback metadata extractor: {error}")
        return _get_video_info_fallback(video_path)
    
    # Find video stream
    video_stream = None
    audio_stream = None
    for stream in data.get("streams", []):
        if stream["codec_type"] == "video" and video_stream is None:
            video_stream = stream
        elif stream["codec_type"] == "audio" and audio_stream is None:
            audio_stream = stream
    
    if not video_stream:
        raise ValueError("No video stream found")
    
    # Parse FPS
    fps_str = video_stream.get("r_frame_rate", "30/1")
    if "/" in fps_str:
        num, den = map(float, fps_str.split("/"))
        fps = num / den if den > 0 else 30.0
    else:
        fps = float(fps_str)
    
    # Get duration
    duration = float(data.get("format", {}).get("duration", 0))
    if duration == 0:
        duration = float(video_stream.get("duration", 0))
    
    # Calculate total frames
    nb_frames = video_stream.get("nb_frames")
    if nb_frames:
        total_frames = int(nb_frames)
    else:
        total_frames = int(duration * fps)
    
    # Get bitrate
    bitrate = int(data.get("format", {}).get("bit_rate", 0))
    
    return {
        "width": int(video_stream.get("width", 0)),
        "height": int(video_stream.get("height", 0)),
        "fps": round(fps, 2),
        "duration": round(duration, 2),
        "total_frames": total_frames,
        "codec": video_stream.get("codec_name", "unknown"),
        "bitrate": bitrate,
        "has_audio": audio_stream is not None,
        "pixel_format": video_stream.get("pix_fmt", "unknown")
    }


def _get_video_info_fallback(video_path: str) -> Dict[str, Any]:
    """Extract basic media metadata without ffprobe (upload-time fallback)."""
    path = Path(video_path)
    suffix = path.suffix.lower()

    # Handle GIF files with Pillow
    if suffix == ".gif" and PIL_AVAILABLE:
        try:
            return _get_gif_info(video_path)
        except Exception as e:
            logger.warning(f"PIL GIF fallback failed: {e}")

    # Try OpenCV for video files
    if CV2_AVAILABLE:
        try:
            capture = cv2.VideoCapture(video_path)
            if capture.isOpened():
                try:
                    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
                    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
                    fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
                    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

                    if width > 0 and height > 0:
                        if fps <= 0:
                            fps = 30.0
                        duration = (frame_count / fps) if frame_count > 0 else 0.0

                        return {
                            "width": width,
                            "height": height,
                            "fps": round(fps, 2),
                            "duration": round(duration, 2),
                            "total_frames": frame_count,
                            "codec": "unknown",
                            "bitrate": 0,
                            "has_audio": False,
                            "pixel_format": "unknown"
                        }
                finally:
                    capture.release()
        except Exception as e:
            logger.warning(f"OpenCV fallback failed: {e}")

    # Final fallback: return placeholder metadata so upload succeeds
    # Real metadata will be extracted when FFmpeg is available during processing
    logger.warning(f"Using placeholder metadata for {video_path} - install FFmpeg for accurate info")
    
    return {
        "width": 0,
        "height": 0,
        "fps": 30.0,
        "duration": 0.0,
        "total_frames": 0,
        "codec": "unknown",
        "bitrate": 0,
        "has_audio": False,
        "pixel_format": "unknown",
        "_placeholder": True  # Flag indicating metadata needs refresh
    }


def _get_gif_info(video_path: str) -> Dict[str, Any]:
    """Extract GIF metadata using Pillow."""
    if not PIL_AVAILABLE:
        raise RuntimeError("Pillow not available for GIF processing")
    
    from PIL import Image
    with Image.open(video_path) as img:
        width, height = img.size
        total_frames = getattr(img, "n_frames", 1)

        # Pillow stores frame duration in milliseconds
        frame_duration_ms = img.info.get("duration", 100)
        frame_duration_ms = frame_duration_ms if frame_duration_ms and frame_duration_ms > 0 else 100
        fps = 1000.0 / frame_duration_ms
        duration = (total_frames * frame_duration_ms) / 1000.0

        return {
            "width": int(width),
            "height": int(height),
            "fps": round(fps, 2),
            "duration": round(duration, 2),
            "total_frames": int(total_frames),
            "codec": "gif",
            "bitrate": 0,
            "has_audio": False,
            "pixel_format": "palette"
        }


def extract_frames(
    video_path: str,
    output_dir: str,
    fps: Optional[float] = None,
    progress_callback: Optional[callable] = None
) -> Tuple[int, float]:
    """
    Extract frames from video using FFmpeg.
    
    Args:
        video_path: Path to input video
        output_dir: Directory for extracted frames
        fps: Target FPS for extraction (None = original)
        progress_callback: Optional progress callback
    
    Returns:
        Tuple of (total_frames, original_fps)
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Get video info
    info = get_video_info(video_path)
    original_fps = info["fps"]
    
    # Build FFmpeg command
    cmd = [
        get_ffmpeg_path(),
        "-i", video_path,
        "-vsync", "0"
    ]
    
    # Set output FPS if specified
    if fps:
        cmd.extend(["-vf", f"fps={fps}"])
    
    # Output pattern
    output_pattern = os.path.join(output_dir, "frame_%06d.png")
    cmd.extend([
        "-start_number", "0",
        output_pattern
    ])
    
    logger.info(f"Extracting frames: {' '.join(cmd)}")
    
    # Run with progress tracking
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )
    
    # Read stderr for progress
    for line in process.stderr:
        if "frame=" in line and progress_callback:
            try:
                frame_str = line.split("frame=")[1].split()[0]
                current_frame = int(frame_str)
                progress = min(100, (current_frame / info["total_frames"]) * 100)
                progress_callback(progress)
            except (IndexError, ValueError):
                pass
    
    process.wait()
    
    if process.returncode != 0:
        raise RuntimeError("Frame extraction failed")
    
    # Count extracted frames
    frame_count = len(list(Path(output_dir).glob("frame_*.png")))
    logger.info(f"Extracted {frame_count} frames")
    
    return frame_count, original_fps


def extract_audio(video_path: str, output_path: str) -> bool:
    """
    Extract audio track from video.
    
    Returns:
        True if audio was extracted, False if no audio track
    """
    info = get_video_info(video_path)
    if not info["has_audio"]:
        return False
    
    cmd = [
        get_ffmpeg_path(),
        "-i", video_path,
        "-vn",  # No video
        "-acodec", "copy",
        "-y",
        output_path
    ]
    
    result = subprocess.run(cmd, capture_output=True)
    return result.returncode == 0


def reassemble_video(
    frames_dir: str,
    output_path: str,
    fps: float,
    audio_path: Optional[str] = None,
    resolution: Optional[Tuple[int, int]] = None,
    bitrate: str = "15M",
    codec: str = "libx265",
    lossless: bool = False,
    progress_callback: Optional[callable] = None
) -> str:
    """
    Reassemble video from frames using FFmpeg.
    
    Args:
        frames_dir: Directory containing frame images
        output_path: Output video file path
        fps: Output frame rate
        audio_path: Optional audio file to mux
        resolution: Optional (width, height) tuple for scaling
        bitrate: Target bitrate
        codec: Video codec (libx265 recommended)
        progress_callback: Optional progress callback
    
    Returns:
        Path to output video
    """
    # Count frames for progress tracking
    frame_count = len(list(Path(frames_dir).glob("frame_*.png")))
    
    # Build FFmpeg command
    cmd = [
        get_ffmpeg_path(),
        "-framerate", str(fps),
        "-i", os.path.join(frames_dir, "frame_%06d.png"),
    ]
    
    # Add audio if available
    if audio_path and os.path.exists(audio_path):
        cmd.extend(["-i", audio_path])
    
    # Build filter chain
    filters = []
    
    # Scale if resolution specified
    if resolution:
        filters.append(f"scale={resolution[0]}:{resolution[1]}:flags=lanczos")
    
    # Format for encoding
    filters.append("format=yuv420p")
    
    if filters:
        cmd.extend(["-vf", ",".join(filters)])
    
    # Video encoding settings
    if lossless:
        # Lossless H.264 – maximum quality, larger files
        cmd.extend([
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "0",
            "-pix_fmt", "yuv420p",
        ])
    else:
        cmd.extend([
            "-c:v", codec,
            "-preset", "slow",
            "-crf", "18",
            "-b:v", bitrate,
            "-maxrate", bitrate,
            "-bufsize", str(int(bitrate.replace("M", "")) * 2) + "M",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart"
        ])
        # H.265 specific options
        if codec == "libx265":
            cmd.extend([
                "-tag:v", "hvc1",
                "-x265-params", "log-level=error"
            ])
    
    # Audio encoding
    if audio_path and os.path.exists(audio_path):
        cmd.extend([
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest"
        ])
    
    # Output
    cmd.extend(["-y", output_path])
    
    logger.info(f"Reassembling video: {' '.join(cmd)}")
    
    # Run with progress tracking
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )
    
    for line in process.stderr:
        if "frame=" in line and progress_callback:
            try:
                frame_str = line.split("frame=")[1].split()[0]
                current_frame = int(frame_str)
                progress = min(100, (current_frame / frame_count) * 100)
                progress_callback(progress)
            except (IndexError, ValueError):
                pass
    
    process.wait()
    
    if process.returncode != 0:
        raise RuntimeError("Video reassembly failed")
    
    logger.info(f"Video reassembled: {output_path}")
    return output_path


def apply_filters(
    input_path: str,
    output_path: str,
    denoise: bool = False,
    sharpen: bool = False,
    lossless: bool = False,
    progress_callback: Optional[callable] = None
) -> str:
    """
    Apply video filters (denoise, sharpen) using FFmpeg.
    """
    filters = []
    
    if denoise:
        # hqdn3d denoiser
        filters.append("hqdn3d=4:4:6:6")
    
    if sharpen:
        # Unsharp mask for sharpening
        filters.append("unsharp=5:5:1.0:5:5:0.0")
    
    if not filters:
        # No filters, just copy
        shutil.copy(input_path, output_path)
        return output_path
    
    info = get_video_info(input_path)

    if lossless:
        encode_opts = ["-c:v", "libx264", "-preset", "ultrafast", "-crf", "0", "-pix_fmt", "yuv420p"]
    else:
        encode_opts = ["-c:v", "libx265", "-preset", "slow", "-crf", "18",
                       "-tag:v", "hvc1", "-x265-params", "log-level=error"]
    
    cmd = [
        get_ffmpeg_path(),
        "-i", input_path,
        "-vf", ",".join(filters),
        *encode_opts,
        "-c:a", "copy",
        "-y",
        output_path
    ]
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )
    
    for line in process.stderr:
        if "frame=" in line and progress_callback:
            try:
                frame_str = line.split("frame=")[1].split()[0]
                current_frame = int(frame_str)
                progress = min(100, (current_frame / info["total_frames"]) * 100)
                progress_callback(progress)
            except (IndexError, ValueError):
                pass
    
    process.wait()
    
    if process.returncode != 0:
        raise RuntimeError("Filter application failed")
    
    return output_path


def reverse_video(
    input_path: str,
    output_path: str,
    lossless: bool = False,
    progress_callback: Optional[callable] = None
) -> str:
    """
    Reverse a video without quality degradation.
    Uses FFmpeg's frame-accurate reverse filter.
    For audio tracks, also applies sample-accurate audio reversal.
    """
    info = get_video_info(input_path)
    total_frames = max(info["total_frames"], 1)

    cmd = [get_ffmpeg_path(), "-i", input_path]

    if info["has_audio"]:
        cmd.extend([
            "-filter_complex", "[0:v]reverse[vr];[0:a]areverse[ar]",
            "-map", "[vr]",
            "-map", "[ar]",
        ])
    else:
        cmd.extend(["-vf", "reverse"])

    if lossless:
        cmd.extend(["-c:v", "libx264", "-preset", "ultrafast", "-crf", "0", "-pix_fmt", "yuv420p"])
    else:
        cmd.extend([
            "-c:v", "libx265", "-preset", "slow", "-crf", "18",
            "-pix_fmt", "yuv420p", "-tag:v", "hvc1",
            "-x265-params", "log-level=error",
        ])

    if info["has_audio"]:
        cmd.extend(["-c:a", "aac", "-b:a", "192k"])

    cmd.extend(["-y", output_path])

    logger.info(f"Reversing video: {input_path}")

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )

    for line in process.stderr:
        if "frame=" in line and progress_callback:
            try:
                frame_str = line.split("frame=")[1].split()[0]
                current_frame = int(frame_str)
                progress = min(100, (current_frame / total_frames) * 100)
                progress_callback(progress)
            except (IndexError, ValueError):
                pass

    process.wait()

    if process.returncode != 0:
        raise RuntimeError("Video reversal failed")

    logger.info(f"Video reversed: {output_path}")
    return output_path


def optimize_for_loop(
    input_path: str,
    output_path: str,
    overlap_frames: int = 5
) -> str:
    """
    Optimize video for seamless looping by crossfading end to beginning.
    """
    info = get_video_info(input_path)
    duration = info["duration"]
    fps = info["fps"]
    
    # Calculate crossfade duration
    fade_duration = overlap_frames / fps
    
    # Ensure we have enough video for crossfade
    if duration < fade_duration * 2:
        shutil.copy(input_path, output_path)
        return output_path
    
    # Use FFmpeg to create crossfade loop
    cmd = [
        get_ffmpeg_path(),
        "-i", input_path,
        "-filter_complex",
        f"[0:v]split[main][loopend];"
        f"[loopend]trim=start={duration - fade_duration},setpts=PTS-STARTPTS[end];"
        f"[main]trim=end={duration - fade_duration},setpts=PTS-STARTPTS[start];"
        f"[end][start]xfade=transition=fade:duration={fade_duration}:offset=0[outv]",
        "-map", "[outv]",
        "-c:v", "libx265",
        "-preset", "slow",
        "-crf", "18",
        "-y",
        output_path
    ]
    
    result = subprocess.run(cmd, capture_output=True)
    
    if result.returncode != 0:
        # Fallback: just copy if loop optimization fails
        logger.warning("Loop optimization failed, using original")
        shutil.copy(input_path, output_path)
    
    return output_path
