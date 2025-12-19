#!/usr/bin/env python3
"""
大文本TTS功能测试脚本
测试系统对不同长度文本的处理能力，特别是超长文本（5万字以上）
"""

import asyncio
import sys
import time
import requests
import uuid
import psutil
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent))

from app.services.tts_service import TTSService


class LargeTextTester:
    def __init__(self):
        self.tts_service = TTSService()
        self.api_base_url = "http://localhost:8000/api/tts"

        # 测试文本生成器
        self.test_sentences = [
            "这是一个测试句子，用于验证TTS系统的功能。",
            "The quick brown fox jumps over the lazy dog.",
            "人工智能技术正在改变我们的生活方式。",
            "Technology has revolutionized the way we communicate.",
            "在信息时代，数据处理能力变得越来越重要。"
        ]

    def generate_test_text(self, target_chars: int) -> str:
        """生成指定长度的测试文本"""
        print(f"生成 {target_chars} 字符的测试文本...")

        text_parts = []
        current_length = 0

        while current_length < target_chars:
            for sentence in self.test_sentences:
                if current_length >= target_chars:
                    break

                # 计算还能添加多少字符
                remaining = target_chars - current_length
                if len(sentence) <= remaining:
                    text_parts.append(sentence)
                    current_length += len(sentence)
                else:
                    # 截断句子
                    truncated = sentence[:remaining]
                    text_parts.append(truncated)
                    current_length += len(truncated)
                    break

                # 添加标点和空格
                if current_length < target_chars:
                    text_parts.append(" ")
                    current_length += 1

        result = "".join(text_parts)
        print(f"实际生成长度: {len(result)} 字符")
        return result

    def check_memory_usage(self) -> tuple:
        """检查当前内存使用情况"""
        memory = psutil.virtual_memory()
        process = psutil.Process()
        process_memory = process.memory_info()

        return {
            'system_total': memory.total,
            'system_available': memory.available,
            'system_percent': memory.percent,
            'process_rss': process_memory.rss,
            'process_vms': process_memory.vms
        }

    def print_memory_usage(self, label: str):
        """打印内存使用情况"""
        usage = self.check_memory_usage()
        print(f"\n=== {label} 内存使用情况 ===")
        print(f"系统内存使用率: {usage['system_percent']:.1f}%")
        print(f"系统可用内存: {usage['system_available'] / 1024 / 1024 / 1024:.1f} GB")
        print(f"进程内存使用: {usage['process_rss'] / 1024 / 1024:.1f} MB (RSS)")
        print(f"进程虚拟内存: {usage['process_vms'] / 1024 / 1024:.1f} MB (VMS)")

    async def test_text_segmentation(self):
        """测试文本分段功能"""
        print("\n" + "="*60)
        print("测试 1: 文本分段功能")
        print("="*60)

        test_lengths = [1000, 5000, 10000, 30000, 50000, 80000]

        for length in test_lengths:
            print(f"\n测试文本长度: {length} 字符")
            text = self.generate_test_text(length)

            # 测试分段
            start_time = time.time()
            chunks = self.tts_service.split_text(text, 1000)
            end_time = time.time()

            print(f"分段结果: {len(chunks)} 个片段")
            print(f"分段耗时: {end_time - start_time:.3f} 秒")
            print(f"平均片段长度: {sum(len(c) for c in chunks) / len(chunks):.1f} 字符")

            # 验证分段完整性
            total_reconstructed = "".join(chunks)
            if len(total_reconstructed) == len(text):
                print("✅ 分段完整性验证通过")
            else:
                print("❌ 分段完整性验证失败")
                print(f"原文长度: {len(text)}, 重组长度: {len(total_reconstructed)}")

    async def test_memory_management(self):
        """测试内存管理功能"""
        print("\n" + "="*60)
        print("测试 2: 内存管理功能")
        print("="*60)

        # 记录初始内存
        self.print_memory_usage("测试开始前")

        # 测试不同长度文本的内存使用
        test_lengths = [10000, 50000, 100000]

        for length in test_lengths:
            print(f"\n测试 {length} 字符文本的内存使用:")
            text = self.generate_test_text(length)

            # 测试最优分块大小计算
            chunk_size = self.tts_service.get_optimal_chunk_size(length)
            concurrency = self.tts_service.get_optimal_concurrency(length)

            print(f"推荐分块大小: {chunk_size} 字符")
            print(f"推荐并发数: {concurrency}")

            # 测试分段后的内存使用
            chunks = self.tts_service.split_text(text, chunk_size)
            self.print_memory_usage(f"分段后 ({len(chunks)} 片段)")

            # 强制垃圾回收
            self.tts_service.force_garbage_collection()
            self.print_memory_usage("垃圾回收后")

    async def test_backend_service(self):
        """测试后端服务直接调用"""
        print("\n" + "="*60)
        print("测试 3: 后端服务直接调用")
        print("="*60)

        # 测试中等长度文本（实际生成音频）
        print("测试 5000 字符文本的实际TTS生成...")
        self.print_memory_usage("TTS生成前")

        text = self.generate_test_text(5000)
        task_id = str(uuid.uuid4())

        try:
            start_time = time.time()
            audio_path = await self.tts_service.generate_tts_async(
                task_id=task_id,
                text=text,
                voice="zh-CN-XiaoxiaoNeural",
                rate="-10%",
                pitch="+0Hz",
                use_ssml=False
            )
            end_time = time.time()

            print(f"✅ TTS生成成功!")
            print(f"音频文件路径: {audio_path}")
            print(f"生成耗时: {end_time - start_time:.1f} 秒")

            # 检查文件是否真的存在
            if Path(audio_path).exists():
                file_size = Path(audio_path).stat().st_size
                print(f"音频文件大小: {file_size / 1024:.1f} KB")
            else:
                print("❌ 音频文件不存在")

        except Exception as e:
            print(f"❌ TTS生成失败: {e}")

        finally:
            self.print_memory_usage("TTS生成后")
            self.tts_service.force_garbage_collection()

    def test_api_endpoints(self):
        """测试API端点"""
        print("\n" + "="*60)
        print("测试 4: API端点测试")
        print("="*60)

        try:
            # 测试健康检查
            response = requests.get(f"{self.api_base_url}/", timeout=5)
            if response.status_code == 200:
                print("✅ API健康检查通过")
            else:
                print(f"❌ API健康检查失败: {response.status_code}")

        except requests.exceptions.RequestException as e:
            print(f"❌ API连接失败: {e}")
            print("请确保后端服务正在运行 (python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000)")
            return False

        return True

    def test_ssml_presets(self):
        """测试SSML预设配置"""
        print("\n" + "="*60)
        print("测试 5: SSML预设配置")
        print("="*60)

        try:
            response = requests.get(f"{self.api_base_url}/ssml/presets", timeout=5)
            if response.status_code == 200:
                presets = response.json().get('presets', {})
                print(f"✅ 获取到 {len(presets)} 个SSML预设:")
                for name, config in presets.items():
                    print(f"  - {name}: {config.get('description', 'N/A')}")
            else:
                print(f"❌ 获取SSML预设失败: {response.status_code}")

        except requests.exceptions.RequestException as e:
            print(f"❌ SSML预设请求失败: {e}")

    def create_test_files(self):
        """创建测试用的文本文件"""
        print("\n" + "="*60)
        print("创建测试文件")
        print("="*60)

        test_dir = Path("test_files")
        test_dir.mkdir(exist_ok=True)

        # 创建不同长度的测试文件
        test_files = [
            ("short_test.txt", 1000),
            ("medium_test.txt", 10000),
            ("long_test.txt", 50000),
            ("xlong_test.txt", 100000)
        ]

        for filename, length in test_files:
            filepath = test_dir / filename
            text = self.generate_test_text(length)

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(text)

            file_size = filepath.stat().st_size
            print(f"✅ 创建 {filename}: {length} 字符, {file_size / 1024:.1f} KB")

    async def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始大文本TTS功能全面测试")
        print("=" * 60)

        # 记录开始时间和内存
        start_time = time.time()
        self.print_memory_usage("测试开始")

        try:
            # 创建测试文件
            self.create_test_files()

            # 测试API连接
            if not self.test_api_endpoints():
                return

            # 测试SSML预设
            self.test_ssml_presets()

            # 测试文本分段
            await self.test_text_segmentation()

            # 测试内存管理
            await self.test_memory_management()

            # 测试后端服务（可选，因为会实际生成音频文件）
            test_audio = input("\n是否测试实际音频生成？(y/N): ").lower().strip()
            if test_audio in ['y', 'yes']:
                await self.test_backend_service()
            else:
                print("跳过音频生成测试")

        except KeyboardInterrupt:
            print("\n测试被用户中断")
        except Exception as e:
            print(f"\n测试过程中发生错误: {e}")
            import traceback
            traceback.print_exc()

        finally:
            # 最终统计
            end_time = time.time()
            total_time = end_time - start_time

            print("\n" + "="*60)
            print("测试总结")
            print("="*60)
            print(f"总耗时: {total_time:.1f} 秒")
            self.print_memory_usage("测试结束")

            # 清理建议
            memory_usage = self.check_memory_usage()
            if memory_usage['system_percent'] > 80:
                print("⚠️ 系统内存使用率较高，建议重启相关服务")


async def main():
    """主函数"""
    tester = LargeTextTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    # 检查是否在正确的目录
    if not Path("app").exists():
        print("❌ 请在项目根目录运行此测试脚本")
        sys.exit(1)

    # 运行测试
    asyncio.run(main())