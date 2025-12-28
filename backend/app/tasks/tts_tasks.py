from celery import current_task
from sqlalchemy.orm import Session
from ..core.database import SessionLocal
from ..core.celery_app import celery_app
from ..models.tts import TTSRequest, TaskStatus
from ..services.tts_service import TTSService
from ..services.ssml_generator import generate_ssml, PRESET_CONFIGS
import asyncio
import traceback
from datetime import datetime
import os
import re


@celery_app.task(bind=True)
def process_tts_task(self, task_id: int):
    """Background task to process TTS request (legacy mode)"""
    return _process_tts_task_internal(self, task_id, use_ssml=False, ssml_preset=None, ssml_overrides=None)


@celery_app.task(bind=True)
def process_tts_task_ssml(self, task_id: int, ssml_preset: str = None, ssml_overrides: dict = None):
    """Background task to process TTS request with SSML"""
    return _process_tts_task_internal(self, task_id, use_ssml=True, ssml_preset=ssml_preset, ssml_overrides=ssml_overrides)


def _process_tts_task_internal(self, task_id: int, use_ssml: bool = False, ssml_preset: str = None, ssml_overrides: dict = None):
    """Internal TTS processing task"""
    db = SessionLocal()
    tts_service = TTSService()

    try:
        # Get the TTS request from database
        tts_request = db.query(TTSRequest).filter(TTSRequest.id == task_id).first()
        if not tts_request:
            raise ValueError(f"TTS request {task_id} not found")

        # Update status to processing (temporarily disable SSML fields)
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
            # Prepare SSML configuration if needed
            ssml_config = None
            if use_ssml:
                if ssml_overrides:
                    ssml_config = tts_service.create_ssml_config_from_preset(
                        ssml_preset or tts_service.default_ssml_config,
                        **ssml_overrides
                    )
                else:
                    ssml_config = ssml_preset or tts_service.default_ssml_config

                # SSML generation will be done during chunk processing
                # (temporarily disabled storing in database)
                pass

            # Clean and split text to get chunk count
            cleaned_text = tts_service.clean_text(tts_request.text)

            # Adjust chunk size based on SSML configuration
            if use_ssml and ssml_config:
                if isinstance(ssml_config, str) and ssml_config in PRESET_CONFIGS:
                    chunk_size = PRESET_CONFIGS[ssml_config].structure.max_sentence_len * 3
                elif hasattr(ssml_config, 'structure'):
                    chunk_size = ssml_config.structure.max_sentence_len * 3
                else:
                    chunk_size = 500
            else:
                chunk_size = 500

            chunks = tts_service.split_text(cleaned_text, chunk_size)
            tts_request.total_chunks = len(chunks)
            db.commit()

            # Update progress
            current_task.update_state(
                state='PROCESSING',
                meta={'progress': 0.2, 'message': f'Processing {len(chunks)} text chunks...'}
            )

            # Generate audio
            # When using SSML, pass empty rate/pitch to avoid conflicts with SSML parameters
            rate = "" if use_ssml else tts_request.rate
            pitch = "" if use_ssml else tts_request.pitch

            audio_path = loop.run_until_complete(tts_service.generate_tts_async(
                tts_request.task_id,
                tts_request.text,
                tts_request.voice,
                rate,
                pitch,
                use_ssml=use_ssml,
                ssml_config=ssml_config
            ))

            # Get file size and actual duration using ffprobe
            file_size = os.path.getsize(audio_path) if os.path.exists(audio_path) else 0

            # Get actual audio duration using ffprobe
            actual_duration = tts_service.get_audio_duration(audio_path)

            # Update request with success
            tts_request.status = TaskStatus.COMPLETED
            tts_request.audio_url = tts_service.get_audio_url(tts_request.task_id)
            tts_request.completed_at = datetime.utcnow()
            tts_request.processed_chunks = len(chunks)
            tts_request.file_size_bytes = file_size
            tts_request.duration_seconds = int(actual_duration) if actual_duration else 0
            db.commit()

            # Final progress update
            current_task.update_state(
                state='SUCCESS',
                meta={
                    'progress': 1.0,
                    'message': 'TTS processing completed successfully',
                    'result_url': tts_request.audio_url,
                    'ssml_used': use_ssml,
                    'ssml_preset': ssml_preset if use_ssml else None
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