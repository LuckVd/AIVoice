"""
SSML 生成器模块 - 专为睡前故事和长篇叙事音频设计的可扩展 SSML 生成系统

作者: AI Assistant
日期: 2024-12-18
版本: 1.0.0

主要功能:
- 分层参数配置 (Voice/Pace/Mood/Structure)
- 智能文本预处理和分段
- 自适应停顿插入
- 多种预设风格支持
"""

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union
from xml.dom import minidom


@dataclass
class VoiceConfig:
    """声音层配置 - 控制语音引擎和声音特性"""
    name: str = "zh-CN-XiaoxiaoNeural"  # 语音模型名称
    style: Optional[str] = None  # 语音风格: calm/assistant/cheerful/customerservice/emo
    fallback: Optional[str] = None  # 备用语音模型
    role: Optional[str] = None  # 角色扮演: girl/boy/youngadultfemale/seniorfemale


@dataclass
class PaceConfig:
    """节奏层配置 - 控制叙事节奏和语速变化"""
    base_rate: str = "-15%"  # 基础语速
    opening_delta: Optional[str] = "-5%"  # 开头额外放慢
    ending_delta: Optional[str] = "-5%"  # 结尾额外放慢
    transition_duration: Optional[str] = "300ms"  # 过渡停顿时长


@dataclass
class MoodConfig:
    """情绪层配置 - 控制语气、情绪和表达方式"""
    pitch: str = "+1%"  # 基础音调
    emphasis: Optional[str] = None  # 强调程度: none/moderate/strong/reduced
    breathing: bool = True  # 是否插入自然呼吸停顿
    thinking_pause: bool = False  # 是否插入思考感停顿
    volume: Optional[str] = None  # 音量控制: default/silent/0-100


@dataclass
class StructureConfig:
    """结构层配置 - 控制文本结构和停顿规则"""
    comma_pause: str = "350ms"  # 逗号停顿
    sentence_pause: str = "700ms"  # 句号停顿
    paragraph_pause: str = "1200ms"  # 段落停顿
    max_sentence_len: int = 150  # 超长句自动拆分阈值
    auto_split_long_sentence: bool = True
    chapter_pause: Optional[str] = "2000ms"  # 章节停顿
    dialog_pause: Optional[str] = "500ms"  # 对话停顿


@dataclass
class SSMLConfig:
    """SSML 完整配置 - 包含所有层级的配置"""
    voice: VoiceConfig = field(default_factory=VoiceConfig)
    pace: PaceConfig = field(default_factory=PaceConfig)
    mood: MoodConfig = field(default_factory=MoodConfig)
    structure: StructureConfig = field(default_factory=StructureConfig)

    # 元数据
    name: str = "Default"
    description: str = "默认 SSML 配置"
    version: str = "1.0"


class TextProcessor:
    """文本预处理器 - 负责文本清理、分段和特殊字符处理"""

    # 需要转义的 XML 特殊字符
    XML_ESCAPE_MAP = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&apos;'
    }

    # 中文标点映射到停顿类型
    PUNCTUATION_PAUSE_MAP = {
        '，': 'comma',
        '。': 'sentence',
        '！': 'sentence',
        '？': 'sentence',
        '；': 'sentence',
        '：': 'sentence',
        '、': 'comma',
        '.': 'sentence',  # 英文句号
        ',': 'comma',    # 英文逗号
        '!': 'sentence',  # 英文感叹号
        '?': 'sentence',  # 英文问号
        ';': 'sentence',  # 英文分号
        ':': 'sentence',  # 英文冒号
    }

    @staticmethod
    def escape_xml(text: str) -> str:
        """转义 XML 特殊字符"""
        for char, escaped in TextProcessor.XML_ESCAPE_MAP.items():
            text = text.replace(char, escaped)
        return text

    @staticmethod
    def normalize_text(text: str) -> str:
        """标准化文本格式"""
        # 统一换行符
        text = text.replace('\r\n', '\n').replace('\r', '\n')

        # 清理多余空白
        text = re.sub(r'\n{3,}', '\n\n', text)  # 多个空行变成两个
        text = re.sub(r'[ \t]+', ' ', text)  # 多个空格变成一个
        text = re.sub(r' +\n', '\n', text)  # 行尾空格清理
        text = re.sub(r'\n +', '\n', text)  # 行首空格清理

        return text.strip()

    @staticmethod
    def split_paragraphs(text: str) -> List[str]:
        """分割段落"""
        paragraphs = text.split('\n\n')
        return [p.strip() for p in paragraphs if p.strip()]

    @staticmethod
    def split_sentences(text: str, max_len: int = 150) -> List[str]:
        """智能分割句子，支持超长句自动拆分"""
        # 使用正则表达式分割句子，保留标点
        sentences = re.split(r'([。！？.!?])', text)

        # 重组句子和标点
        result = []
        for i in range(0, len(sentences), 2):
            if i + 1 < len(sentences):
                sentence = sentences[i] + sentences[i + 1]
            else:
                sentence = sentences[i]

            sentence = sentence.strip()
            if not sentence:
                continue

            # 检查是否需要进一步拆分
            if len(sentence) > max_len:
                sub_sentences = TextProcessor._split_long_sentence(sentence, max_len)
                result.extend(sub_sentences)
            else:
                result.append(sentence)

        return result

    @staticmethod
    def _split_long_sentence(sentence: str, max_len: int) -> List[str]:
        """拆分超长句子"""
        # 优先在逗号、分号等位置拆分
        split_points = ['，', '、', ';', '；', ' ', '  ']

        for split_char in split_points:
            if split_char in sentence:
                parts = sentence.split(split_char)
                result = []
                current = ""

                for part in parts:
                    if len(current + part + split_char) <= max_len:
                        current += (part + split_char if current else part)
                    else:
                        if current:
                            result.append(current.strip())
                        current = part

                if current:
                    result.append(current.strip())

                if len(result) > 1:
                    return result

        # 如果无法拆分，强制按长度拆分
        result = []
        for i in range(0, len(sentence), max_len):
            result.append(sentence[i:i + max_len])

        return result


class SSMLGenerator:
    """SSML 生成器核心类 - 将文本和配置转换为 SSML"""

    def __init__(self, config: SSMLConfig):
        self.config = config
        self.processor = TextProcessor()

    def generate_ssml(self, text: str) -> str:
        """
        生成完整的 SSML 输出

        Args:
            text: 输入文本

        Returns:
            格式化的 SSML 字符串
        """
        # 文本预处理
        normalized_text = self.processor.normalize_text(text)
        paragraphs = self.processor.split_paragraphs(normalized_text)

        # 创建 SSML 根元素
        speak_elem = ET.Element("speak", xmlns="http://www.w3.org/2001/10/synthesis")
        speak_elem.set("version", "1.0")
        speak_elem.set("xml:lang", "zh-CN")

        # 创建 voice 元素
        voice_attrs = {"name": self.config.voice.name}
        if self.config.voice.style:
            voice_attrs["style"] = self.config.voice.style
        if self.config.voice.role:
            voice_attrs["role"] = self.config.voice.role

        voice_elem = ET.SubElement(speak_elem, "voice", voice_attrs)

        # 处理每个段落
        for i, paragraph in enumerate(paragraphs):
            # 段落间停顿
            if i > 0:
                ET.SubElement(voice_elem, "break", {
                    "time": self.config.structure.paragraph_pause
                })

            # 处理段落内容
            self._process_paragraph(voice_elem, paragraph, i == 0, i == len(paragraphs) - 1)

        # 格式化输出
        rough_string = ET.tostring(speak_elem, encoding='unicode')
        reparsed = minidom.parseString(rough_string)

        # 美化输出，添加缩进
        return self._format_ssml(reparsed.toprettyxml(indent="  "))

    def _process_paragraph(self, parent_elem: ET.Element, paragraph: str,
                          is_first_para: bool, is_last_para: bool) -> None:
        """处理单个段落"""
        sentences = self.processor.split_sentences(paragraph, self.config.structure.max_sentence_len)

        for i, sentence in enumerate(sentences):
            # 句子间停顿
            if i > 0:
                ET.SubElement(parent_elem, "break", {
                    "time": self.config.structure.sentence_pause
                })

            # 处理句子
            self._process_sentence(parent_elem, sentence, is_first_para and i == 0,
                                 is_last_para and i == len(sentences) - 1)

    def _process_sentence(self, parent_elem: ET.Element, sentence: str,
                         is_opening: bool, is_ending: bool) -> None:
        """处理单个句子，应用语速和音调变化"""
        # 计算当前句子的语速
        current_rate = self._calculate_rate(is_opening, is_ending)

        # 创建 prosody 元素
        prosody_attrs = {"rate": current_rate}

        # 应用音调
        if self.config.mood.pitch and self.config.mood.pitch != "0%":
            prosody_attrs["pitch"] = self.config.mood.pitch

        # 应用音量
        if self.config.mood.volume:
            prosody_attrs["volume"] = self.config.mood.volume

        prosody_elem = ET.SubElement(parent_elem, "prosody", prosody_attrs)

        # 应用强调
        if self.config.mood.emphasis and self.config.mood.emphasis != "none":
            # 找出需要强调的关键词（简单实现：形容词、动词等）
            emphasized_sentence = self._apply_emphasis(sentence)
            if emphasized_sentence != sentence:
                # 如果有强调，使用 emphasis 元素
                self._add_emphasized_content(prosody_elem, emphasized_sentence)
            else:
                # 没有强调，直接添加文本
                self._add_text_with_pauses(prosody_elem, sentence)
        else:
            # 直接添加带停顿的文本
            self._add_text_with_pauses(prosody_elem, sentence)

        # 添加呼吸停顿
        if self.config.mood.breathing and not is_ending:
            ET.SubElement(parent_elem, "break", {"time": "200ms"})

    def _calculate_rate(self, is_opening: bool, is_ending: bool) -> str:
        """计算当前语境下的语速"""
        base_rate = self.config.pace.base_rate

        # 提取数值部分
        rate_match = re.match(r'([+-]?)(\d+)%', base_rate)
        if not rate_match:
            return base_rate

        sign = rate_match.group(1)
        base_value = int(rate_match.group(2))

        # 应用开头或结尾的额外调整
        if is_opening and self.config.pace.opening_delta:
            delta_match = re.match(r'([+-]?)(\d+)%', self.config.pace.opening_delta)
            if delta_match:
                delta_sign = delta_match.group(1)
                delta_value = int(delta_match.group(2))

                if delta_sign == '-':
                    base_value += delta_value  # 更负表示更慢
                else:
                    base_value -= delta_value  # 正值表示要加快

        if is_ending and self.config.pace.ending_delta:
            delta_match = re.match(r'([+-]?)(\d+)%', self.config.pace.ending_delta)
            if delta_match:
                delta_sign = delta_match.group(1)
                delta_value = int(delta_match.group(2))

                if delta_sign == '-':
                    base_value += delta_value
                else:
                    base_value -= delta_value

        # 重新构建语速字符串
        if base_value >= 0:
            return f"+{base_value}%"
        else:
            return f"{base_value}%"

    def _add_text_with_pauses(self, parent_elem: ET.Element, text: str) -> None:
        """添加文本，自动插入停顿"""
        # 转义 XML 特殊字符
        escaped_text = self.processor.escape_xml(text)

        # 分割文本片段
        segments = []
        current_segment = ""

        for char in escaped_text:
            if char in self.processor.PUNCTUATION_PAUSE_MAP:
                # 添加当前文本片段
                if current_segment:
                    segments.append(("text", current_segment))
                    current_segment = ""
                # 添加标点
                segments.append(("punct", char))
                # 添加停顿类型
                pause_type = self.processor.PUNCTUATION_PAUSE_MAP[char]
                if pause_type == 'comma':
                    pause_time = self.config.structure.comma_pause
                elif pause_type == 'sentence':
                    pause_time = self.config.structure.sentence_pause
                else:
                    pause_time = self.config.structure.comma_pause
                segments.append(("break", pause_time))
            else:
                current_segment += char

        # 添加最后的文本片段
        if current_segment:
            segments.append(("text", current_segment))

        # 构建XML结构
        current_text = ""
        for seg_type, seg_content in segments:
            if seg_type == "text":
                current_text += seg_content
            elif seg_type == "punct":
                # 设置当前文本
                if current_text:
                    if parent_elem.text:
                        parent_elem.text += current_text
                    else:
                        parent_elem.text = current_text
                    current_text = ""
                # 添加标点
                if parent_elem.text:
                    parent_elem.text += seg_content
                else:
                    parent_elem.text = seg_content
            elif seg_type == "break":
                # 设置当前文本
                if current_text:
                    if parent_elem.text:
                        parent_elem.text += current_text
                    else:
                        parent_elem.text = current_text
                    current_text = ""
                # 添加停顿
                ET.SubElement(parent_elem, "break", {"time": seg_content})

        # 添加剩余的文本
        if current_text:
            if parent_elem.text:
                parent_elem.text += current_text
            else:
                parent_elem.text = current_text

    def _apply_emphasis(self, text: str) -> str:
        """应用强调规则（简单实现）"""
        # 这里可以实现更复杂的强调逻辑
        # 例如识别关键词、形容词、动词等
        # 当前简单实现：对某些词汇添加强调标记
        emphasis_keywords = ['非常', '特别', '极了', '真的', '重要', '关键', '终于', '突然']

        for keyword in emphasis_keywords:
            text = text.replace(keyword, f"<emphasis level='{self.config.mood.emphasis}'>{keyword}</emphasis>")

        return text

    def _add_emphasized_content(self, parent_elem: ET.Element, text: str) -> None:
        """处理包含强调标记的文本"""
        # 简单实现：直接设置包含 SSML 标记的文本
        # 在实际应用中，可能需要更复杂的 XML 解析
        escaped_text = self.processor.escape_xml(
            text.replace("<emphasis level='moderate'>", "<emphasis level='moderate'>")
                .replace("</emphasis>", "</emphasis>")
        )
        parent_elem.text = escaped_text

    def _format_ssml(self, ssml_string: str) -> str:
        """美化 SSML 输出格式"""
        # 移除空行
        lines = ssml_string.split('\n')
        formatted_lines = []

        for line in lines:
            line = line.strip()
            if line and not line.startswith('<?xml'):
                formatted_lines.append(line)

        return '\n'.join(formatted_lines)


# 预设配置定义

BEDTIME_SOFT = SSMLConfig(
    name="BEDTIME_SOFT",
    description="极轻柔的睡前故事配置，适合助眠",
    voice=VoiceConfig(
        name="zh-CN-XiaoxiaoNeural",
        style="gentle",
        role="youngadultfemale"
    ),
    pace=PaceConfig(
        base_rate="-25%",  # 很慢的语速
        opening_delta="-5%",
        ending_delta="-5%",
        transition_duration="500ms"
    ),
    mood=MoodConfig(
        pitch="-5%",  # 稍低的音调
        emphasis="none",  # 避免强调
        breathing=True,
        thinking_pause=True,
        volume="soft"  # 轻柔音量
    ),
    structure=StructureConfig(
        comma_pause="500ms",  # 较长的逗号停顿
        sentence_pause="1000ms",  # 很长的句子停顿
        paragraph_pause="2000ms",  # 超长的段落停顿
        max_sentence_len=120,  # 更短的句子
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
        base_rate="-15%",  # 适中的慢速
        opening_delta="-3%",
        ending_delta="-3%",
        transition_duration="300ms"
    ),
    mood=MoodConfig(
        pitch="+1%",  # 自然音调
        emphasis="moderate",  # 适度强调
        breathing=True,
        thinking_pause=False,
        volume=None  # 默认音量
    ),
    structure=StructureConfig(
        comma_pause="350ms",  # 适中的逗号停顿
        sentence_pause="700ms",  # 适中的句子停顿
        paragraph_pause="1200ms",  # 适中的段落停顿
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
        base_rate="-10%",  # 相对快一点
        opening_delta="0%",
        ending_delta="-2%",
        transition_duration="200ms"
    ),
    mood=MoodConfig(
        pitch="+5%",  # 稍高的音调
        emphasis="moderate",  # 适度强调
        breathing=True,
        thinking_pause=False,
        volume="default"
    ),
    structure=StructureConfig(
        comma_pause="300ms",  # 较短的停顿
        sentence_pause="600ms",
        paragraph_pause="1000ms",
        max_sentence_len=160,
        auto_split_long_sentence=True,
        chapter_pause="1500ms",
        dialog_pause="400ms"
    )
)

# 预设配置字典
PRESET_CONFIGS = {
    "BEDTIME_SOFT": BEDTIME_SOFT,
    "BEDTIME_BALANCED": BEDTIME_BALANCED,
    "BEDTIME_FAIRY": BEDTIME_FAIRY,
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

    generator = SSMLGenerator(config)
    return generator.generate_ssml(text)


# 使用示例
if __name__ == "__main__":
    # 示例文本
    sample_text = """
    从前，在一个美丽的小村庄里，住着一只可爱的小兔子。它的名字叫小白，因为它全身都是雪白的毛茸茸的毛。

    有一天，小白决定去森林里探险。它带上了最爱的胡萝卜，告别了妈妈，踏上了未知的旅程。

    森林里真的很美！有高高的大树，有五颜六色的花朵，还有唱着歌的小鸟。小白开心地跳来跳去，这里看看，那里瞧瞧。
    """

    # 生成三种不同风格的 SSML
    print("=== BEDTIME_SOFT SSML ===")
    soft_ssml = generate_ssml(sample_text, "BEDTIME_SOFT")
    print(soft_ssml)

    print("\n=== BEDTIME_BALANCED SSML ===")
    balanced_ssml = generate_ssml(sample_text, "BEDTIME_BALANCED")
    print(balanced_ssml)

    print("\n=== BEDTIME_FAIRY SSML ===")
    fairy_ssml = generate_ssml(sample_text, "BEDTIME_FAIRY")
    print(fairy_ssml)

    # 自定义配置示例
    print("\n=== CUSTOM CONFIG SSML ===")
    custom_config = SSMLConfig(
        name="CUSTOM_EXAMPLE",
        voice=VoiceConfig(name="zh-CN-YunyangNeural", style="narrator"),
        pace=PaceConfig(base_rate="-20%"),
        mood=MoodConfig(pitch="0%", emphasis="strong"),
        structure=StructureConfig(comma_pause="400ms", sentence_pause="800ms")
    )

    custom_ssml = generate_ssml("这是一个自定义配置的示例。", custom_config)
    print(custom_ssml)