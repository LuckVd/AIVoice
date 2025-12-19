import asyncio
import edge_tts
import re
import subprocess
import uuid
import os
import gc
import psutil
import logging
from pathlib import Path
from typing import List, Optional, Union
from ..core.config import settings
from .ssml_generator import generate_ssml, SSMLConfig, PRESET_CONFIGS, SimpleSSMLGenerator
from .ssml_tts_service import ssml_communicate

# 配置日志
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class TTSService:
    def __init__(self):
        self.storage_path = Path(settings.storage_path)
        self.audio_dir = self.storage_path / "audio"
        self.temp_dir = self.storage_path / "temp"

        # Ensure directories exist
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        # Default SSML configuration
        self.default_ssml_config = "BEDTIME_BALANCED"

        # Memory management settings
        self.max_memory_usage_percent = 70  # Maximum memory usage before triggering cleanup
        self.batch_size = 5  # Number of chunks to process in each batch

    @staticmethod
    def clean_text(text: str) -> str:
        """清理文本，去掉 Markdown 或不希望发音的符号"""
        # 去掉 Markdown 标题、列表符号、引用符号等
        text = re.sub(r"[#>*`_~\-+=\[\]\(\)<>]", "", text)
        # 去掉多余空格
        text = re.sub(r"\s+", " ", text)
        # 保留中文、英文、数字和常用标点
        text = re.sub(r"[^\u4e00-\u9fffA-Za-z0-9，。！？,.!?；;:、\s]", "", text)
        return text.strip()

    @staticmethod
    def split_text(text: str, max_chars: int = 1000) -> List[str]:
        """智能文本分段，支持超长文本"""
        # 如果文本很短，直接返回
        if len(text) <= max_chars:
            return [text]

        chunks = []

        # 多种分段策略
        strategies = [
            # 1. 按段落分段（优先级最高）
            lambda t: TTSService._split_by_paragraph(t, max_chars),
            # 2. 按句子分段
            lambda t: TTSService._split_by_sentences(t, max_chars),
            # 3. 按逗号分段
            lambda t: TTSService._split_by_commas(t, max_chars),
            # 4. 强制按长度分段（最后手段）
            lambda t: TTSService._split_by_length(t, max_chars)
        ]

        for strategy in strategies:
            chunks = strategy(text)
            if len(chunks) > 1 or len(chunks[0]) <= max_chars:
                break

        return chunks

    def check_memory_usage(self) -> float:
        """检查当前内存使用百分比"""
        try:
            return psutil.virtual_memory().percent
        except Exception:
            return 0.0

    def force_garbage_collection(self):
        """强制垃圾回收释放内存"""
        try:
            gc.collect()
            print(f"Memory after GC: {self.check_memory_usage():.1f}%")
        except Exception as e:
            print(f"GC failed: {e}")

    def get_optimal_chunk_size(self, text_length: int) -> int:
        """根据文本长度和内存状况动态调整分块大小"""
        base_chunk_size = settings.max_chars_per_chunk
        memory_usage = self.check_memory_usage()

        # 如果内存使用过高，减小分块大小
        if memory_usage > self.max_memory_usage_percent:
            return max(500, base_chunk_size // 2)

        # 超长文本使用更小的分块
        if text_length > 100000:  # 10万字以上
            return max(800, base_chunk_size // 1.5)
        elif text_length > 50000:  # 5万字以上
            return max(1000, base_chunk_size // 1.2)

        return base_chunk_size

    def get_optimal_concurrency(self, text_length: int) -> int:
        """根据文本长度和内存状况动态调整并发数"""
        memory_usage = self.check_memory_usage()
        base_concurrency = settings.concurrency

        # 如果内存使用过高，大幅降低并发数
        if memory_usage > self.max_memory_usage_percent:
            return max(1, base_concurrency // 4)

        # 超长文本使用更低的并发
        if text_length > 100000:
            return max(2, base_concurrency // 2)
        elif text_length > 50000:
            return max(3, base_concurrency // 1.5)

        return base_concurrency

    @staticmethod
    def _split_by_paragraph(text: str, max_chars: int) -> List[str]:
        """按段落分段"""
        import re
        # 匹配段落分隔符
        paragraphs = re.split(r'\n\s*\n+', text.strip())
        chunks = []
        current_chunk = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if len(current_chunk) + len(para) + 2 <= max_chars:
                current_chunk += ("\n\n" + para) if current_chunk else para
            else:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = para

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks if chunks else [text]

    @staticmethod
    def _split_by_sentences(text: str, max_chars: int) -> List[str]:
        """按句子分段"""
        import re
        # 支持更多标点符号
        sentence_endings = r'([。！？.!?；;])'
        sentences = re.split(sentence_endings, text)

        chunks = []
        current_chunk = ""

        for i in range(0, len(sentences), 2):
            if i + 1 < len(sentences):
                sentence = sentences[i] + sentences[i + 1]
            else:
                sentence = sentences[i]

            if len(current_chunk) + len(sentence) <= max_chars:
                current_chunk += sentence
            else:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = sentence

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks if chunks else [text]

    @staticmethod
    def _split_by_commas(text: str, max_chars: int) -> List[str]:
        """按逗号分段"""
        import re
        # 按逗号、顿号、分号分割
        separators = r'([，、；;])'
        parts = re.split(separators, text)

        chunks = []
        current_chunk = ""

        for i in range(0, len(parts), 2):
            # 获取文本部分
            text_part = parts[i]

            # 获取分隔符部分（如果存在）
            separator = parts[i + 1] if i + 1 < len(parts) else ""

            # 组合文本和分隔符
            full_part = text_part + separator

            if len(current_chunk) + len(full_part) <= max_chars:
                current_chunk += full_part
            else:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = full_part

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks if chunks else [text]

    @staticmethod
    def _split_by_length(text: str, max_chars: int) -> List[str]:
        """按长度强制分段"""
        chunks = []
        for i in range(0, len(text), max_chars):
            chunk = text[i:i + max_chars]
            # 尽量不在词语中间断开
            if i + max_chars < len(text):
                # 寻找合适的断点
                for j in range(max_chars - 1, max_chars - 50, -1):
                    if text[i + j] in '，。！？；; ':
                        chunk = text[i:i + j + 1]
                        break
            chunks.append(chunk.strip())
        return chunks

    async def generate_audio_chunk(self, text: str, voice: str, rate: str, pitch: str, output_path: Path, use_ssml: bool = False, ssml_config: Optional[Union[str, SSMLConfig]] = None) -> None:
        """Generate audio for a single text chunk"""
        try:
            if use_ssml:
                # 使用SSML配置直接生成SSML
                if ssml_config is None:
                    ssml_config = self.default_ssml_config

                # 为分段生成SSML（只包含内容部分）
                if isinstance(ssml_config, str) and ssml_config in PRESET_CONFIGS:
                    config_obj = PRESET_CONFIGS[ssml_config]
                else:
                    config_obj = ssml_config

                # 直接生成原始文本，不使用SSML复杂结构
                # 创建基本的prosody标签，避免edge-tts念出SSML标签
                rate = config_obj.pace.base_rate.replace("%", "")
                pitch = config_obj.mood.pitch.replace("Hz", "")

                # 确保rate格式正确
                if not rate.startswith(('+', '-')):
                    rate = f"+{rate}"

                # 确保pitch格式正确
                if not pitch.startswith(('+', '-')):
                    pitch = f"+{pitch}"

                # 构建完整的SSML，使用自定义WebSocket通信
                if isinstance(ssml_config, str) and ssml_config in PRESET_CONFIGS:
                    config_obj = PRESET_CONFIGS[ssml_config]
                else:
                    config_obj = ssml_config

                # 使用SSML生成器创建正确的SSML格式
                generator = SimpleSSMLGenerator(config_obj)
                final_ssml = generator.generate_ssml(text)

                logger.info(f"🚀 开始SSML处理，SSML长度: {len(final_ssml)}")
                logger.info(f"📝 SSML内容预览: {final_ssml[:200]}...")

                # 使用自定义WebSocket SSML通信，避免edge-tts念出SSML标签
                # 这将直接调用ssml_communicate函数而不是edge_tts.Communicate
                try:
                    logger.info(f"🔄 尝试使用自定义WebSocket SSML通信...")
                    ssml_communicate(final_ssml, str(output_path))
                    logger.info(f"✅ SSML通信成功！音频保存到: {output_path}")
                    return  # 直接返回，跳过下面的edge-tts处理
                except Exception as e:
                    logger.error(f"⚠️ SSML通信失败，回退到edge-tts: {e}")
                    logger.error(f"🔄 回退原因: {type(e).__name__} - {str(e)}")

                    # 如果SSML通信失败，我们需要使用edge-tts但是不能直接传递SSML
                    # 提取SSML配置参数并使用edge-tts的标准参数
                    rate_param = config_obj.pace.base_rate
                    pitch_param = config_obj.mood.pitch

                    # 确保rate参数格式正确
                    if rate_param == "0%":
                        rate_param = ""
                    elif rate_param and not rate_param.startswith(('+', '-')):
                        try:
                            num_value = int(rate_param.rstrip('%'))
                            if num_value > 0:
                                rate_param = f"+{rate_param}"
                            else:
                                rate_param = f"{rate_param}"
                        except ValueError:
                            rate_param = ""

                    # 确保pitch参数格式正确 - edge-tts需要Hz格式
                    if pitch_param == "0Hz" or pitch_param == "0%":
                        pitch_param = ""
                    elif pitch_param:
                        try:
                            # 移除所有后缀，获取数值
                            clean_pitch = pitch_param.replace('%', '').replace('Hz', '')
                            num_value = int(clean_pitch)

                            # edge-tts要求pitch必须是Hz格式，不能是百分比
                            # 将百分比转换为Hz（这是一个近似转换）
                            if '%' in pitch_param:
                                # 如果原来是百分比，转换为Hz（1% ≈ 2Hz）
                                num_value = num_value * 2

                            if num_value > 0:
                                pitch_param = f"+{num_value}Hz"
                            elif num_value < 0:
                                pitch_param = f"{num_value}Hz"
                            else:
                                pitch_param = ""
                        except ValueError:
                            pitch_param = ""

                    logger.info(f"🔄 使用edge-tts回退参数: voice={config_obj.voice.name}, rate={rate_param}, pitch={pitch_param}")

                    communicate = edge_tts.Communicate(
                        text=text,  # 使用原始文本，不是SSML
                        voice=config_obj.voice.name,
                        rate=rate_param,
                        pitch=pitch_param
                    )
            else:
                # 传统方式，保持向后兼容
                # Fix rate parameter: edge-tts requires rate to start with + or -
                if rate == "0%":
                    rate = ""
                elif rate and not rate.startswith(('+', '-')):
                    try:
                        num_value = int(rate.rstrip('%'))
                        if num_value > 0:
                            rate = f"+{rate}"
                        elif num_value < 0:
                            rate = f"{rate}"
                        else:
                            rate = ""
                    except ValueError:
                        rate = ""

                # Same for pitch if needed
                if pitch == "0Hz":
                    pitch = ""
                elif pitch and not pitch.startswith(('+', '-')):
                    try:
                        num_value = int(pitch.rstrip('Hz'))
                        if num_value > 0:
                            pitch = f"+{pitch}"
                        elif num_value < 0:
                            pitch = f"{pitch}"
                        else:
                            pitch = ""
                    except ValueError:
                        pitch = ""

                communicate = edge_tts.Communicate(
                    text=text,
                    voice=voice,
                    rate=rate,
                    pitch=pitch
                )

            await communicate.save(str(output_path))
        except Exception as e:
            raise RuntimeError(f"Failed to generate audio for chunk: {str(e)}")

    async def generate_tts_async(self, task_id: str, text: str, voice: str, rate: str, pitch: str,
                              use_ssml: bool = False, ssml_config: Optional[Union[str, SSMLConfig]] = None) -> str:
        """Generate TTS audio and return the file path with memory optimization for long text"""
        print(f"Starting TTS generation for task {task_id}, text length: {len(text)}")
        print(f"Initial memory usage: {self.check_memory_usage():.1f}%")

        # Create task-specific directories
        task_dir = self.temp_dir / task_id
        parts_dir = task_dir / "parts"
        parts_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Clean and split text with memory-aware chunk sizing
            cleaned_text = text if use_ssml else self.clean_text(text)
            if not cleaned_text:
                raise ValueError("Text is empty after cleaning")

            # Get optimal chunk size and concurrency based on text length and memory
            text_length = len(cleaned_text)
            if use_ssml and ssml_config:
                if isinstance(ssml_config, str) and ssml_config in PRESET_CONFIGS:
                    base_chunk_size = PRESET_CONFIGS[ssml_config].structure.max_sentence_len * 3
                elif hasattr(ssml_config, 'structure'):
                    base_chunk_size = ssml_config.structure.max_sentence_len * 3
                else:
                    base_chunk_size = settings.max_chars_per_chunk
                chunk_size = min(base_chunk_size, self.get_optimal_chunk_size(text_length))
            else:
                chunk_size = self.get_optimal_chunk_size(text_length)

            max_concurrency = self.get_optimal_concurrency(text_length)
            print(f"Using chunk size: {chunk_size}, max concurrency: {max_concurrency}")

            chunks = self.split_text(cleaned_text, chunk_size)
            if not chunks:
                raise ValueError("No text chunks to process")

            print(f"Split into {len(chunks)} chunks")

            # Process chunks in batches to manage memory
            await self._process_chunks_in_batches(
                chunks, task_id, parts_dir, voice, rate, pitch,
                use_ssml, ssml_config, text, max_concurrency
            )

            # Force garbage collection before concatenation
            self.force_garbage_collection()

            # Concatenate audio files using ffmpeg
            print("Starting audio concatenation...")
            final_output = self.audio_dir / f"{task_id}.mp3"
            await self.concatenate_audio(parts_dir, final_output)

            print(f"TTS generation completed. Final memory usage: {self.check_memory_usage():.1f}%")
            return str(final_output)

        finally:
            # Clean up temp files and force final garbage collection
            import shutil
            shutil.rmtree(task_dir, ignore_errors=True)
            self.force_garbage_collection()

    async def _process_chunks_in_batches(self, chunks: List[str], task_id: str, parts_dir: Path,
                                       voice: str, rate: str, pitch: str, use_ssml: bool,
                                       ssml_config: Optional[Union[str, SSMLConfig]],
                                       original_text: str, max_concurrency: int):
        """Process audio chunks in batches to manage memory usage"""
        total_chunks = len(chunks)
        processed = 0

        # Process in batches to avoid memory overload
        for batch_start in range(0, total_chunks, self.batch_size):
            batch_end = min(batch_start + self.batch_size, total_chunks)
            batch_chunks = chunks[batch_start:batch_end]

            print(f"Processing batch {batch_start//self.batch_size + 1}/{(total_chunks-1)//self.batch_size + 1} "
                  f"(chunks {batch_start}-{batch_end-1})")

            # Check memory before processing batch
            current_memory = self.check_memory_usage()
            if current_memory > self.max_memory_usage_percent:
                print(f"High memory usage ({current_memory:.1f}%), forcing garbage collection")
                self.force_garbage_collection()

            # Create semaphore for this batch
            sem = asyncio.Semaphore(max_concurrency)

            async def process_chunk(index: int, chunk_text: str):
                chunk_index = batch_start + index
                output_file = parts_dir / f"{chunk_index:05d}.mp3"

                for attempt in range(1, settings.max_retries + 1):
                    try:
                        async with sem:
                            # 对每个分段分别生成SSML，避免重复处理整个文本
                            await self.generate_audio_chunk(chunk_text, voice, rate, pitch, output_file, use_ssml, ssml_config)
                            return
                    except Exception as e:
                        if attempt == settings.max_retries:
                            raise RuntimeError(f"Failed to process chunk {chunk_index} after {settings.max_retries} attempts: {str(e)}")
                        await asyncio.sleep(1)

            # Process this batch concurrently
            batch_tasks = [process_chunk(i, chunk) for i, chunk in enumerate(batch_chunks)]
            await asyncio.gather(*batch_tasks)

            processed += len(batch_chunks)
            print(f"Batch completed. Processed {processed}/{total_chunks} chunks. Memory: {self.check_memory_usage():.1f}%")

            # Force garbage collection after each batch for long texts
            if total_chunks > 20:  # Only for long texts
                self.force_garbage_collection()

    async def concatenate_audio(self, parts_dir: Path, output_path: Path) -> None:
        """Concatenate multiple MP3 files into one using ffmpeg"""
        import subprocess
        import os

        parts = sorted(parts_dir.glob("*.mp3"))
        if not parts:
            raise ValueError("No audio parts to concatenate")

        if len(parts) == 1:
            # 只有一个文件，直接复制
            import shutil
            shutil.copy2(parts[0], output_path)
            return

        # 创建临时文件列表
        parts_list_path = parts_dir / "parts_list.txt"
        with open(parts_list_path, 'w', encoding='utf-8') as f:
            for part in parts:
                f.write(f"file '{part}'\n")

        try:
            # 使用ffmpeg拼接音频文件
            cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', str(parts_list_path),
                '-c', 'copy',
                '-y',  # 覆盖输出文件
                str(output_path)
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )

            print(f"Audio concatenation completed: {result.stderr}")

        except subprocess.CalledProcessError as e:
            # 如果ffmpeg失败，使用简单方式处理
            print(f"ffmpeg concatenation failed: {e}")
            print("Falling back to simple concatenation...")

            # 创建临时文件进行简单拼接
            temp_files = []
            try:
                import wave
                import io
                import struct

                # 读取所有音频文件
                audio_data = []
                for part in parts:
                    with wave.open(str(part), 'rb') as wav_file:
                        frames = wav_file.readframes(-1)
                        audio_data.append((frames, wav_file.getsampwidth(), wav_file.getframerate(), wav_file.getnchannels()))

                # 写入拼接后的文件
                temp_output = str(output_path) + '.wav'
                with wave.open(temp_output, 'wb') as wav_out:
                    wav_out.setnchannels(audio_data[0][3])
                    wav_out.setsampwidth(audio_data[0][1])
                    wav_out.setframerate(audio_data[0][2])

                    for frames, sw, fr, ch in audio_data:
                        wav_out.writeframes(frames)

                # 转换为MP3
                cmd_mp3 = [
                    'ffmpeg', '-y', '-i', temp_output,
                    str(output_path)
                ]
                subprocess.run(cmd_mp3, capture_output=True, check=True)

                # 删除临时WAV文件
                os.remove(temp_output)

            except Exception as inner_e:
                print(f"Simple concatenation failed: {inner_e}")
                # 最后的备选方案：复制第一个文件
                import shutil
                shutil.copy2(parts[0], output_path)

        finally:
            # 清理临时文件
            if parts_list_path.exists():
                os.remove(parts_list_path)

    def get_audio_url(self, task_id: str) -> str:
        """Get the URL for the generated audio file"""
        audio_path = self.audio_dir / f"{task_id}.mp3"
        if audio_path.exists():
            return f"/storage/audio/{task_id}.mp3"
        return None

    def delete_audio(self, task_id: str) -> bool:
        """Delete the audio file for a task"""
        audio_path = self.audio_dir / f"{task_id}.mp3"
        if audio_path.exists():
            audio_path.unlink()
            return True
        return False

    def get_available_ssml_presets(self) -> dict:
        """获取可用的 SSML 预设配置"""
        return {
            name: {
                "name": config.name,
                "description": config.description,
                "voice": config.voice.name,
                "style": config.voice.style,
                "role": config.voice.role,
                "rate": config.pace.base_rate,
                "pitch": config.mood.pitch,
                "comma_pause": config.structure.comma_pause,
                "sentence_pause": config.structure.sentence_pause
            }
            for name, config in PRESET_CONFIGS.items()
        }

    def create_ssml_config_from_preset(self, preset_name: str, **overrides) -> SSMLConfig:
        """从预设创建 SSML 配置，支持参数覆盖"""
        if preset_name not in PRESET_CONFIGS:
            raise ValueError(f"Unknown preset: {preset_name}")

        # 复制预设配置
        base_config = PRESET_CONFIGS[preset_name]

        # 应用覆盖（简单实现）
        from .ssml_generator import VoiceConfig, PaceConfig, MoodConfig, StructureConfig

        voice_config = VoiceConfig(
            name=overrides.get('voice', base_config.voice.name),
            style=overrides.get('style', base_config.voice.style),
            role=overrides.get('role', base_config.voice.role),
            fallback=base_config.voice.fallback
        )

        pace_config = PaceConfig(
            base_rate=overrides.get('rate', base_config.pace.base_rate),
            opening_delta=overrides.get('opening_delta', base_config.pace.opening_delta),
            ending_delta=overrides.get('ending_delta', base_config.pace.ending_delta),
            transition_duration=base_config.pace.transition_duration
        )

        mood_config = MoodConfig(
            pitch=overrides.get('pitch', base_config.mood.pitch),
            emphasis=overrides.get('emphasis', base_config.mood.emphasis),
            breathing=overrides.get('breathing', base_config.mood.breathing),
            thinking_pause=overrides.get('thinking_pause', base_config.mood.thinking_pause),
            volume=overrides.get('volume', base_config.mood.volume)
        )

        structure_config = StructureConfig(
            comma_pause=overrides.get('comma_pause', base_config.structure.comma_pause),
            sentence_pause=overrides.get('sentence_pause', base_config.structure.sentence_pause),
            paragraph_pause=overrides.get('paragraph_pause', base_config.structure.paragraph_pause),
            max_sentence_len=overrides.get('max_sentence_len', base_config.structure.max_sentence_len),
            auto_split_long_sentence=base_config.structure.auto_split_long_sentence,
            chapter_pause=base_config.structure.chapter_pause,
            dialog_pause=base_config.structure.dialog_pause
        )

        return SSMLConfig(
            voice=voice_config,
            pace=pace_config,
            mood=mood_config,
            structure=structure_config,
            name=f"CUSTOM_{preset_name}",
            description=f"基于 {preset_name} 的自定义配置"
        )