"""
Real-ESRGAN Upscaler
AI-based image/video upscaling using Real-ESRGAN
"""

import os
import glob
import torch
import numpy as np
from PIL import Image
from pathlib import Path
from typing import Optional, Callable, List
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging

logger = logging.getLogger(__name__)

# Try to import Real-ESRGAN
try:
    from basicsr.archs.rrdbnet_arch import RRDBNet
    from realesrgan import RealESRGANer
    ESRGAN_AVAILABLE = True
except ImportError:
    ESRGAN_AVAILABLE = False
    logger.warning("Real-ESRGAN not available. Install with: pip install realesrgan")


class RealESRGANUpscaler:
    """
    Real-ESRGAN based image upscaler.
    Supports 2x and 4x upscaling with GPU acceleration.
    """
    
    # Model configurations
    MODELS = {
        "realesrgan-x4plus": {
            "url": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth",
            "scale": 4,
            "model_params": {"num_in_ch": 3, "num_out_ch": 3, "num_feat": 64, "num_block": 23, "num_grow_ch": 32}
        },
        "realesrgan-x4plus-anime": {
            "url": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth",
            "scale": 4,
            "model_params": {"num_in_ch": 3, "num_out_ch": 3, "num_feat": 64, "num_block": 6, "num_grow_ch": 32}
        },
        "realesrgan-x2plus": {
            "url": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth",
            "scale": 2,
            "model_params": {"num_in_ch": 3, "num_out_ch": 3, "num_feat": 64, "num_block": 23, "num_grow_ch": 32}
        }
    }
    
    def __init__(
        self,
        model_name: str = "realesrgan-x4plus-anime",
        models_dir: str = "./models",
        device: Optional[str] = None,
        fp16: bool = True,
        tile: int = 200,
        tile_pad: int = 10
    ):
        """
        Initialize Real-ESRGAN upscaler.
        
        Args:
            model_name: Model to use (realesrgan-x4plus, realesrgan-x4plus-anime, realesrgan-x2plus)
            models_dir: Directory to store/load models
            device: Device to use (cuda, cpu, or None for auto)
            fp16: Use half precision for faster inference
        """
        self.model_name = model_name
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine device
        if device:
            self.device = device
        else:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        self.fp16 = fp16 and self.device == "cuda"
        self.tile = tile
        self.tile_pad = tile_pad
        self.upsampler = None
        
        logger.info(
            f"Upscaler initialized: model={model_name}, device={self.device}, "
            f"fp16={self.fp16}, tile={self.tile}, tile_pad={self.tile_pad}"
        )
    
    def _download_model(self, model_name: str) -> str:
        """Download model if not present."""
        if model_name not in self.MODELS:
            raise ValueError(f"Unknown model: {model_name}")
        
        config = self.MODELS[model_name]
        model_path = self.models_dir / f"{model_name}.pth"
        
        if not model_path.exists():
            logger.info(f"Downloading model {model_name}...")
            import requests
            
            response = requests.get(config["url"], stream=True)
            response.raise_for_status()
            
            with open(model_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"Model downloaded: {model_path}")
        
        return str(model_path)
    
    def load_model(self):
        """Load the upscaling model."""
        if not ESRGAN_AVAILABLE:
            raise RuntimeError("Real-ESRGAN is not available. Please install it.")
        
        if self.upsampler is not None:
            return  # Already loaded
        
        config = self.MODELS[self.model_name]
        model_path = self._download_model(self.model_name)
        
        # Create model
        model = RRDBNet(**config["model_params"], scale=config["scale"])
        
        # Create upsampler
        self.upsampler = RealESRGANer(
            scale=config["scale"],
            model_path=model_path,
            model=model,
            tile=self.tile,
            tile_pad=self.tile_pad,
            pre_pad=0,
            half=self.fp16,
            device=self.device
        )
        
        logger.info(f"Model loaded: {self.model_name}")
    
    @property
    def scale_factor(self) -> int:
        """Get the scale factor of the loaded model."""
        return self.MODELS[self.model_name]["scale"]
    
    def upscale_image(self, image_path: str, output_path: str) -> str:
        """
        Upscale a single image.
        
        Args:
            image_path: Path to input image
            output_path: Path for output image
        
        Returns:
            Path to upscaled image
        """
        self.load_model()
        
        # Read image
        img = Image.open(image_path).convert("RGB")
        img_np = np.array(img)
        
        # Upscale
        output, _ = self.upsampler.enhance(img_np, outscale=self.scale_factor)
        
        # Save
        Image.fromarray(output).save(output_path, quality=95)
        
        return output_path
    
    def upscale_frames(
        self,
        input_dir: str,
        output_dir: str,
        target_factor: int = 4,
        progress_callback: Optional[Callable[[float], None]] = None,
        max_workers: int = 1
    ) -> int:
        """
        Upscale all frames in a directory.
        
        Args:
            input_dir: Directory containing input frames
            output_dir: Directory for output frames
            target_factor: Target upscale factor (2 or 4)
            progress_callback: Callback for progress updates
            max_workers: Number of parallel workers (1 for GPU)
        
        Returns:
            Number of processed frames
        """
        self.load_model()
        
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Get all frame files
        frame_files = sorted(glob.glob(os.path.join(input_dir, "frame_*.png")))
        total_frames = len(frame_files)
        
        if total_frames == 0:
            raise ValueError("No frames found in input directory")
        
        logger.info(f"Upscaling {total_frames} frames with {self.model_name}")
        
        # Calculate actual upscale runs needed
        model_scale = self.scale_factor
        runs_needed = 1
        if target_factor > model_scale:
            runs_needed = 2  # Need to run twice for 4x when using 2x model
        
        processed = 0
        
        for frame_file in frame_files:
            frame_name = os.path.basename(frame_file)
            output_file = os.path.join(output_dir, frame_name)
            
            try:
                # Read frame
                img = Image.open(frame_file).convert("RGB")
                img_np = np.array(img)
                
                # Upscale (multiple passes if needed)
                current_scale = 1
                output = img_np
                
                for _ in range(runs_needed):
                    if current_scale >= target_factor:
                        break
                    output, _ = self.upsampler.enhance(output, outscale=model_scale)
                    current_scale *= model_scale
                
                # If overscaled, resize down
                if current_scale > target_factor:
                    h, w = output.shape[:2]
                    new_h = int(h * target_factor / current_scale)
                    new_w = int(w * target_factor / current_scale)
                    output = np.array(Image.fromarray(output).resize((new_w, new_h), Image.LANCZOS))
                
                # Save
                Image.fromarray(output).save(output_file, quality=95)
                
                processed += 1
                
                if progress_callback:
                    progress_callback((processed / total_frames) * 100)
                    
            except Exception as e:
                logger.error(f"Failed to upscale {frame_file}: {e}")
                # Copy original on failure
                import shutil
                shutil.copy(frame_file, output_file)
                processed += 1
        
        logger.info(f"Upscaling complete: {processed}/{total_frames} frames")
        return processed
    
    def cleanup(self):
        """Release model resources."""
        if self.upsampler is not None:
            del self.upsampler
            self.upsampler = None
            
            if self.device == "cuda":
                torch.cuda.empty_cache()
            
            logger.info("Upscaler resources released")


class FallbackUpscaler:
    """
    Fallback upscaler using Lanczos when Real-ESRGAN is not available.
    """
    
    def __init__(self, scale_factor: int = 2):
        self.scale_factor = scale_factor
        logger.info(f"Using fallback Lanczos upscaler (scale={scale_factor})")
    
    def upscale_frames(
        self,
        input_dir: str,
        output_dir: str,
        target_factor: int = 4,
        progress_callback: Optional[Callable[[float], None]] = None,
        max_workers: int = 4
    ) -> int:
        """Upscale frames using Lanczos interpolation."""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        frame_files = sorted(glob.glob(os.path.join(input_dir, "frame_*.png")))
        total_frames = len(frame_files)
        
        if total_frames == 0:
            raise ValueError("No frames found")
        
        processed = 0
        
        def process_frame(frame_file):
            frame_name = os.path.basename(frame_file)
            output_file = os.path.join(output_dir, frame_name)
            
            img = Image.open(frame_file)
            new_size = (img.width * target_factor, img.height * target_factor)
            upscaled = img.resize(new_size, Image.LANCZOS)
            upscaled.save(output_file, quality=95)
            
            return frame_name
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(process_frame, f): f for f in frame_files}
            
            for future in as_completed(futures):
                processed += 1
                if progress_callback:
                    progress_callback((processed / total_frames) * 100)
        
        return processed
    
    def cleanup(self):
        pass


class BicubicUpscaler:
    """
    CPU upscaler using bicubic interpolation. Fastest option, good quality.
    """

    def __init__(self, scale_factor: int = 2):
        self.scale_factor = scale_factor
        logger.info(f"Using Bicubic upscaler (scale={scale_factor})")

    def upscale_frames(
        self,
        input_dir: str,
        output_dir: str,
        target_factor: int = 4,
        progress_callback: Optional[Callable[[float], None]] = None,
        max_workers: int = 4
    ) -> int:
        """Upscale frames using bicubic interpolation."""
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        frame_files = sorted(glob.glob(os.path.join(input_dir, "frame_*.png")))
        total_frames = len(frame_files)

        if total_frames == 0:
            raise ValueError("No frames found")

        processed = 0

        def process_frame(frame_file):
            frame_name = os.path.basename(frame_file)
            output_file = os.path.join(output_dir, frame_name)
            img = Image.open(frame_file)
            new_size = (img.width * target_factor, img.height * target_factor)
            upscaled = img.resize(new_size, Image.BICUBIC)
            upscaled.save(output_file, quality=95)
            return frame_name

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(process_frame, f): f for f in frame_files}
            for future in as_completed(futures):
                processed += 1
                if progress_callback:
                    progress_callback((processed / total_frames) * 100)

        return processed

    def cleanup(self):
        pass


# Algorithm name → Real-ESRGAN model mapping
_ALGORITHM_MODEL_MAP = {
    "realesrgan-anime":   "realesrgan-x4plus-anime",
    "realesrgan-general": "realesrgan-x4plus",
    "realesrgan-x2":      "realesrgan-x2plus",
    "realesrgan":         "realesrgan-x4plus-anime",  # legacy
}


def create_upscaler(
    algorithm: str = "realesrgan-anime",
    model_name: str = None,  # kept for back-compat, overridden by algorithm
    models_dir: str = "./models",
    use_gpu: bool = True,
    require_realesrgan: bool = False,
    fp16: bool = True,
    tile: int = 200,
    tile_pad: int = 10
):
    """
    Factory: return the appropriate upscaler for the requested algorithm.

    Supported algorithms:
        realesrgan-anime    – Real-ESRGAN anime/GIF model (best for animation)
        realesrgan-general  – Real-ESRGAN general photo model
        realesrgan-x2       – Real-ESRGAN 2× model (faster)
        lanczos             – CPU Lanczos (fast, sharp)
        bicubic             – CPU Bicubic (fastest)
    """
    if algorithm == "bicubic":
        return BicubicUpscaler()

    if algorithm == "lanczos":
        return FallbackUpscaler()

    # Resolve algorithm to model name
    resolved_model = _ALGORITHM_MODEL_MAP.get(algorithm, model_name or "realesrgan-x4plus-anime")

    if ESRGAN_AVAILABLE:
        device = "cuda" if use_gpu and torch.cuda.is_available() else "cpu"
        return RealESRGANUpscaler(
            model_name=resolved_model,
            models_dir=models_dir,
            device=device,
            fp16=fp16,
            tile=tile,
            tile_pad=tile_pad,
        )
    else:
        if require_realesrgan:
            raise RuntimeError(
                "Real-ESRGAN is not available. Install required packages: "
                'pip install "basicsr>=1.4.2" "realesrgan>=0.3.0"'
            )
        logger.warning("Real-ESRGAN not available, using Lanczos fallback")
        return FallbackUpscaler()
