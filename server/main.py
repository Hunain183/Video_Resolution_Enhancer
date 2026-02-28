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

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import logging

from config import settings
from processors.pipeline import VideoPipeline
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

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class EnhanceRequest(BaseModel):
    """Video enhancement request parameters."""
    resolution: str = Field("original", description="Target resolution: original, 1080p, 1440p, 4k")
    upscale_factor: int = Field(2, ge=1, le=4, description="Upscale factor: 2 or 4")
    target_fps: str = Field("original", description="Target FPS: original, 60, 120")
    denoise: bool = Field(False, description="Enable denoising")
    sharpen: bool = Field(False, description="Enable sharpening")
    loop_optimize: bool = Field(False, description="Optimize for seamless looping")


class JobResponse(BaseModel):
    """Job status response."""
    job_id: str
    status: str
    progress: float = 0
    current_step: str = ""
    message: str = ""
    estimated_time: Optional[float] = None
    result: Optional[Dict[str, Any]] = None


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
            "cuda_version": torch.version.cuda if gpu_available else None
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
    """
    # Validate file extension
    ext = Path(file.filename).suffix.lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format. Allowed: {list(settings.ALLOWED_EXTENSIONS)}"
        )
    
    # Read file to check size
    content = await file.read()
    file_size = len(content)
    
    if file_size > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max size: {settings.MAX_FILE_SIZE // (1024*1024)}MB"
        )
    
    # Generate unique filename
    file_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"upload_{timestamp}_{file_id}{ext}"
    file_path = Path(settings.UPLOAD_DIR) / safe_filename
    
    # Save file
    with open(file_path, "wb") as f:
        f.write(content)
    
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


@app.post("/enhance", response_model=JobResponse)
async def start_enhancement(
    file_path: str = Form(...),
    resolution: str = Form("original"),
    upscale_factor: int = Form(2),
    target_fps: str = Form("original"),
    denoise: bool = Form(False),
    sharpen: bool = Form(False),
    loop_optimize: bool = Form(False)
):
    """
    Start video enhancement job.
    Returns job ID for status tracking.
    """
    # Validate input file exists
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Input file not found")
    
    # Create job
    job_id = job_manager.create_job(
        input_path=file_path,
        settings={
            "resolution": resolution,
            "upscale_factor": upscale_factor,
            "target_fps": target_fps,
            "denoise": denoise,
            "sharpen": sharpen,
            "loop_optimize": loop_optimize
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


@app.get("/status/{job_id}", response_model=JobResponse)
async def get_job_status(job_id: str):
    """Get job processing status."""
    job = job_manager.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobResponse(
        job_id=job_id,
        status=job["status"].value,
        progress=job.get("progress", 0),
        current_step=job.get("current_step", ""),
        message=job.get("message", ""),
        estimated_time=job.get("estimated_time"),
        result=job.get("result")
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
