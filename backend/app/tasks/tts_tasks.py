from celery import current_task
from sqlalchemy.orm import Session
from ..core.database import SessionLocal
from ..core.celery_app import celery_app
from ..models.tts import TTSRequest, TaskStatus
from ..services.tts_service import TTSService
import asyncio
import traceback
from datetime import datetime
import os


@celery_app.task(bind=True)
def process_tts_task(self, task_id: int):
    """Background task to process TTS request"""
    db = SessionLocal()
    tts_service = TTSService()

    try:
        # Get the TTS request from database
        tts_request = db.query(TTSRequest).filter(TTSRequest.id == task_id).first()
        if not tts_request:
            raise ValueError(f"TTS request {task_id} not found")

        # Update status to processing
        tts_request.status = TaskStatus.PROCESSING
        tts_request.started_at = datetime.utcnow()
        db.commit()

        # Update task progress
        current_task.update_state(
            state='PROCESSING',
            meta={'progress': 0.1, 'message': 'Starting TTS processing...'}
        )

        # Run the async TTS generation
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Clean and split text to get chunk count
            cleaned_text = tts_service.clean_text(tts_request.text)
            chunks = tts_service.split_text(cleaned_text)
            tts_request.total_chunks = len(chunks)
            db.commit()

            # Update progress
            current_task.update_state(
                state='PROCESSING',
                meta={'progress': 0.2, 'message': f'Processing {len(chunks)} text chunks...'}
            )

            # Generate audio
            audio_path = loop.run_until_complete(tts_service.generate_tts_async(
                tts_request.task_id,
                tts_request.text,
                tts_request.voice,
                tts_request.rate,
                tts_request.pitch
            ))

            # Get file size and duration (approximate)
            file_size = os.path.getsize(audio_path) if os.path.exists(audio_path) else 0
            # Approximate duration: 150 words per minute, average Chinese character is a word
            estimated_duration = len(tts_request.text) * 60 / 150

            # Update request with success
            tts_request.status = TaskStatus.COMPLETED
            tts_request.audio_url = tts_service.get_audio_url(tts_request.task_id)
            tts_request.completed_at = datetime.utcnow()
            tts_request.processed_chunks = len(chunks)
            tts_request.file_size_bytes = file_size
            tts_request.duration_seconds = int(estimated_duration)
            db.commit()

            # Final progress update
            current_task.update_state(
                state='SUCCESS',
                meta={
                    'progress': 1.0,
                    'message': 'TTS processing completed successfully',
                    'result_url': tts_request.audio_url
                }
            )

        finally:
            loop.close()

    except Exception as e:
        # Update request with error
        error_message = f"TTS processing failed: {str(e)}\n{traceback.format_exc()}"

        if tts_request:
            tts_request.status = TaskStatus.FAILED
            tts_request.error_message = error_message
            tts_request.completed_at = datetime.utcnow()
            db.commit()

        # Update task state
        current_task.update_state(
            state='FAILURE',
            meta={
                'progress': 0,
                'message': error_message,
                'error': str(e)
            }
        )

        # Re-raise the exception for Celery
        raise

    finally:
        db.close()


@celery_app.task
def cleanup_old_audio():
    """Clean up old audio files (run periodically)"""
    db = SessionLocal()
    tts_service = TTSService()

    try:
        # Delete files older than 24 hours and marked as completed
        from datetime import timedelta
        cutoff_time = datetime.utcnow() - timedelta(hours=24)

        old_requests = db.query(TTSRequest).filter(
            TTSRequest.created_at < cutoff_time,
            TTSRequest.status == TaskStatus.COMPLETED
        ).all()

        for request in old_requests:
            if tts_service.delete_audio(request.task_id):
                # Update database to reflect deletion
                request.audio_url = None
                request.file_size_bytes = None
                db.commit()

        return f"Cleaned up {len(old_requests)} old audio files"

    finally:
        db.close()