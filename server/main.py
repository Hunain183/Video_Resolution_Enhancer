"""
AI Video Enhancement Server
Main FastAPI Application
"""

import os
import uuid
import asyncio
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import aiofiles

from config import settings
from processors.job_manager import JobManager, JobStatus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize job manager
job_manager = JobManager()

# Directory setup
def setup_directories():
    """Create required directories."""
    for directory in [settings.UPLOAD_DIR, settings.OUTPUT_DIR, settings.TEMP_DIR, settings.MODELS_DIR]:
        Path(directory).mkdir(parents=True, exist_ok=True)
    logger.info("Directories initialized")


async def cleanup_old_files():
    """Background task to clean up old temporary files."""
    while True:
        try:
            cutoff_time = datetime.now() - timedelta(hours=settings.FILE_RETENTION_HOURS)
            
            for directory in [settings.UPLOAD_DIR, settings.OUTPUT_DIR, settings.TEMP_DIR]:
                dir_path = Path(directory)
                if dir_path.exists():
                    for item in dir_path.iterdir():
                        try:
                            item_mtime = datetime.fromtimestamp(item.stat().st_mtime)
                            if item_mtime < cutoff_time:
                                if item.is_dir():
                                    shutil.rmtree(item)
                                else:
                                    item.unlink()
                                logger.info(f"Cleaned up: {item}")
                        except Exception as e:
                            logger.error(f"Failed to clean {item}: {e}")
            
            # Clean completed jobs
            job_manager.cleanup_old_jobs(cutoff_time)
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
        
        await asyncio.sleep(1800)  # Run every 30 minutes


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    setup_directories()
    cleanup_task = asyncio.create_task(cleanup_old_files())
    logger.info("AI Video Enhancement Server started")
    yield
    cleanup_task.cancel()
    logger.info("AI Video Enhancement Server stopped")


# Create FastAPI app
app = FastAPI(
    title="AI Video Enhancement API",
    description="AI-powered video upscaling and frame interpolation",
    version="1.0.0",
    lifespan=lifespan
)

# Increase request body size limit
class MaxBodySizeMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_body_size: int = 2 * 1024 * 1024 * 1024):
        super().__init__(app)
        self.max_body_size = max_body_size

    async def dispatch(self, request: Request, call_next):
        request._max_body_size = self.max_body_size
        return await call_next(request)

app.add_middleware(MaxBodySizeMiddleware, max_body_size=2 * 1024 * 1024 * 1024)

# CORS middleware - allow all origins for Codespaces compatibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # Must be False when using allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# Request/Response Models
class EnhanceRequest(BaseModel):
    """Video enhancement request parameters."""
    resolution: str = Field("original", description="Target resolution: original, 1080p, 1440p, 4k")
    upscale_factor: int = Field(2, ge=1, le=4, description="Upscale factor: 2 or 4")
    upscaler_algorithm: str = Field("realesrgan", description="Upscaler: original (None), realesrgan, lanczos")
    target_fps: str = Field("original", description="Target FPS: original, 60, 120")
    denoise: bool = Field(False, description="Enable denoising")
    sharpen: bool = Field(False, description="Enable sharpening")
    loop_optimize: bool = Field(False, description="Optimize for seamless looping")
    reverse_video: bool = Field(False, description="Reverse the video")
    lossless_output: bool = Field(False, description="Lossless encoding for maximum quality")


class JobResponse(BaseModel):
    """Job status response."""
    job_id: str
    status: str
    progress: float = 0
    current_step: str = ""
    message: str = ""
    estimated_time: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    processing_device: Optional[str] = None
    effective_tile: Optional[int] = None


class UploadResponse(BaseModel):
    """Upload response with file info."""
    file_id: str
    filename: str
    file_path: str
    file_size: int
    video_info: Dict[str, Any]


# API Endpoints

@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "AI Video Enhancement API",
        "version": "1.0.0",
        "status": "running",
        "supported_formats": list(settings.ALLOWED_EXTENSIONS),
        "features": {
            "upscaling": "Real-ESRGAN (2x, 4x)",
            "interpolation": "RIFE",
            "resolutions": ["original", "1080p", "1440p", "4k"],
            "fps_options": ["original", "60", "120"]
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    import torch
    
    gpu_available = torch.cuda.is_available()
    gpu_name = torch.cuda.get_device_name(0) if gpu_available else None
    
    # Check FFmpeg
    ffmpeg_ok = shutil.which("ffmpeg") is not None
    
    return {
        "status": "healthy",
        "ffmpeg": "available" if ffmpeg_ok else "missing",
        "gpu": {
            "available": gpu_available,
            "name": gpu_name,
            "cuda_version": torch.version.cuda if gpu_available else None,
            "torch_version": torch.__version__,
            "torch_cuda_build": torch.version.cuda
        },
        "directories": {
            "upload": Path(settings.UPLOAD_DIR).exists(),
            "output": Path(settings.OUTPUT_DIR).exists(),
            "temp": Path(settings.TEMP_DIR).exists(),
            "models": Path(settings.MODELS_DIR).exists()
        }
    }


@app.post("/upload", response_model=UploadResponse)
async def upload_video(file: UploadFile = File(...)):
    """
    Upload a video file for processing.
    Validates format and extracts video information.
    Uses streaming to handle large files without memory issues.
    """
    # Validate file extension
    ext = Path(file.filename).suffix.lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format. Allowed: {list(settings.ALLOWED_EXTENSIONS)}"
        )
    
    # Generate unique filename
    file_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"upload_{timestamp}_{file_id}{ext}"
    file_path = Path(settings.UPLOAD_DIR) / safe_filename
    
    # Stream file to disk in chunks to handle large files
    file_size = 0
    chunk_size = 1024 * 1024  # 1MB chunks
    
    try:
        async with aiofiles.open(file_path, 'wb') as f:
            while chunk := await file.read(chunk_size):
                file_size += len(chunk)
                if file_size > settings.MAX_FILE_SIZE:
                    await f.close()
                    file_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large. Max size: {settings.MAX_FILE_SIZE // (1024*1024)}MB"
                    )
                await f.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
    
    # Get video info
    try:
        from processors.ffmpeg_utils import get_video_info
        video_info = get_video_info(str(file_path))
    except Exception as e:
        file_path.unlink()
        raise HTTPException(status_code=400, detail=f"Invalid video file: {str(e)}")
    
    return UploadResponse(
        file_id=file_id,
        filename=safe_filename,
        file_path=str(file_path),
        file_size=file_size,
        video_info=video_info
    )


# Store for chunked uploads
chunked_uploads: Dict[str, Dict[str, Any]] = {}


@app.post("/upload-chunk")
async def upload_chunk(
    chunk: UploadFile = File(...),
    chunk_index: int = Form(...),
    total_chunks: int = Form(...),
    file_id: str = Form(...),
    filename: str = Form(...),
    file_size: int = Form(...)
):
    """
    Upload a single chunk of a large file.
    Chunks are stored temporarily and assembled when finalized.
    """
    # Create chunk directory if needed
    chunk_dir = Path(settings.TEMP_DIR) / "chunks" / file_id
    chunk_dir.mkdir(parents=True, exist_ok=True)
    
    # Save chunk
    chunk_path = chunk_dir / f"chunk_{chunk_index:05d}"
    content = await chunk.read()
    
    async with aiofiles.open(chunk_path, 'wb') as f:
        await f.write(content)
    
    # Track upload progress
    if file_id not in chunked_uploads:
        chunked_uploads[file_id] = {
            "filename": filename,
            "file_size": file_size,
            "total_chunks": total_chunks,
            "received_chunks": set(),
            "chunk_dir": str(chunk_dir)
        }
    
    chunked_uploads[file_id]["received_chunks"].add(chunk_index)
    
    return {
        "status": "chunk_received",
        "chunk_index": chunk_index,
        "received": len(chunked_uploads[file_id]["received_chunks"]),
        "total": total_chunks
    }


@app.post("/finalize-upload", response_model=UploadResponse)
async def finalize_upload(
    file_id: str = Form(...),
    filename: str = Form(...)
):
    """
    Finalize a chunked upload by assembling all chunks.
    """
    if file_id not in chunked_uploads:
        raise HTTPException(status_code=404, detail="Upload not found")
    
    upload_info = chunked_uploads[file_id]
    chunk_dir = Path(upload_info["chunk_dir"])
    
    # Verify all chunks received
    if len(upload_info["received_chunks"]) != upload_info["total_chunks"]:
        raise HTTPException(
            status_code=400,
            detail=f"Missing chunks: received {len(upload_info['received_chunks'])}/{upload_info['total_chunks']}"
        )
    
    # Generate final filename
    ext = Path(filename).suffix.lower()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    short_id = file_id[:8] if len(file_id) > 8 else file_id
    safe_filename = f"upload_{timestamp}_{short_id}{ext}"
    final_path = Path(settings.UPLOAD_DIR) / safe_filename
    
    # Assemble chunks
    try:
        async with aiofiles.open(final_path, 'wb') as outfile:
            for i in range(upload_info["total_chunks"]):
                chunk_path = chunk_dir / f"chunk_{i:05d}"
                async with aiofiles.open(chunk_path, 'rb') as chunk_file:
                    content = await chunk_file.read()
                    await outfile.write(content)
        
        # Clean up chunks
        shutil.rmtree(chunk_dir)
        del chunked_uploads[file_id]
        
    except Exception as e:
        final_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Failed to assemble file: {str(e)}")
    
    # Get video info
    try:
        from processors.ffmpeg_utils import get_video_info
        video_info = get_video_info(str(final_path))
    except Exception as e:
        final_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"Invalid video file: {str(e)}")
    
    file_size = final_path.stat().st_size
    
    return UploadResponse(
        file_id=short_id,
        filename=safe_filename,
        file_path=str(final_path),
        file_size=file_size,
        video_info=video_info
    )


@app.post("/enhance", response_model=JobResponse)
async def start_enhancement(
    file_path: str = Form(...),
    resolution: str = Form("original"),
    upscale_factor: int = Form(2),
    upscaler_algorithm: str = Form("realesrgan"),
    target_fps: str = Form("original"),
    denoise: bool = Form(False),
    sharpen: bool = Form(False),
    loop_optimize: bool = Form(False),
    reverse_video: bool = Form(False),
    lossless_output: bool = Form(False),
):
    """
    Start video enhancement job.
    Returns job ID for status tracking.
    """
    # Validate input file exists
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Input file not found")

    valid_algorithms = {"original", "realesrgan", "lanczos"}
    if upscaler_algorithm not in valid_algorithms:
        raise HTTPException(status_code=400, detail=f"Invalid upscaler_algorithm. Valid options: {sorted(valid_algorithms)}")
    
    # Create job
    job_id = job_manager.create_job(
        input_path=file_path,
        settings={
            "resolution": resolution,
            "upscale_factor": upscale_factor,
            "upscaler_algorithm": upscaler_algorithm,
            "target_fps": target_fps,
            "denoise": denoise,
            "sharpen": sharpen,
            "loop_optimize": loop_optimize,
            "reverse_video": reverse_video,
            "lossless_output": lossless_output,
        }
    )
    
    # Start processing in background
    asyncio.create_task(process_video_async(job_id))
    
    return JobResponse(
        job_id=job_id,
        status="queued",
        progress=0,
        current_step="Initializing",
        message="Job queued for processing"
    )


async def process_video_async(job_id: str):
    """Background task for video processing."""
    try:
        try:
            from processors.pipeline import VideoPipeline
        except Exception as e:
            raise RuntimeError(
                "AI processing dependencies are missing. Run install.bat to install torch/realesrgan packages."
            ) from e

        job = job_manager.get_job(job_id)
        if not job:
            return
        
        job_manager.update_job(job_id, status=JobStatus.PROCESSING, current_step="Starting pipeline")
        
        # Create pipeline and run in thread pool
        pipeline = VideoPipeline(
            job_id=job_id,
            progress_callback=lambda p, s: job_manager.update_job(job_id, progress=p, current_step=s)
        )
        
        def run_pipeline():
            return pipeline.process(
                input_path=job["input_path"],
                output_dir=settings.OUTPUT_DIR,
                **job["settings"]
            )
        
        # Run in thread pool to avoid blocking
        result = await asyncio.to_thread(run_pipeline)
        
        job_manager.update_job(
            job_id,
            status=JobStatus.COMPLETED,
            progress=100,
            current_step="Complete",
            result=result
        )
        logger.info(f"Job {job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        job_manager.update_job(
            job_id,
            status=JobStatus.FAILED,
            current_step="Error",
            message=str(e)
        )


def _derive_runtime_context(job: Dict[str, Any]) -> Dict[str, Any]:
    """Infer active processing device/tile for current job settings."""
    settings_map = job.get("settings", {})
    algorithm = settings_map.get("upscaler_algorithm", "original")

    if algorithm == "original":
        return {"processing_device": None, "effective_tile": None}

    if algorithm == "lanczos":
        return {"processing_device": "cpu", "effective_tile": None}

    # Real-ESRGAN path: device depends on CUDA availability, and CPU forces tile=0.
    gpu_available = False
    try:
        import torch
        gpu_available = torch.cuda.is_available()
    except Exception:
        gpu_available = False

    configured_tile = int(getattr(settings, "ESRGAN_TILE", 0) or 0)

    if gpu_available:
        return {
            "processing_device": "gpu",
            "effective_tile": configured_tile,
        }

    return {
        "processing_device": "cpu",
        "effective_tile": 0,
    }


@app.get("/status/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str):
    """Get job processing status."""
    job = job_manager.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    runtime_context = _derive_runtime_context(job)

    return JobResponse(
        job_id=job_id,
        status=job["status"].value,
        progress=job.get("progress", 0),
        current_step=job.get("current_step", ""),
        message=job.get("message", ""),
        estimated_time=job.get("estimated_time"),
        result=job.get("result"),
        processing_device=runtime_context["processing_device"],
        effective_tile=runtime_context["effective_tile"],
    )


@app.get("/download/{job_id}")
async def download_result(job_id: str):
    """Download processed video."""
    job = job_manager.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job["status"] != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Job not completed")
    
    output_path = job.get("result", {}).get("output_path")
    if not output_path or not os.path.exists(output_path):
        raise HTTPException(status_code=404, detail="Output file not found")
    
    filename = Path(output_path).name
    return FileResponse(
        path=output_path,
        filename=filename,
        media_type="video/mp4"
    )


@app.delete("/job/{job_id}")
async def cancel_job(job_id: str):
    """Cancel a processing job."""
    job = job_manager.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job["status"] in [JobStatus.COMPLETED, JobStatus.FAILED]:
        return {"message": "Job already finished"}
    
    job_manager.update_job(job_id, status=JobStatus.CANCELLED)
    return {"message": "Job cancelled"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
