from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from pydantic import BaseModel

from ..core.database import get_db
from ..models.saved_audio import SavedAudio
from ..models.tts import TTSRequest
import shutil
import os

router = APIRouter(prefix="/saved-audios", tags=["saved-audios"])


class SaveAudioRequest(BaseModel):
    task_id: str
    name: str


@router.post("")
async def save_audio(
    request: SaveAudioRequest,
    db: Session = Depends(get_db)
):
    """
    保存音频到收藏

    Args:
        request: 包含 task_id 和 name 的请求体
        db: 数据库会话
    """
    # 查找原始任务
    task = db.query(TTSRequest).filter(TTSRequest.task_id == request.task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status != "completed":
        raise HTTPException(status_code=400, detail="任务未完成，无法保存")

    if not task.audio_url:
        raise HTTPException(status_code=400, detail="音频文件不存在")

    # 提取音频文件路径
    audio_filename = task.audio_url.split("/")[-1]
    source_path = f"/app/storage/audio/{audio_filename}"

    # 创建保存目录
    saved_dir = "/app/storage/saved"
    os.makedirs(saved_dir, exist_ok=True)

    # 复制音频文件到保存目录
    saved_filename = f"saved_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{audio_filename}"
    dest_path = os.path.join(saved_dir, saved_filename)

    try:
        if os.path.exists(source_path):
            shutil.copy2(source_path, dest_path)
        else:
            raise HTTPException(status_code=404, detail="源音频文件不存在")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存文件失败: {str(e)}")

    # 保存到数据库
    saved_audio = SavedAudio(
        name=request.name,
        original_task_id=request.task_id,
        audio_path=f"/storage/saved/{saved_filename}",
        text=task.text,
        voice=task.voice,
        duration_seconds=task.duration_seconds,
        file_size_bytes=task.file_size_bytes
    )

    db.add(saved_audio)
    db.commit()
    db.refresh(saved_audio)

    return {
        "id": saved_audio.id,
        "name": saved_audio.name,
        "audio_url": f"http://localhost:8000{saved_audio.audio_path}",
        "created_at": saved_audio.created_at
    }


@router.get("")
async def get_saved_audios(db: Session = Depends(get_db)):
    """获取所有保存的音频列表"""
    saved_audios = db.query(SavedAudio).order_by(SavedAudio.created_at.desc()).all()

    return {
        "saved_audios": [
            {
                "id": sa.id,
                "name": sa.name,
                "audio_url": f"http://localhost:8000{sa.audio_path}",
                "text": sa.text,
                "voice": sa.voice,
                "duration_seconds": sa.duration_seconds,
                "file_size_bytes": sa.file_size_bytes,
                "created_at": sa.created_at.isoformat()
            }
            for sa in saved_audios
        ]
    }


@router.delete("/{saved_id}")
async def delete_saved_audio(saved_id: int, db: Session = Depends(get_db)):
    """删除保存的音频"""
    saved_audio = db.query(SavedAudio).filter(SavedAudio.id == saved_id).first()
    if not saved_audio:
        raise HTTPException(status_code=404, detail="保存的音频不存在")

    # 删除文件
    file_path = f"/app{saved_audio.audio_path}"
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            print(f"删除文件失败: {e}")

    # 从数据库删除
    db.delete(saved_audio)
    db.commit()

    return {"message": "删除成功"}
