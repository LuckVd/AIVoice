"""AI对话分析综合服务"""
import re
import json
import logging
import uuid
import time
from typing import Dict, List, Any
from sqlalchemy.orm import Session

from ..models.ai_config import AIConfig
from ..services.ai_providers import AIProviderFactory
from ..services.text_segmenter import TextSegmenter

logger = logging.getLogger(__name__)


class AIDialogService:
    """AI对话分析服务"""
    
    DIALOG_ANALYSIS_PROMPT = """你是一个专业的小说文本分析专家。
请分析给定文本，识别对话和旁白。

返回JSON格式（不要markdown）：
{
  "segments": [
    {
      "index": 0,
      "type": "narration",
      "text": "旁白内容",
      "speaker": null
    },
    {
      "index": 1,
      "type": "dialog",
      "text": "对话内容",
      "speaker": "角色名",
      "emotion": "neutral"
    }
  ],
  "detected_speakers": ["角色A", "角色B"]
}

重要要求：
1. 必须为每段对话推断说话人（speaker字段不能为空或null）
2. 识别引号内容：""「」
3. 根据上下文推断说话人：
   - 如果对话前面有"某某说"、"某某问"、"某某答"等，则说话人为该人名
   - 如果没有明确提示，根据上下文逻辑推断（如：对话轮次中交替出现的角色）
   - 如果实在无法推断，使用"角色A"、"角色B"、"角色C"等通用名称
4. **必须保留所有原文内容，包括所有旁白和动作描述**：
   - 旁白包括：场景描述、人物动作（如"小红点点头"、"他叹了口气"）、心理活动等
   - 对话用引号括起来的内容单独提取
   - 动作描述（如"某某说"、"某某点点头"）应作为旁白保留，不要删除
   - **绝对不能省略或合并任何原文内容**
5. 保留原文标点，不要删除

文本：
{text}"""

    def __init__(self, db: Session):
        self.db = db
        self.segmenter = TextSegmenter()
    
    async def analyze_full_text(
        self, 
        text: str, 
        ai_config: AIConfig,
        progress_callback = None
    ) -> Dict[str, Any]:
        """完整分析流程"""
        
        analysis_id = str(uuid.uuid4())
        result = {
            "analysis_id": analysis_id,
            "segments": [],
            "characters": {},
            "text_segments": [],
            "analysis_metadata": {
                "total_chars": len(text),
                "segment_count": 0,
                "processing_time": 0,
                "errors": []
            }
        }
        
        start_time = time.time()
        
        try:
            # 步骤1：文本分段
            if progress_callback:
                await progress_callback(analysis_id, 1, 4, "正在分段文本...")
            
            text_segments = self.segmenter.segment(text)
            result["text_segments"] = text_segments
            result["analysis_metadata"]["segment_count"] = len(text_segments)
            
            # 步骤2：逐段分析
            all_segments = []
            for idx, text_seg in enumerate(text_segments):
                if progress_callback:
                    await progress_callback(
                        analysis_id,
                        2 + idx,
                        2 + len(text_segments),
                        f"正在分析第{idx+1}/{len(text_segments)}段..."
                    )
                
                segments = await self._analyze_segment(text_seg, ai_config, idx)
                all_segments.extend(segments)
            
            result["segments"] = all_segments
            
            # 步骤3：提取角色
            if progress_callback:
                await progress_callback(analysis_id, 3, 4, "正在提取角色...")
            
            result["characters"] = self._extract_characters(all_segments)
            
            # 完成
            if progress_callback:
                await progress_callback(analysis_id, 4, 4, "分析完成！")
            
            result["analysis_metadata"]["processing_time"] = time.time() - start_time
            result["status"] = "completed"
            
        except Exception as e:
            logger.error(f"分析失败: {str(e)}")
            result["analysis_metadata"]["errors"].append(str(e))
            result["status"] = "failed"
            result["error"] = str(e)
        
        return result
    
    async def _analyze_segment(
        self, 
        text: str, 
        ai_config: AIConfig,
        segment_index: int
    ) -> List[Dict]:
        """分析单个文本段"""
        
        provider = AIProviderFactory.create_provider(ai_config)
        
        messages = [
            {
                "role": "system",
                "content": self.DIALOG_ANALYSIS_PROMPT
            },
            {
                "role": "user",
                "content": f"待分析文本：\n\n{text}"
            }
        ]
        
        try:
            response = await provider.chat(messages)
            content = response["choices"][0]["message"]["content"]

            logger.info(f"🤖 AI原始响应内容: {content[:500]}...")  # 记录前500字符

            # 提取JSON - 改进正则表达式以匹配完整JSON
            json_match = re.search(r'\{[\s\S]*\}', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                logger.info(f"📦 提取的JSON字符串: {json_str[:500]}...")

                result = json.loads(json_str)

                # 添加segment标记
                segments = result.get("segments", [])
                for seg in segments:
                    seg["text_segment_index"] = segment_index

                # 记录检测结果
                speakers_in_segments = [seg.get("speaker") for seg in segments if seg.get("speaker")]
                logger.info(f"✅ 本段分析完成: {len(segments)}个segments, 检测到的说话人: {speakers_in_segments}")

                return segments
            else:
                logger.warning(f"⚠️ 未能从AI响应中提取JSON: {content[:200]}")

        except json.JSONDecodeError as e:
            logger.warning(f"JSON解析失败: {str(e)}")
            logger.warning(f"响应内容: {content[:500]}")
        except Exception as e:
            logger.warning(f"AI分析失败，使用规则分析: {str(e)}")
            logger.warning(f"错误类型: {type(e).__name__}")

        return self._fallback_analysis(text, segment_index)
    
    def _fallback_analysis(self, text: str, segment_index: int) -> List[Dict]:
        """降级：使用规则分析"""
        segments = []
        index = 0
        
        # 简单规则：查找引号
        dialog_pattern = r'["「『](.*?)["」』]'
        last_end = 0
        
        for match in re.finditer(dialog_pattern, text):
            # 之前的旁白
            if match.start() > last_end:
                narration = text[last_end:match.start()].strip()
                if narration:
                    segments.append({
                        "index": index,
                        "type": "narration",
                        "text": narration,
                        "speaker": None,
                        "text_segment_index": segment_index
                    })
                    index += 1
            
            # 对话
            segments.append({
                "index": index,
                "type": "dialog",
                "text": match.group(1),
                "speaker": "未知角色",
                "emotion": "neutral",
                "text_segment_index": segment_index
            })
            index += 1
            
            last_end = match.end()
        
        # 最后的旁白
        if last_end < len(text):
            narration = text[last_end:].strip()
            if narration:
                segments.append({
                    "index": index,
                    "type": "narration",
                    "text": narration,
                    "speaker": None,
                    "text_segment_index": segment_index
                })
        
        return segments
    
    def _extract_characters(self, segments: List[Dict]) -> Dict[str, Dict]:
        """从segments中提取角色"""
        characters = {}

        logger.info(f"🔍 开始提取角色，总segments数: {len(segments)}")

        for seg in segments:
            speaker = seg.get("speaker")
            logger.info(f"  - segment type={seg.get('type')}, speaker={speaker}")

            if speaker and speaker != "未知角色":
                if speaker not in characters:
                    characters[speaker] = {
                        "name": speaker,
                        "dialog_count": 0,
                        "first_appearance": seg.get("text_segment_index", 0)
                    }

                if speaker in characters:
                    characters[speaker]["dialog_count"] += 1

        logger.info(f"✅ 最终提取的角色: {list(characters.keys())}")
        return characters
