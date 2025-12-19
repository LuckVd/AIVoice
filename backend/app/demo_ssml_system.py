#!/usr/bin/env python3
"""
SSML 生成系统完整演示

这个脚本演示了如何使用新的 SSML 生成系统来创建不同风格的睡前故事音频
"""

import asyncio
from pathlib import Path
import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.ssml_generator import (
    generate_ssml,
    SSMLConfig,
    VoiceConfig,
    PaceConfig,
    MoodConfig,
    StructureConfig,
    PRESET_CONFIGS
)


def demonstrate_ssml_generation():
    """演示 SSML 生成功能"""
    print("🎙️ SSML 生成系统演示")
    print("=" * 60)

    # 示例故事
    story = """
    在一个宁静的夜晚，小星星闪烁着温柔的光芒。月亮婆婆慢慢地升起来了，她照看着整个沉睡的世界。

    森林里的小动物们都回到了温暖的家中。小兔子在妈妈的怀抱里，听着最动听的睡前故事。

    故事讲的是：有一颗勇敢的小种子，它经历了风雨，最终长成了参天大树，为所有的小鸟提供了家园。

    晚安，亲爱的小朋友们。愿你们的梦里，都有美丽的星星和温暖的家。
    """

    print("📖 原始故事:")
    print(story[:200] + "...\n")

    # 演示三种预设配置
    configs = [
        ("BEDTIME_SOFT", "极轻柔助眠版本"),
        ("BEDTIME_BALANCED", "平衡故事版本"),
        ("BEDTIME_FAIRY", "童话活泼版本")
    ]

    for config_name, description in configs:
        print(f"🎵 {description} ({config_name}):")
        print("-" * 40)

        # 获取配置信息
        config = PRESET_CONFIGS[config_name]
        print(f"语音: {config.voice.name}")
        print(f"风格: {config.voice.style}")
        print(f"语速: {config.pace.base_rate}")
        print(f"音调: {config.mood.pitch}")
        print(f"逗号停顿: {config.structure.comma_pause}")
        print(f"句子停顿: {config.structure.sentence_pause}")

        # 生成 SSML
        ssml = generate_ssml(story, config_name)
        print(f"\n📄 生成的 SSML (前 300 字符):")
        print(ssml[:300] + "...")
        print(f"完整 SSML 长度: {len(ssml)} 字符\n")

    return story


def demonstrate_custom_config():
    """演示自定义配置"""
    print("🎨 自定义配置演示")
    print("=" * 60)

    # 创建自定义配置
    custom_config = SSMLConfig(
        name="CUSTOM_STORYTELLER",
        description="专业故事讲述者配置",
        voice=VoiceConfig(
            name="zh-CN-YunxiNeural",  # 云希语音
            style="narrator",  # 讲述者风格
            role="youngadultmale"  # 年轻男性角色
        ),
        pace=PaceConfig(
            base_rate="-18%",  # 慢速讲述
            opening_delta="-5%",  # 开头更慢
            ending_delta="-5%"   # 结尾更慢
        ),
        mood=MoodConfig(
            pitch="-2%",  # 稍低音调
            emphasis="moderate",  # 适度强调
            breathing=True,  # 自然呼吸
            thinking_pause=True,  # 思考停顿
            volume="default"  # 标准音量
        ),
        structure=StructureConfig(
            comma_pause="400ms",  # 适中的逗号停顿
            sentence_pause="800ms",  # 较长的句子停顿
            paragraph_pause="1500ms",  # 较长的段落停顿
            max_sentence_len=140,  # 适中的句子长度
            auto_split_long_sentence=True,
            chapter_pause="2000ms",
            dialog_pause="600ms"
        )
    )

    print("🔧 自定义配置详情:")
    print(f"名称: {custom_config.name}")
    print(f"描述: {custom_config.description}")
    print(f"语音模型: {custom_config.voice.name}")
    print(f"语音风格: {custom_config.voice.style}")
    print(f"扮演角色: {custom_config.voice.role}")
    print(f"基础语速: {custom_config.pace.base_rate}")
    print(f"基础音调: {custom_config.mood.pitch}")
    print(f"强调程度: {custom_config.mood.emphasis}")
    print(f"自然呼吸: {custom_config.mood.breathing}")
    print(f"思考停顿: {custom_config.mood.thinking_pause}")

    # 使用自定义配置生成 SSML
    sample_text = "这是一个自定义配置的示例。请注意语速、音调和停顿的变化。"
    ssml = generate_ssml(sample_text, custom_config)

    print(f"\n📄 生成的 SSML:")
    print(ssml)

    return custom_config


def demonstrate_text_processing():
    """演示文本处理功能"""
    print("\n🔧 文本处理功能演示")
    print("=" * 60)

    test_cases = [
        "包含特殊字符: & < > \" ' 的文本",
        "多行文本\n\n这是第二段\n\n\n\n这是第三段",
        "这是一个非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常长的句子，需要在合适的位置进行分割。",
        "中文标点，。！？；：和英文标点, . ! ? ; : 的混合",
        ""
    ]

    from services.ssml_generator import SimpleSSMLGenerator

    generator = SimpleSSMLGenerator(PRESET_CONFIGS["BEDTIME_BALANCED"])

    for i, test_text in enumerate(test_cases, 1):
        print(f"\n测试案例 {i}:")
        print(f"输入: {repr(test_text)}")

        # 文本预处理
        processed = generator._preprocess_text(test_text)
        print(f"预处理: {repr(processed)}")

        # 段落分割
        paragraphs = generator._split_paragraphs(processed)
        print(f"段落分割: {paragraphs}")

        # 句子分割
        sentences = generator._split_sentences(processed)
        print(f"句子分割: {len(sentences)} 个句子")

        # 生成 SSML
        if processed:
            ssml = generate_ssml(test_text, "BEDTIME_BALANCED")
            print(f"SSML 长度: {len(ssml)} 字符")


def demonstrate_integration_examples():
    """演示集成示例"""
    print("\n🔗 系统集成示例")
    print("=" * 60)

    # 示例 1: 基本集成
    print("1. 基本集成到 FastAPI:")
    example_code = '''
from fastapi import FastAPI
from app.services.ssml_generator import generate_ssml

app = FastAPI()

@app.post("/tts")
async def create_tts(text: str, style: str = "bedtime"):
    # 生成 SSML
    ssml = generate_ssml(text, style)

    # 调用 edge-tts
    # audio = await edge_tts.Communicate(ssml, voice="").save()

    return {"ssml": ssml, "audio_url": "..."}
'''
    print(example_code)

    # 示例 2: 与现有 TTS 服务集成
    print("\n2. 集成到现有 TTS 服务:")
    example_code = '''
from app.services.enhanced_tts_service import EnhancedTTSService

# 替换原有服务
tts_service = EnhancedTTSService()

# 生成故事音频
audio_path = await tts_service.generate_story_tts(
    story_text="你的故事内容",
    story_type="bedtime"
)
'''
    print(example_code)

    # 示例 3: 自定义配置
    print("\n3. 创建自定义风格:")
    example_code = '''
from app.services.ssml_generator import SSMLConfig, VoiceConfig

# 创建教学讲解配置
teaching_config = SSMLConfig(
    voice=VoiceConfig(name="zh-CN-YunyangNeural", style="customerservice"),
    pace=PaceConfig(base_rate="-10%"),
    mood=MoodConfig(pitch="+2%", emphasis="moderate"),
    structure=StructureConfig(
        comma_pause="200ms",  # 较短的停顿，保持节奏
        sentence_pause="500ms"
    )
)

# 使用配置
ssml = generate_ssml("教学内容", teaching_config)
'''
    print(example_code)


def main():
    """主演示函数"""
    print("🚀 SSML 生成系统完整演示")
    print("🎯 专为睡前故事和长篇叙事音频设计")
    print("🏗️ 采用分层配置架构，易于扩展")
    print("=" * 80)

    # 演示各个功能模块
    story = demonstrate_ssml_generation()
    custom_config = demonstrate_custom_config()
    demonstrate_text_processing()
    demonstrate_integration_examples()

    # 总结
    print("\n" + "=" * 80)
    print("📋 系统功能总结:")
    print("✅ 四层配置架构 (Voice/Pace/Mood/Structure)")
    print("✅ 3 套内置预设配置 (BEDTIME_SOFT/BALANCED/FAIRY)")
    print("✅ 完全可定制的参数系统")
    print("✅ 智能文本预处理和分段")
    print("✅ 自动停顿插入和语速调节")
    print("✅ XML 安全处理")
    print("✅ 与现有系统无缝集成")

    print("\n📚 使用方法:")
    print("1. 简单使用: generate_ssml(text, 'BEDTIME_BALANCED')")
    print("2. 查看预设: list(PRESET_CONFIGS.keys())")
    print("3. 自定义配置: SSMLConfig(...)")

    print("\n📁 相关文件:")
    print("- ssml_generator.py: 核心生成器模块")
    print("- enhanced_tts_service.py: 集成示例服务")
    print("- test_ssml_generator_new.py: 完整测试套件")
    print("- SSML_GENERATOR_GUIDE.md: 详细使用指南")

    print("\n🎉 演示完成！你现在可以开始使用 SSML 生成系统了。")


if __name__ == "__main__":
    main()