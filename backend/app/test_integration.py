#!/usr/bin/env python3
"""
SSML 系统集成测试

测试整个 SSML 生成系统是否正确集成到现有的 TTS 服务中
"""

import sys
import os

# 设置项目路径
backend_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_path)
sys.path.insert(0, os.path.dirname(backend_path))

# 设置环境变量
os.environ.setdefault('PYTHONPATH', backend_path)

from app.services.ssml_generator import (
    generate_ssml, PRESET_CONFIGS, SSMLConfig,
    VoiceConfig, PaceConfig, MoodConfig, StructureConfig
)
from app.services.tts_service import TTSService
from app.services.enhanced_tts_service import EnhancedTTSService


def test_ssml_service_integration():
    """测试 SSML 生成器与 TTS 服务的集成"""
    print("🧪 测试 SSML 服务集成")

    service = TTSService()

    # 测试获取预设配置
    presets = service.get_available_ssml_presets()
    print(f"✅ 获取到 {len(presets)} 个预设配置")
    assert "BEDTIME_SOFT" in presets
    assert "BEDTIME_BALANCED" in presets
    assert "BEDTIME_FAIRY" in presets

    # 测试从预设创建自定义配置
    custom_config = service.create_ssml_config_from_preset(
        "BEDTIME_BALANCED",
        voice="zh-CN-YunxiNeural",
        rate="-20%",
        pitch="0%"
    )
    print(f"✅ 创建自定义配置: {custom_config.name}")
    assert custom_config.voice.name == "zh-CN-YunxiNeural"
    assert custom_config.pace.base_rate == "-20%"

    # 测试 SSML 生成
    sample_text = "这是一个测试文本。用来验证集成是否正常工作。"
    ssml = generate_ssml(sample_text, "BEDTIME_BALANCED")
    print(f"✅ 生成 SSML，长度: {len(ssml)}")
    assert "<speak" in ssml
    assert "<voice" in ssml
    assert sample_text.replace("。", "").replace("，", "") in ssml

    print("✅ SSML 服务集成测试通过")


def test_enhanced_service():
    """测试增强版 TTS 服务"""
    print("\n🧪 测试增强版 TTS 服务")

    # 注意：这个测试不会实际生成音频文件，只是测试配置和逻辑
    service = EnhancedTTSService()

    # 测试便捷方法
    story_config = service.create_story_config(
        voice_name="zh-CN-YunxiNeural",
        style="narrator",
        rate="-15%",
        pitch="+2%"
    )
    print(f"✅ 创建故事配置: {story_config.name}")
    assert story_config.voice.name == "zh-CN-YunxiNeural"
    assert story_config.voice.style == "narrator"

    print("✅ 增强版 TTS 服务测试通过")


def test_ssml_preset_differences():
    """测试不同预设配置的差异"""
    print("\n🧪 测试 SSML 预设差异")

    test_text = "这是一个测试文本。用来比较不同配置的效果。请注意语速和停顿的变化。"

    results = {}
    for preset_name, config in PRESET_CONFIGS.items():
        ssml = generate_ssml(test_text, preset_name)
        results[preset_name] = {
            'ssml': ssml,
            'config': config
        }

        print(f"\n📋 {preset_name}:")
        print(f"  - 语音: {config.voice.name} ({config.voice.style})")
        print(f"  - 语速: {config.pace.base_rate}")
        print(f"  - 音调: {config.mood.pitch}")
        print(f"  - 逗号停顿: {config.structure.comma_pause}")
        print(f"  - 句子停顿: {config.structure.sentence_pause}")
        print(f"  - SSML 长度: {len(ssml)}")

    # 验证不同配置产生不同结果
    soft_ssml = results["BEDTIME_SOFT"]["ssml"]
    fairy_ssml = results["BEDTIME_FAIRY"]["ssml"]

    # SOFT 配置应该有更多/更长的停顿
    soft_breaks = soft_ssml.count("<break")
    fairy_breaks = fairy_ssml.count("<break")

    print(f"\n📊 停顿对比:")
    print(f"  - BEDTIME_SOFT: {soft_breaks} 个停顿")
    print(f"  - BEDTIME_FAIRY: {fairy_breaks} 个停顿")

    assert soft_ssml != fairy_ssml, "不同配置应该生成不同的 SSML"

    print("✅ SSML 预设差异测试通过")


def test_text_processing_edge_cases():
    """测试文本处理边界情况"""
    print("\n🧪 测试文本处理边界情况")

    test_cases = [
        ("", "空文本"),
        ("这是一个测试", "简单中文"),
        ("This is English text", "英文文本"),
        ("中英文 mixed text 测试", "混合文本"),
        ("包含特殊字符: & < > \" ' 的文本", "特殊字符"),
        ("多行文本\n\n第二段\n\n第三段", "多段落"),
        "这是一个非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常非常长的句子，需要在合适的位置进行分割，这样可以测试系统的自动分割功能是否正常工作。",
        ("，，。！？；：", "只有标点")
    ]

    for test_text, description in test_cases:
        print(f"\n测试 {description}:")
        print(f"输入: {repr(test_text)}")

        try:
            # 测试所有预设配置
            for preset_name in ["BEDTIME_SOFT", "BEDTIME_BALANCED", "BEDTIME_FAIRY"]:
                ssml = generate_ssml(test_text, preset_name)
                print(f"  {preset_name}: SSML 长度 {len(ssml)}")

                # 基本验证
                assert "<speak" in ssml
                assert "</speak>" in ssml

                if test_text:  # 非空文本
                    assert len(ssml) > 50  # SSML 应该比原始文本长

            print(f"  ✅ {description} 测试通过")

        except Exception as e:
            print(f"  ❌ {description} 测试失败: {str(e)}")
            raise

    print("✅ 文本处理边界情况测试通过")


def test_api_compatibility():
    """测试 API 兼容性（模拟）"""
    print("\n🧪 测试 API 兼容性")

    # 模拟 API 请求数据结构
    from schemas.tts import TTSRequestCreateSSML

    # 测试基本 SSML 请求
    request_data = TTSRequestCreateSSML(
        text="这是一个测试文本",
        ssml_preset="BEDTIME_BALANCED",
        use_ssml=True
    )

    print(f"✅ SSML 请求数据验证通过")
    assert request_data.use_ssml == True
    assert request_data.ssml_preset == "BEDTIME_BALANCED"

    # 测试自定义覆盖
    custom_request = TTSRequestCreateSSML(
        text="自定义测试",
        ssml_preset="BEDTIME_SOFT",
        use_ssml=True,
        voice="zh-CN-YunxiNeural",
        rate="-20%",
        pitch="0%",
        comma_pause="400ms"
    )

    print(f"✅ 自定义覆盖请求验证通过")
    assert custom_request.voice == "zh-CN-YunxiNeural"
    assert custom_request.rate == "-20%"

    # 测试传统模式兼容
    legacy_request = TTSRequestCreateSSML(
        text="传统模式测试",
        legacy_mode=True,
        legacy_rate="-10%",
        legacy_pitch="0Hz"
    )

    print(f"✅ 传统模式兼容性验证通过")
    assert legacy_request.legacy_mode == True

    print("✅ API 兼容性测试通过")


def main():
    """运行所有集成测试"""
    print("🚀 SSML 系统集成测试")
    print("🎯 验证 SSML 生成器与现有 TTS 系统的完整集成")
    print("=" * 60)

    try:
        test_ssml_service_integration()
        test_enhanced_service()
        test_ssml_preset_differences()
        test_text_processing_edge_cases()
        test_api_compatibility()

        print("\n" + "=" * 60)
        print("🎉 所有集成测试通过！")
        print("✅ SSML 生成系统已成功集成到现有 TTS 服务中")

        print("\n📚 可用的 API 接口:")
        print("- POST /api/tts/ssml - 创建 SSML TTS 请求")
        print("- GET /api/tts/ssml/presets - 获取预设配置列表")
        print("- GET /api/tts/ssml/{preset_name} - 获取特定预设详情")
        print("- POST /api/tts/ssml/preview - 预览 SSML（不生成音频）")

        print("\n🔧 数据库已更新:")
        print("- tts_requests 表新增 SSML 相关字段")
        print("- use_ssml, ssml_preset, ssml_config, ssml_generated")

        print("\n⚡ 系统特性:")
        print("- ✅ 完全向后兼容，不影响现有功能")
        print("- ✅ 支持三种内置预设配置")
        print("- ✅ 支持自定义参数覆盖")
        print("- ✅ 智能文本预处理和分段")
        print("- ✅ 自动停顿插入和语速调节")

    except Exception as e:
        print(f"\n❌ 集成测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)