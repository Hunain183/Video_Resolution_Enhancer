"""
Job Manager
Handles job tracking and status updates
"""

import uuid
from enum import Enum
from datetime import datetime
from typing import Dict, Any, Optional
from threading import Lock
import logging

logger = logging.getLogger(__name__)


class JobStatus(Enum):
    """Job status states."""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobManager:
    """
    Thread-safe job manager for tracking video processing jobs.
    """
    
    def __init__(self):
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()
    
    def create_job(self, input_path: str, settings: Dict[str, Any]) -> str:
        """Create a new job and return job ID."""
        job_id = str(uuid.uuid4())
        
        with self._lock:
            self._jobs[job_id] = {
                "job_id": job_id,
                "input_path": input_path,
                "settings": settings,
                "status": JobStatus.QUEUED,
                "progress": 0,
                "current_step": "Queued",
                "message": "",
                "estimated_time": None,
                "result": None,
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
        
        logger.info(f"Created job {job_id}")
        return job_id
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job by ID."""
        with self._lock:
            return self._jobs.get(job_id)
    
    def update_job(
        self,
        job_id: str,
        status: Optional[JobStatus] = None,
        progress: Optional[float] = None,
        current_step: Optional[str] = None,
        message: Optional[str] = None,
        estimated_time: Optional[float] = None,
        result: Optional[Dict[str, Any]] = None
    ):
        """Update job status and info."""
        with self._lock:
            if job_id not in self._jobs:
                return
            
            job = self._jobs[job_id]
            
            if status is not None:
                job["status"] = status
            if progress is not None:
                job["progress"] = progress
            if current_step is not None:
                job["current_step"] = current_step
            if message is not None:
                job["message"] = message
            if estimated_time is not None:
                job["estimated_time"] = estimated_time
            if result is not None:
                job["result"] = result
            
            job["updated_at"] = datetime.now()
    
    def cleanup_old_jobs(self, cutoff_time: datetime):
        """Remove jobs older than cutoff time."""
        with self._lock:
            old_jobs = [
                jid for jid, job in self._jobs.items()
                if job.get("created_at", datetime.now()) < cutoff_time
                and job["status"] in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]
            ]
            
            for jid in old_jobs:
                del self._jobs[jid]
                logger.info(f"Cleaned up old job {jid}")
    
    def is_job_cancelled(self, job_id: str) -> bool:
        """Check if job was cancelled."""
        job = self.get_job(job_id)
        return job is not None and job["status"] == JobStatus.CANCELLED
