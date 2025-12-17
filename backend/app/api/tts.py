from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from uuid import uuid4
from datetime import datetime

from ..core.database import get_db
from ..models.tts import TTSRequest, TaskStatus
from ..schemas.tts import TTSRequestCreate, TTSRequestResponse, TaskStatusResponse
from ..tasks.tts_tasks import process_tts_task
from ..services.tts_service import TTSService

router = APIRouter(prefix="/tts", tags=["TTS"])
tts_service = TTSService()


@router.post("/", response_model=TTSRequestResponse)
async def create_tts_request(
    request_data: TTSRequestCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Create a new TTS request"""
    # Validate text length
    if len(request_data.text) > 10000:
        raise HTTPException(status_code=400, detail="Text too long (max 10000 characters)")

    # Create database record
    task_id = str(uuid4())
    tts_request = TTSRequest(
        text=request_data.text,
        voice=request_data.voice,
        rate=request_data.rate,
        pitch=request_data.pitch,
        task_id=task_id,
        status=TaskStatus.PENDING
    )

    db.add(tts_request)
    db.commit()
    db.refresh(tts_request)

    # Queue background task
    process_tts_task.delay(tts_request.id)

    return tts_request


@router.get("/{task_identifier}", response_model=TTSRequestResponse)
def get_tts_request(task_identifier: str, db: Session = Depends(get_db)):
    """Get TTS request details by numeric ID or task_id"""
    # Try to parse as integer ID first
    try:
        id_value = int(task_identifier)
        tts_request = db.query(TTSRequest).filter(TTSRequest.id == id_value).first()
    except ValueError:
        # If not an integer, treat as task_id
        tts_request = db.query(TTSRequest).filter(TTSRequest.task_id == task_identifier).first()

    if not tts_request:
        raise HTTPException(status_code=404, detail="TTS request not found")

    return tts_request


@router.get("/{task_id}/status", response_model=TaskStatusResponse)
def get_task_status(task_id: str, db: Session = Depends(get_db)):
    """Get real-time task status"""
    tts_request = db.query(TTSRequest).filter(TTSRequest.task_id == task_id).first()
    if not tts_request:
        raise HTTPException(status_code=404, detail="Task not found")

    # Calculate progress
    progress = 0.0
    if tts_request.total_chunks > 0:
        progress = tts_request.processed_chunks / tts_request.total_chunks

    # Map status
    status_mapping = {
        TaskStatus.PENDING: "PENDING",
        TaskStatus.PROCESSING: "PROCESSING",
        TaskStatus.COMPLETED: "SUCCESS",
        TaskStatus.FAILED: "FAILURE",
        TaskStatus.CANCELLED: "CANCELLED"
    }

    return TaskStatusResponse(
        task_id=task_id,
        status=tts_request.status,
        progress=progress,
        message=tts_request.error_message if tts_request.status == TaskStatus.FAILED else None,
        result_url=tts_request.audio_url if tts_request.status == TaskStatus.COMPLETED else None
    )


@router.get("/", response_model=List[TTSRequestResponse])
def list_tts_requests(
    skip: int = 0,
    limit: int = 50,
    status: TaskStatus = None,
    db: Session = Depends(get_db)
):
    """List TTS requests with pagination and optional status filter"""
    query = db.query(TTSRequest)

    if status:
        query = query.filter(TTSRequest.status == status)

    requests = query.order_by(TTSRequest.created_at.desc()).offset(skip).limit(limit).all()
    return requests


@router.delete("/{task_id}")
def delete_tts_request(task_id: str, db: Session = Depends(get_db)):
    """Delete a TTS request and its audio file"""
    tts_request = db.query(TTSRequest).filter(TTSRequest.task_id == task_id).first()
    if not tts_request:
        raise HTTPException(status_code=404, detail="TTS request not found")

    # Delete audio file if exists
    if tts_request.audio_url:
        tts_service.delete_audio(task_id)

    # Delete database record
    db.delete(tts_request)
    db.commit()

    return {"message": "TTS request deleted successfully"}


@router.post("/{task_id}/cancel")
def cancel_tts_request(task_id: str, db: Session = Depends(get_db)):
    """Cancel a pending or processing TTS request"""
    tts_request = db.query(TTSRequest).filter(TTSRequest.task_id == task_id).first()
    if not tts_request:
        raise HTTPException(status_code=404, detail="TTS request not found")

    if tts_request.status not in [TaskStatus.PENDING, TaskStatus.PROCESSING]:
        raise HTTPException(status_code=400, detail="Cannot cancel completed or failed request")

    # Update status
    tts_request.status = TaskStatus.CANCELLED
    tts_request.completed_at = datetime.utcnow()
    db.commit()

    # TODO: Cancel the Celery task if it's running

    return {"message": "TTS request cancelled successfully"}