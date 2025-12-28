"""AI分析API端点"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, List
import logging

from ..core.database import get_db
from ..models.ai_config import AIConfig
from ..schemas.ai_analysis import *
from ..services.ai_dialog_service import AIDialogService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai-analysis", tags=["ai-analysis"])

# 存储分析结果（内存中，生产环境应使用Redis）
analysis_results = {}


@router.get("/providers")
async def get_providers():
    """获取可用的AI服务商列表"""
    from ..services.ai_providers import AIProviderFactory
    
    providers = AIProviderFactory.get_available_providers()
    return {"providers": providers}


@router.post("/config")
async def save_ai_config(config: AIConfigCreate, db: Session = Depends(get_db)):
    """保存AI配置"""
    try:
        # 检查是否已有默认配置
        existing = db.query(AIConfig).filter_by(
            provider=config.provider,
            is_default=True
        ).first()
        
        if existing:
            existing.is_default = False
        
        # 创建新配置
        ai_config = AIConfig(
            provider=config.provider,
            api_key=config.api_key,
            model=config.model,
            base_url=config.base_url,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            is_active=True,
            is_default=(existing is None)  # 第一个配置作为默认
        )
        
        db.add(ai_config)
        db.commit()
        db.refresh(ai_config)
        
        return {
            "id": ai_config.id,
            "provider": ai_config.provider,
            "model": ai_config.model,
            "is_default": ai_config.is_default
        }
    except Exception as e:
        logger.error(f"保存AI配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config")
async def get_ai_configs(db: Session = Depends(get_db)):
    """获取所有AI配置"""
    configs = db.query(AIConfig).order_by(AIConfig.created_at.desc()).all()
    
    return {
        "configs": [
            {
                "id": c.id,
                "provider": c.provider,
                "model": c.model,
                "is_active": c.is_active,
                "is_default": c.is_default,
                "last_tested": c.last_tested,
                "test_status": c.test_status
            }
            for c in configs
        ]
    }


@router.delete("/config/{config_id}")
async def delete_ai_config(config_id: int, db: Session = Depends(get_db)):
    """删除AI配置"""
    config = db.query(AIConfig).filter(AIConfig.id == config_id).first()
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")
    
    db.delete(config)
    db.commit()
    
    return {"message": "删除成功"}


@router.post("/test-connection")
async def test_connection(request: TestConnectionRequest):
    """测试API连接"""
    from ..services.ai_providers import AIProviderFactory
    
    try:
        provider = AIProviderFactory.create_provider_from_dict({
            "provider": request.provider,
            "api_key": request.api_key,
            "model": request.model,
            "base_url": request.base_url
        })
        
        result = await provider.test_connection()
        return result
    except Exception as e:
        return {"success": False, "message": f"测试失败: {str(e)}"}


@router.post("/analyze")
async def analyze_text(request: AnalysisRequest, db: Session = Depends(get_db)):
    """分析文本"""
    # 获取AI配置
    if request.ai_config_id:
        ai_config = db.query(AIConfig).filter(
            AIConfig.id == request.ai_config_id
        ).first()
    else:
        # 使用默认配置
        ai_config = db.query(AIConfig).filter(
            AIConfig.is_default == True
        ).first()
    
    if not ai_config:
        raise HTTPException(
            status_code=400,
            detail="未找到AI配置，请先配置AI API"
        )
    
    # 创建服务并分析
    service = AIDialogService(db)
    result = await service.analyze_full_text(
        request.text,
        ai_config
    )
    
    return result
