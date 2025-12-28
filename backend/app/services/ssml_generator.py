"""
SSML 生成器模块 V2 - 简化版本，专注于正确性
"""

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union
from xml.dom import minidom


@dataclass
class VoiceConfig:
    """声音层配置"""
    name: str = "zh-CN-XiaoxiaoNeural"
    style: Optional[str] = None
    fallback: Optional[str] = None
    role: Optional[str] = None


@dataclass
class PaceConfig:
    """节奏层配置"""
    base_rate: str = "-15%"
    opening_delta: Optional[str] = "-5%"
    ending_delta: Optional[str] = "-5%"
    transition_duration: Optional[str] = "300ms"


@dataclass
class MoodConfig:
    """情绪层配置"""
    pitch: str = "+1%"
    emphasis: Optional[str] = None
    breathing: bool = True
    thinking_pause: bool = False
    volume: Optional[str] = None


@dataclass
class StructureConfig:
    """结构层配置"""
    comma_pause: str = "350ms"
    sentence_pause: str = "700ms"
    paragraph_pause: str = "1200ms"
    max_sentence_len: int = 150
    auto_split_long_sentence: bool = True
    chapter_pause: Optional[str] = "2000ms"
    dialog_pause: Optional[str] = "500ms"


@dataclass
class SSMLConfig:
    """SSML 完整配置"""
    voice: VoiceConfig = field(default_factory=VoiceConfig)
    pace: PaceConfig = field(default_factory=PaceConfig)
    mood: MoodConfig = field(default_factory=MoodConfig)
    structure: StructureConfig = field(default_factory=StructureConfig)
    name: str = "Default"
    description: str = "默认 SSML 配置"
    version: str = "1.0"


class SimpleSSMLGenerator:
    """简化的 SSML 生成器，专注于正确生成 SSML"""

    def __init__(self, config: SSMLConfig):
        self.config = config

    def generate_ssml(self, text: str) -> str:
        """生成 SSML"""
        # 文本预处理
        text = self._preprocess_text(text)

        # 分割段落
        paragraphs = self._split_paragraphs(text)

        # 构建SSML，不包含XML声明，edge-tts会直接处理speak标签
        ssml_parts = []
        ssml_parts.append('<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="zh-CN">')

        # voice标签
        voice_attrs = f'name="{self.config.voice.name}"'
        if self.config.voice.style:
            voice_attrs += f' style="{self.config.voice.style}"'
        if self.config.voice.role:
            voice_attrs += f' role="{self.config.voice.role}"'

        ssml_parts.append(f'<voice {voice_attrs}>')

        # 处理段落
        for i, paragraph in enumerate(paragraphs):
            if i > 0:
                ssml_parts.append(f'<break time="{self.config.structure.paragraph_pause}"/>')

            # 处理段落内容
            paragraph_ssml = self._process_paragraph(paragraph, i == 0, i == len(paragraphs) - 1)
            ssml_parts.append(paragraph_ssml)

        ssml_parts.append('</voice>')
        ssml_parts.append('</speak>')

        # 组装成紧凑的SSML字符串，不使用换行符
        ssml = ''.join(ssml_parts)
        return ssml

    def generate_ssml_content_only(self, text: str) -> str:
        """只生成SSML内容部分，不包含外层<speak>和<voice>标签（用于分段处理）"""
        # 文本预处理
        text = self._preprocess_text(text)

        # 分割段落
        paragraphs = self._split_paragraphs(text)

        # 只生成内容部分
        content_parts = []

        # 处理段落内容
        for i, paragraph in enumerate(paragraphs):
            if i > 0:
                content_parts.append(f'<break time="{self.config.structure.paragraph_pause}"/>')

            # 处理段落内的句子和停顿
            processed_paragraph = self._process_paragraph_content(paragraph)
            content_parts.append(processed_paragraph)

        return ''.join(content_parts)

    def _process_paragraph_content(self, paragraph: str) -> str:
        """处理段落内容，只返回prosody部分"""
        if not paragraph.strip():
            return ""

        # 按句子分割
        import re
        sentences = re.split(r'([。！？.!?；;])', paragraph)
        processed_parts = []

        for i in range(0, len(sentences), 2):
            if i < len(sentences):
                sentence = sentences[i]
                if i + 1 < len(sentences):
                    sentence += sentences[i + 1]

                if sentence.strip():
                    # 创建prosody标签
                    prosody_attrs = f'rate="{self.config.pace.base_rate}" pitch="{self.config.mood.pitch}"'
                    processed_parts.append(f'<prosody {prosody_attrs}>{sentence}</prosody>')

        return ''.join(processed_parts)

    def _preprocess_text(self, text: str) -> str:
        """文本预处理"""
        # 转义 XML 特殊字符
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('"', '&quot;')
        text = text.replace("'", '&apos;')

        # 标准化换行
        text = text.replace('\r\n', '\n').replace('\r', '\n')

        # 清理多余空白
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)

        return text.strip()

    def _split_paragraphs(self, text: str) -> List[str]:
        """分割段落"""
        paragraphs = text.split('\n\n')
        return [p.strip() for p in paragraphs if p.strip()]

    def _process_paragraph(self, paragraph: str, is_first: bool, is_last: bool) -> str:
        """处理段落"""
        sentences = self._split_sentences(paragraph)

        ssml_parts = []

        for i, sentence in enumerate(sentences):
            if i > 0:
                ssml_parts.append(f'<break time="{self.config.structure.sentence_pause}"/>')

            # 处理句子
            sentence_ssml = self._process_sentence(sentence, is_first and i == 0, is_last and i == len(sentences) - 1)
            ssml_parts.append(sentence_ssml)

        return ''.join(ssml_parts)

    def _split_sentences(self, text: str) -> List[str]:
        """分割句子"""
        # 按标点分割
        sentences = re.split(r'([。！？.!?])', text)

        result = []
        for i in range(0, len(sentences), 2):
            if i + 1 < len(sentences):
                sentence = sentences[i] + sentences[i + 1]
            else:
                sentence = sentences[i]

            sentence = sentence.strip()
            if sentence:
                # 检查长度
                if len(sentence) > self.config.structure.max_sentence_len:
                    # 进一步分割长句
                    sub_sentences = self._split_long_sentence(sentence)
                    result.extend(sub_sentences)
                else:
                    result.append(sentence)

        return result

    def _split_long_sentence(self, sentence: str) -> List[str]:
        """分割长句"""
        # 优先在逗号分割
        if '，' in sentence:
            parts = sentence.split('，')
            result = []
            current = ""

            for part in parts:
                if len(current + part + '，') <= self.config.structure.max_sentence_len:
                    current += (part + '，' if current else part)
                else:
                    if current:
                        result.append(current.strip())
                    current = part

            if current:
                result.append(current.strip())

            return [r for r in result if r]

        # 如果无法分割，强制按长度
        result = []
        for i in range(0, len(sentence), self.config.structure.max_sentence_len):
            result.append(sentence[i:i + self.config.structure.max_sentence_len])

        return result

    def _process_sentence(self, sentence: str, is_opening: bool, is_ending: bool) -> str:
        """处理句子"""
        # 计算语速
        rate = self._calculate_rate(is_opening, is_ending)

        # 构建 prosody 标签
        prosody_attrs = f'rate="{rate}"'
        if self.config.mood.pitch and self.config.mood.pitch != "0%":
            prosody_attrs += f' pitch="{self.config.mood.pitch}"'
        if self.config.mood.volume:
            prosody_attrs += f' volume="{self.config.mood.volume}"'

        # 处理句子内的停顿
        processed_sentence = self._insert_sentence_breaks(sentence)

        return f'<prosody {prosody_attrs}>{processed_sentence}</prosody>'

    def _calculate_rate(self, is_opening: bool, is_ending: bool) -> str:
        """计算语速"""
        base_rate = self.config.pace.base_rate

        # 解析基础语速
        rate_match = re.match(r'([+-]?)(\d+)%', base_rate)
        if not rate_match:
            return base_rate

        sign = rate_match.group(1)
        base_value = int(rate_match.group(2))

        # 转换为有符号值
        if sign == '-':
            base_value = -base_value  # 负值表示慢速
        elif sign == '+':
            base_value = base_value   # 正值表示快速
        else:
            base_value = -base_value  # 默认负值表示慢速

        # 应用开头调整
        if is_opening and self.config.pace.opening_delta:
            delta_match = re.match(r'([+-]?)(\d+)%', self.config.pace.opening_delta)
            if delta_match:
                delta_value = int(delta_match.group(2))
                if delta_match.group(1) == '-':
                    base_value -= delta_value  # 更慢
                else:
                    base_value += delta_value  # 更快

        # 应用结尾调整
        if is_ending and self.config.pace.ending_delta:
            delta_match = re.match(r'([+-]?)(\d+)%', self.config.pace.ending_delta)
            if delta_match:
                delta_value = int(delta_match.group(2))
                if delta_match.group(1) == '-':
                    base_value -= delta_value  # 更慢
                else:
                    base_value += delta_value  # 更快

        return f"{base_value:+d}%"

    def _insert_sentence_breaks(self, sentence: str) -> str:
        """在句子中插入停顿"""
        # 替换逗号为停顿
        sentence = sentence.replace('，', f'，<break time="{self.config.structure.comma_pause}"/>')
        sentence = sentence.replace('、', f'、<break time="{self.config.structure.comma_pause}"/>')

        # 处理其他标点（句子结束的标点已经在更高层处理）
        return sentence

    def _format_ssml(self, ssml: str) -> str:
        """格式化 SSML - 返回紧凑格式避免edge-tts解析问题"""
        # 移除多余的空白字符，返回紧凑的SSML
        import re
        ssml = re.sub(r'>\s+<', '><', ssml)  # 移除标签间的空白
        ssml = re.sub(r'\n\s*', '', ssml)   # 移除换行符和缩进
        return ssml.strip()


# 预设配置（与原版本相同）
BEDTIME_SOFT = SSMLConfig(
    name="BEDTIME_SOFT",
    description="极轻柔的睡前故事配置，适合助眠",
    voice=VoiceConfig(
        name="zh-CN-XiaoxiaoNeural",
        style="gentle",
        role="youngadultfemale"
    ),
    pace=PaceConfig(
        base_rate="-25%",
        opening_delta="-5%",
        ending_delta="-5%",
        transition_duration="500ms"
    ),
    mood=MoodConfig(
        pitch="-5%",
        emphasis="none",
        breathing=True,
        thinking_pause=True,
        volume="soft"
    ),
    structure=StructureConfig(
        comma_pause="500ms",
        sentence_pause="1000ms",
        paragraph_pause="2000ms",
        max_sentence_len=120,
        auto_split_long_sentence=True,
        chapter_pause="3000ms",
        dialog_pause="800ms"
    )
)

BEDTIME_BALANCED = SSMLConfig(
    name="BEDTIME_BALANCED",
    description="平衡的睡前故事配置，通用推荐",
    voice=VoiceConfig(
        name="zh-CN-XiaoxiaoNeural",
        style="calm",
        role=None
    ),
    pace=PaceConfig(
        base_rate="-15%",
        opening_delta="-3%",
        ending_delta="-3%",
        transition_duration="300ms"
    ),
    mood=MoodConfig(
        pitch="+1%",
        emphasis="moderate",
        breathing=True,
        thinking_pause=False,
        volume=None
    ),
    structure=StructureConfig(
        comma_pause="350ms",
        sentence_pause="700ms",
        paragraph_pause="1200ms",
        max_sentence_len=150,
        auto_split_long_sentence=True,
        chapter_pause="2000ms",
        dialog_pause="500ms"
    )
)

BEDTIME_FAIRY = SSMLConfig(
    name="BEDTIME_FAIRY",
    description="童话故事配置，稍活泼有趣",
    voice=VoiceConfig(
        name="zh-CN-XiaoxiaoNeural",
        style="cheerful",
        role="girl"
    ),
    pace=PaceConfig(
        base_rate="-10%",
        opening_delta="0%",
        ending_delta="-2%",
        transition_duration="200ms"
    ),
    mood=MoodConfig(
        pitch="+5%",
        emphasis="moderate",
        breathing=True,
        thinking_pause=False,
        volume="default"
    ),
    structure=StructureConfig(
        comma_pause="300ms",
        sentence_pause="600ms",
        paragraph_pause="1000ms",
        max_sentence_len=160,
        auto_split_long_sentence=True,
        chapter_pause="1500ms",
        dialog_pause="400ms"
    )
)


# 恐怖悬疑配置
HORROR_SUSPENSE = SSMLConfig(
    name="HORROR_SUSPENSE",
    description="恐怖悬疑配置，低沉缓慢，营造紧张氛围",
    voice=VoiceConfig(
        name="zh-CN-XiaoxiaoNeural",
        style="calm",
        role=None
    ),
    pace=PaceConfig(
        base_rate="-30%",  # 非常慢
        opening_delta="-10%",
        ending_delta="-10%",
        transition_duration="500ms"
    ),
    mood=MoodConfig(
        pitch="-30%",  # 低沉
        emphasis="strong",
        breathing=False,
        thinking_pause=True,
        volume="soft"  # 轻声
    ),
    structure=StructureConfig(
        comma_pause="600ms",  # 长停顿
        sentence_pause="1500ms",
        paragraph_pause="3000ms",
        max_sentence_len=120,
        auto_split_long_sentence=True,
        chapter_pause="4000ms",
        dialog_pause="1500ms"
    )
)

# 浪漫温馨配置
ROMANTIC = SSMLConfig(
    name="ROMANTIC",
    description="浪漫温馨配置，温柔甜美，适合爱情故事",
    voice=VoiceConfig(
        name="zh-CN-XiaoxiaoNeural",
        style="gentle",
        role="youngadultfemale"
    ),
    pace=PaceConfig(
        base_rate="-10%",
        opening_delta="0%",
        ending_delta="-5%",
        transition_duration="200ms"
    ),
    mood=MoodConfig(
        pitch="+5%",  # 轻快高音
        emphasis="moderate",
        breathing=True,
        thinking_pause=False,
        volume=None
    ),
    structure=StructureConfig(
        comma_pause="300ms",
        sentence_pause="600ms",
        paragraph_pause="1000ms",
        max_sentence_len=160,
        auto_split_long_sentence=True,
        chapter_pause="1500ms",
        dialog_pause="500ms"
    )
)

# 激昂热血配置
PASSIONATE = SSMLConfig(
    name="PASSIONATE",
    description="激昂热血配置，快速有力，适合战斗场景",
    voice=VoiceConfig(
        name="zh-CN-YunyangNeural",  # 男声，更有力量
        style="cheerful",
        role=None
    ),
    pace=PaceConfig(
        base_rate="+20%",  # 快速
        opening_delta="+10%",
        ending_delta="+5%",
        transition_duration="200ms"
    ),
    mood=MoodConfig(
        pitch="+15%",  # 高音
        emphasis="strong",
        breathing=False,
        thinking_pause=False,
        volume="loud"  # 大声
    ),
    structure=StructureConfig(
        comma_pause="200ms",  # 短停顿
        sentence_pause="400ms",
        paragraph_pause="800ms",
        max_sentence_len=150,
        auto_split_long_sentence=True,
        chapter_pause="1000ms",
        dialog_pause="300ms"
    )
)

# 悲伤抑郁配置
MELANCHOLY = SSMLConfig(
    name="MELANCHOLY",
    description="悲伤抑郁配置，低沉缓慢，压抑感人",
    voice=VoiceConfig(
        name="zh-CN-XiaoxiaoNeural",
        style="sad",
        role=None
    ),
    pace=PaceConfig(
        base_rate="-25%",  # 缓慢
        opening_delta="-5%",
        ending_delta="-10%",  # 结尾更慢
        transition_duration="400ms"
    ),
    mood=MoodConfig(
        pitch="-20%",  # 低音
        emphasis="reduced",
        breathing=True,
        thinking_pause=True,
        volume="soft"
    ),
    structure=StructureConfig(
        comma_pause="500ms",
        sentence_pause="1200ms",
        paragraph_pause="2500ms",
        max_sentence_len=130,
        auto_split_long_sentence=True,
        chapter_pause="3500ms",
        dialog_pause="1000ms"
    )
)

# 新闻报道配置
NEWS = SSMLConfig(
    name="NEWS",
    description="新闻报道配置，专业平稳，清晰准确",
    voice=VoiceConfig(
        name="zh-CN-XiaoyiNeural",  # 专业女声
        style=None,
        role=None
    ),
    pace=PaceConfig(
        base_rate="+5%",  # 稍快
        opening_delta="0%",
        ending_delta="0%",
        transition_duration="100ms"
    ),
    mood=MoodConfig(
        pitch="+2%",
        emphasis="moderate",
        breathing=False,
        thinking_pause=False,
        volume=None
    ),
    structure=StructureConfig(
        comma_pause="250ms",
        sentence_pause="500ms",
        paragraph_pause="800ms",
        max_sentence_len=180,
        auto_split_long_sentence=True,
        chapter_pause="1200ms",
        dialog_pause="400ms"
    )
)

# 教学讲解配置
EDUCATIONAL = SSMLConfig(
    name="EDUCATIONAL",
    description="教学讲解配置，清晰稳重，有条理",
    voice=VoiceConfig(
        name="zh-CN-YunxiNeural",  # 稳重男声
        style=None,
        role=None
    ),
    pace=PaceConfig(
        base_rate="-5%",  # 稍慢，便于理解
        opening_delta="0%",
        ending_delta="0%",
        transition_duration="200ms"
    ),
    mood=MoodConfig(
        pitch="+3%",
        emphasis="moderate",
        breathing=False,
        thinking_pause=True,
        volume=None
    ),
    structure=StructureConfig(
        comma_pause="400ms",
        sentence_pause="700ms",
        paragraph_pause="1200ms",
        max_sentence_len=140,
        auto_split_long_sentence=True,
        chapter_pause="2000ms",
        dialog_pause="600ms"
    )
)


# 预设配置字典
PRESET_CONFIGS = {
    # 睡前故事系列
    "BEDTIME_SOFT": BEDTIME_SOFT,
    "BEDTIME_BALANCED": BEDTIME_BALANCED,
    "BEDTIME_FAIRY": BEDTIME_FAIRY,
    # 情感系列
    "HORROR_SUSPENSE": HORROR_SUSPENSE,
    "ROMANTIC": ROMANTIC,
    "PASSIONATE": PASSIONATE,
    "MELANCHOLY": MELANCHOLY,
    # 通用系列
    "NEWS": NEWS,
    "EDUCATIONAL": EDUCATIONAL,
}


def generate_ssml(text: str, config: Union[str, SSMLConfig]) -> str:
    """
    生成 SSML 的便捷函数

    Args:
        text: 输入文本
        config: SSML 配置对象或预设名称

    Returns:
        SSML 字符串
    """
    if isinstance(config, str):
        if config not in PRESET_CONFIGS:
            raise ValueError(f"Unknown preset: {config}. Available: {list(PRESET_CONFIGS.keys())}")
        config = PRESET_CONFIGS[config]

    generator = SimpleSSMLGenerator(config)
    return generator.generate_ssml(text)


if __name__ == "__main__":
    # 测试示例
    sample_text = "从前，有一个小女孩。她叫小红，每天都很开心。"

    print("=== 简化版 SSML 生成器测试 ===")

    for preset in ["BEDTIME_SOFT", "BEDTIME_BALANCED", "BEDTIME_FAIRY"]:
        print(f"\n📝 {preset}:")
        ssml = generate_ssml(sample_text, preset)
        print(ssml)