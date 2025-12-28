"""文本分段服务"""
import re
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


class TextSegmenter:
    """智能文本分段器"""

    # 分段策略配置
    SEGMENT_CONFIG = {
        "min_chars": 2000,      # 最小2000字
        "max_chars": 4000,      # 最大4000字
        "target_chars": 3000,   # 目标3000字
    }

    def __init__(self, config: Dict = None):
        """初始化分段器

        Args:
            config: 自定义配置，覆盖默认配置
        """
        self.config = config or self.SEGMENT_CONFIG

    def segment(self, text: str) -> List[str]:
        """
        智能分段文本

        策略优先级：
        1. 按章节分割（章节标题）
        2. 按场景分割（空行分隔）
        3. 按长度强制分割

        Args:
            text: 待分段的文本

        Returns:
            文本段列表
        """
        if not text or not text.strip():
            return []

        text = text.strip()

        # 策略1：按章节分割
        chapters = self._split_by_chapters(text)

        # 检查章节分割是否合适
        if self._are_segments_good(chapters):
            logger.info(f"使用章节分割，共{len(chapters)}段")
            return chapters

        # 策略2：章节过长，按场景分割
        segments = []
        for chapter in chapters:
            if len(chapter) > self.config["max_chars"]:
                scenes = self._split_by_scenes(chapter)
                segments.extend(scenes)
                logger.info(f"章节过长，使用场景分割，分为{len(scenes)}段")
            else:
                segments.append(chapter)

        # 策略3：如果还太长，强制按长度分割
        final_segments = []
        for segment in segments:
            if len(segment) > self.config["max_chars"]:
                parts = self._split_by_length(segment)
                final_segments.extend(parts)
                logger.info(f"段落仍然过长，强制分割为{len(parts)}段")
            else:
                final_segments.append(segment)

        logger.info(f"最终分段: {len(final_segments)}段")
        return final_segments

    def _split_by_chapters(self, text: str) -> List[str]:
        """按章节分割

        匹配常见章节标题格式：
        - 第X章
        - Chapter X
        - 一、二、三、
        """
        chapter_patterns = [
            r'第[一二三四五六七八九十百千零\d]+章[^\n]*',
            r'第[一二三四五六七八九十百千零\d]+节[^\n]*',
            r'Chapter\s*\d+[^\n]*',
            r'[一二三四五六七八九十]+、[^\n]*',
            r'\d+\.[^\n]*',  # 1. 2. 3.
        ]

        # 尝试每种模式
        for pattern in chapter_patterns:
            matches = list(re.finditer(pattern, text, re.MULTILINE))
            if len(matches) >= 2:  # 至少2个章节才算
                segments = []
                last_end = 0

                for match in matches:
                    start = match.start()
                    if start > last_end:
                        segments.append(text[last_end:start].strip())
                    last_end = start

                # 添加最后一章
                if last_end < len(text):
                    segments.append(text[last_end:].strip())

                if segments and all(self._is_valid_segment(seg) for seg in segments):
                    return segments

        # 没有找到合适的章节，返回整个文本
        return [text]

    def _split_by_scenes(self, text: str) -> List[str]:
        """按场景（空行）分割"""
        # 按连续空行分割
        segments = re.split(r'\n\s*\n\s*\n+', text)
        return [s.strip() for s in segments if s.strip()]

    def _split_by_length(self, text: str) -> List[str]:
        """强制按长度分割

        优先在句子结束处分割，保持语义完整
        """
        target = self.config["target_chars"]
        segments = []

        # 优先在句子结束处分割
        sentences = re.split(r'([。！？.!?])', text)
        current = ""

        for i in range(0, len(sentences), 2):
            sentence = sentences[i]
            if i + 1 < len(sentences):
                sentence += sentences[i + 1]

            if len(current) + len(sentence) <= target:
                current += sentence
            else:
                if current:
                    segments.append(current.strip())
                current = sentence

        if current:
            segments.append(current.strip())

        return segments

    def _are_segments_good(self, segments: List[str]) -> bool:
        """检查分段是否合适

        Args:
            segments: 文本段列表

        Returns:
            是否所有段都在范围内
        """
        if not segments:
            return False

        min_size = self.config["min_chars"]
        max_size = self.config["max_chars"]

        return all(min_size <= len(seg) <= max_size for seg in segments)

    def _is_valid_segment(self, segment: str) -> bool:
        """检查单个段落是否有效

        Args:
            segment: 文本段落

        Returns:
            是否在合理范围内
        """
        return self.config["min_chars"] <= len(segment) <= self.config["max_chars"] * 2

    def get_segment_stats(self, text: str) -> Dict:
        """获取分段统计信息

        Args:
            text: 待分段的文本

        Returns:
            统计信息字典
        """
        total_chars = len(text)
        estimated_segments = total_chars // self.config["target_chars"]

        return {
            "total_chars": total_chars,
            "estimated_segments": estimated_segments + 1,
            "config": self.config
        }
