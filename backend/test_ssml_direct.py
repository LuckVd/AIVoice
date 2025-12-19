#!/usr/bin/env python3
"""
直接测试SSML通信，验证是否还会念出SSML标签
"""
import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, '/opt/projects/AIVoice/backend')

from app.services.ssml_tts_service import ssml_communicate
from app.services.ssml_generator import generate_ssml, PRESET_CONFIGS
from pathlib import Path

async def test_ssml_communication():
    """测试SSML通信"""

    # 测试文本
    test_text = "这是一个SSML测试。看看会不会念出标签内容。"

    print("=== 测试自定义SSML通信 ===")

    # 生成SSML
    ssml_content = generate_ssml(test_text, "BEDTIME_BALANCED")
    print(f"生成的SSML: {ssml_content[:200]}...")

    # 测试文件路径
    output_file = "/opt/projects/AIVoice/backend/test_ssml_communication.mp3"

    try:
        # 使用自定义SSML通信
        print("开始使用自定义WebSocket SSML通信...")
        ssml_communicate(ssml_content, output_file)
        print(f"✅ SSML通信成功！音频文件: {output_file}")

        # 检查文件大小
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            print(f"📁 文件大小: {file_size} bytes ({file_size/1024:.1f} KB)")
        else:
            print("❌ 音频文件未生成")

    except Exception as e:
        print(f"❌ SSML通信失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_ssml_communication())