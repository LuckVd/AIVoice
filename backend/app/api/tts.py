from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import uuid4
from datetime import datetime

from ..core.database import get_db
from ..models.tts import TTSRequest, TaskStatus
from ..schemas.tts import (
    TTSRequestCreate, TTSRequestResponse, TaskStatusResponse,
    TTSRequestCreateSSML, TTSRequestCreateSSMLResponse,
    SSMLPresetResponse, SSMLPresetsListResponse, SSMLPreviewResponse
)
from ..tasks.tts_tasks import process_tts_task, process_tts_task_ssml
from ..services.tts_service import TTSService
from ..services.ssml_generator import generate_ssml, PRESET_CONFIGS

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
    if len(request_data.text) > 200000:
        raise HTTPException(status_code=400, detail="Text too long (max 200000 characters)")

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


# === SSML 相关接口 ===

@router.post("/ssml", response_model=TTSRequestCreateSSMLResponse)
async def create_tts_request_ssml(
    request_data: TTSRequestCreateSSML,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """创建使用 SSML 的 TTS 请求"""
    # Validate text length
    if len(request_data.text) > 200000:
        raise HTTPException(status_code=400, detail="Text too long (max 200000 characters)")

    # Determine if using SSML
    use_ssml = request_data.use_ssml and not request_data.legacy_mode

    # Determine SSML configuration
    ssml_config = None
    ssml_preset_name = None

    if use_ssml:
        if request_data.ssml_preset:
            ssml_preset_name = request_data.ssml_preset
            if ssml_preset_name not in PRESET_CONFIGS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid preset. Available: {list(PRESET_CONFIGS.keys())}"
                )

        # Check for custom overrides
        overrides = {}
        for field in ['voice', 'style', 'role', 'rate', 'pitch', 'comma_pause', 'sentence_pause']:
            value = getattr(request_data, field)
            if value is not None:
                overrides[field] = value

        if overrides or ssml_preset_name:
            # Create custom SSML config
            if not ssml_preset_name:
                ssml_preset_name = tts_service.default_ssml_config

            ssml_config = tts_service.create_ssml_config_from_preset(ssml_preset_name, **overrides)

    # Determine voice and parameters for database
    voice = request_data.voice or "zh-CN-XiaoxiaoNeural"
    rate = request_data.legacy_rate if request_data.legacy_mode else "-15%"
    pitch = request_data.legacy_pitch if request_data.legacy_mode else "-2Hz"

    # Create database record (temporarily disable SSML fields to avoid database issues)
    task_id = str(uuid4())
    tts_request = TTSRequest(
        text=request_data.text,
        voice=voice,
        rate=rate,
        pitch=pitch,
        task_id=task_id,
        status=TaskStatus.PENDING
    )

    db.add(tts_request)
    db.commit()
    db.refresh(tts_request)

    # Estimate chunks
    if use_ssml and ssml_config:
        max_len = ssml_config.structure.max_sentence_len * 3
    else:
        max_len = 500

    chunks = tts_service.split_text(tts_service.clean_text(request_data.text), max_len)
    estimated_chunks = len(chunks)

    # Queue background task
    if use_ssml:
        process_tts_task_ssml.delay(
            tts_request.id,
            ssml_preset=ssml_preset_name,
            ssml_overrides=overrides if overrides else None
        )
    else:
        process_tts_task.delay(tts_request.id)

    return TTSRequestCreateSSMLResponse(
        task_id=task_id,
        status=TaskStatus.PENDING,
        message="TTS request created successfully",
        ssml_used=use_ssml,
        ssml_preset=ssml_preset_name,
        estimated_chunks=estimated_chunks
    )


@router.get("/ssml/presets", response_model=SSMLPresetsListResponse)
def get_ssml_presets():
    """获取可用的 SSML 预设配置"""
    presets_dict = tts_service.get_available_ssml_presets()

    presets_response = {}
    for name, config in presets_dict.items():
        presets_response[name] = SSMLPresetResponse(**config)

    return SSMLPresetsListResponse(presets=presets_response)


@router.post("/ssml/preview", response_model=SSMLPreviewResponse)
def preview_ssml(request_data: TTSRequestCreateSSML):
    """预览生成的 SSML（不生成音频）"""
    # Validate text length
    if len(request_data.text) > 200000:
        raise HTTPException(status_code=400, detail="Text too long (max 200000 characters)")

    # Determine SSML configuration
    ssml_config = None
    ssml_preset_name = request_data.ssml_preset or tts_service.default_ssml_config

    if ssml_preset_name not in PRESET_CONFIGS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid preset. Available: {list(PRESET_CONFIGS.keys())}"
        )

    # Check for custom overrides
    overrides = {}
    for field in ['voice', 'style', 'role', 'rate', 'pitch', 'comma_pause', 'sentence_pause']:
        value = getattr(request_data, field)
        if value is not None:
            overrides[field] = value

    if overrides:
        ssml_config = tts_service.create_ssml_config_from_preset(ssml_preset_name, **overrides)

    # Generate SSML
    ssml = generate_ssml(request_data.text, ssml_config or ssml_preset_name)

    # Estimate duration (rough estimate: 150 characters per minute)
    character_count = len(request_data.text)
    estimated_duration = int(character_count * 60 / 150)

    return SSMLPreviewResponse(
        ssml=ssml,
        preset_used=ssml_preset_name,
        estimated_duration=estimated_duration,
        character_count=character_count
    )


@router.get("/ssml/{preset_name}", response_model=SSMLPresetResponse)
def get_ssml_preset(preset_name: str):
    """获取特定 SSML 预设配置的详细信息"""
    presets_dict = tts_service.get_available_ssml_presets()

    if preset_name not in presets_dict:
        raise HTTPException(
            status_code=404,
            detail=f"Preset not found. Available: {list(presets_dict.keys())}"
        )

    return SSMLPresetResponse(**presets_dict[preset_name])