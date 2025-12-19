"""
增强版 TTS 服务 - 集成 SSML 生成器

这个示例展示了如何将新的 SSML 生成器集成到现有的 TTS 服务中
"""

import asyncio
import edge_tts
import uuid
from pathlib import Path
from typing import List, Optional, Union
from .ssml_generator import generate_ssml, SSMLConfig, PRESET_CONFIGS
from .tts_service import TTSService


class EnhancedTTSService(TTSService):
    """增强版 TTS 服务，支持 SSML 生成"""

    def __init__(self):
        super().__init__()
        # 默认使用平衡的睡前故事配置
        self.default_ssml_config = "BEDTIME_BALANCED"

    async def generate_audio_chunk_with_ssml(
        self,
        text: str,
        ssml_config: Optional[Union[str, SSMLConfig]] = None,
        output_path: Optional[Path] = None
    ) -> str:
        """
        使用 SSML 生成单个音频块

        Args:
            text: 输入文本
            ssml_config: SSML 配置（预设名称或配置对象）
            output_path: 输出文件路径

        Returns:
            生成的音频文件路径
        """
        if output_path is None:
            output_path = self.temp_dir / f"chunk_{uuid.uuid4()}.mp3"

        # 生成 SSML
        if ssml_config is None:
            ssml_config = self.default_ssml_config

        ssml = generate_ssml(text, ssml_config)

        try:
            # 使用 SSML 调用 edge-tts
            communicate = edge_tts.Communicate(ssml, voice="")  # voice 在 SSML 中定义
            await communicate.save(str(output_path))
            return str(output_path)

        except Exception as e:
            raise RuntimeError(f"Failed to generate SSML audio: {str(e)}")

    async def generate_story_tts(
        self,
        story_text: str,
        story_type: str = "bedtime",  # bedtime/fairy/custom
        task_id: Optional[str] = None,
        custom_config: Optional[SSMLConfig] = None
    ) -> str:
        """
        生成故事 TTS，支持不同风格

        Args:
            story_text: 故事文本
            story_type: 故事类型
            task_id: 任务ID
            custom_config: 自定义 SSML 配置

        Returns:
            最终音频文件路径
        """
        if task_id is None:
            task_id = str(uuid.uuid4())

        # 选择 SSML 配置
        if custom_config:
            ssml_config = custom_config
        elif story_type == "bedtime":
            ssml_config = "BEDTIME_SOFT"
        elif story_type == "fairy":
            ssml_config = "BEDTIME_FAIRY"
        else:
            ssml_config = "BEDTIME_BALANCED"

        # 创建任务目录
        task_dir = self.temp_dir / task_id
        task_dir.mkdir(parents=True, exist_ok=True)

        # 清理文本（使用父类的清理方法）
        cleaned_text = self.clean_text(story_text)
        if not cleaned_text:
            raise ValueError("Text is empty after cleaning")

        # 分割文本块（使用 SSML 配置中的最大句子长度）
        if isinstance(ssml_config, str):
            chunk_size = PRESET_CONFIGS[ssml_config].structure.max_sentence_len * 3
        else:
            chunk_size = ssml_config.structure.max_sentence_len * 3

        chunks = self.split_text(cleaned_text, chunk_size)
        if not chunks:
            raise ValueError("No text chunks to process")

        # 生成音频块
        chunk_files = []
        for i, chunk in enumerate(chunks):
            chunk_path = task_dir / f"chunk_{i:05d}.mp3"
            await self.generate_audio_chunk_with_ssml(chunk, ssml_config, chunk_path)
            chunk_files.append(chunk_path)

        # 合并音频文件
        final_output = self.audio_dir / f"{task_id}.mp3"
        await self.concatenate_audio_files(chunk_files, final_output)

        # 清理临时文件
        import shutil
        shutil.rmtree(task_dir, ignore_errors=True)

        return str(final_output)

    async def concatenate_audio_files(self, chunk_files: List[Path], output_path: Path) -> None:
        """
        合并多个音频文件

        Args:
            chunk_files: 音频文件路径列表
            output_path: 输出文件路径
        """
        if not chunk_files:
            raise ValueError("No audio files to concatenate")

        # 这里应该使用 ffmpeg 或其他音频处理工具来合并文件
        # 为了示例，我们只复制第一个文件
        import shutil
        shutil.copy2(chunk_files[0], output_path)

        # 实际生产环境中的实现示例（需要安装 ffmpeg）：
        """
        import subprocess

        # 创建文件列表
        file_list_path = output_path.parent / f"{output_path.stem}_list.txt"
        with open(file_list_path, 'w') as f:
            for chunk_file in chunk_files:
                f.write(f"file '{chunk_file}'\n")

        # 使用 ffmpeg 合并
        cmd = [
            'ffmpeg', '-f', 'concat', '-safe', '0', '-i', str(file_list_path),
            '-c', 'copy', str(output_path)
        ]
        subprocess.run(cmd, check=True)

        # 清理临时文件
        file_list_path.unlink()
        """

    def get_available_presets(self) -> dict:
        """获取可用的 SSML 预设配置"""
        return {
            name: {
                "name": config.name,
                "description": config.description,
                "voice": config.voice.name,
                "style": config.voice.style,
                "rate": config.pace.base_rate,
                "pitch": config.mood.pitch
            }
            for name, config in PRESET_CONFIGS.items()
        }

    def create_story_config(
        self,
        voice_name: str,
        style: str = "calm",
        rate: str = "-15%",
        pitch: str = "+1%",
        comma_pause: str = "350ms",
        sentence_pause: str = "700ms"
    ) -> SSMLConfig:
        """
        创建自定义故事配置的便捷方法

        Args:
            voice_name: 语音模型名称
            style: 语音风格
            rate: 基础语速
            pitch: 基础音调
            comma_pause: 逗号停顿
            sentence_pause: 句子停顿

        Returns:
            SSML 配置对象
        """
        from .ssml_generator import VoiceConfig, PaceConfig, MoodConfig, StructureConfig

        return SSMLConfig(
            name="CUSTOM_STORY",
            description="自定义故事配置",
            voice=VoiceConfig(name=voice_name, style=style),
            pace=PaceConfig(base_rate=rate),
            mood=MoodConfig(pitch=pitch),
            structure=StructureConfig(
                comma_pause=comma_pause,
                sentence_pause=sentence_pause
            )
        )


# 使用示例
async def example_usage():
    """演示如何使用增强版 TTS 服务"""
    service = EnhancedTTSService()

    story = """
    从前，在一个美丽的森林里，住着一只可爱的小兔子。它的名字叫雪球，因为它的毛像雪一样洁白。

    有一天，雪球决定去寻找传说中的彩虹花。据说这种花只在雨后的阳光中出现，七种颜色的花瓣闪闪发光。

    雪球踏上了冒险的旅程。它穿过潺潺的小溪，越过青青的草地，最后在一座小山上找到了彩虹花。

    "你好，小兔子，"彩虹花温柔地说，"你为什么要寻找我呢？"

    雪球回答："我想把你的美丽带给森林里的每一个朋友。"

    彩虹花很高兴，它送给雪球一颗种子。雪球把种子带回森林，种在了大家都能看到的地方。

    从此以后，森林里开满了美丽的彩虹花，每个动物都过得很快乐。
    """

    # 生成不同风格的音频
    print("🎵 生成轻柔睡前故事...")
    soft_audio = await service.generate_story_tts(
        story, story_type="bedtime", task_id="bedtime_story"
    )
    print(f"✅ 轻柔版本: {soft_audio}")

    print("\n🎵 生成童话故事...")
    fairy_audio = await service.generate_story_tts(
        story, story_type="fairy", task_id="fairy_story"
    )
    print(f"✅ 童话版本: {fairy_audio}")

    print("\n🎵 生成自定义配置故事...")
    custom_config = service.create_story_config(
        voice_name="zh-CN-YunxiNeural",
        style="narrator",
        rate="-20%",
        pitch="0%"
    )
    custom_audio = await service.generate_story_tts(
        story, custom_config=custom_config, task_id="custom_story"
    )
    print(f"✅ 自定义版本: {custom_audio}")

    # 显示可用预设
    print("\n📚 可用的预设配置:")
    presets = service.get_available_presets()
    for name, info in presets.items():
        print(f"  {name}: {info['description']}")
        print(f"    - 语音: {info['voice']} ({info['style']})")
        print(f"    - 语速: {info['rate']}, 音调: {info['pitch']}")


if __name__ == "__main__":
    # 运行示例
    asyncio.run(example_usage())