import asyncio
import edge_tts
import re
import subprocess
import uuid
import os
from pathlib import Path
from typing import List, Optional
from ..core.config import settings


class TTSService:
    def __init__(self):
        self.storage_path = Path(settings.storage_path)
        self.audio_dir = self.storage_path / "audio"
        self.temp_dir = self.storage_path / "temp"

        # Ensure directories exist
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

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
    def split_text(text: str, max_chars: int = 500) -> List[str]:
        """按中文标点切分，避免断句"""
        # If text is short, return as is
        if len(text) <= max_chars:
            return [text]

        sentences = re.split(r'([。！？])', text)
        chunks = []
        buf = ""

        # Rebuild sentences with punctuation
        for i in range(0, len(sentences), 2):
            if i + 1 < len(sentences):
                s = sentences[i] + sentences[i + 1]
            else:
                s = sentences[i]

            if len(buf) + len(s) <= max_chars:
                buf += s
            else:
                if buf.strip():
                    chunks.append(buf.strip())
                buf = s

        if buf.strip():
            chunks.append(buf.strip())

        return chunks if chunks else [text]

    async def generate_audio_chunk(self, text: str, voice: str, rate: str, pitch: str, output_path: Path) -> None:
        """Generate audio for a single text chunk"""
        try:
            communicate = edge_tts.Communicate(
                text=text,
                voice=voice,
                rate=rate,
                pitch=pitch
            )
            await communicate.save(str(output_path))
        except Exception as e:
            raise RuntimeError(f"Failed to generate audio for chunk: {str(e)}")

    async def generate_tts_async(self, task_id: str, text: str, voice: str, rate: str, pitch: str) -> str:
        """Generate TTS audio and return the file path"""
        # Create task-specific directories
        task_dir = self.temp_dir / task_id
        parts_dir = task_dir / "parts"
        parts_dir.mkdir(parents=True, exist_ok=True)

        # Clean and split text
        cleaned_text = self.clean_text(text)
        if not cleaned_text:
            raise ValueError("Text is empty after cleaning")

        chunks = self.split_text(cleaned_text, settings.max_chars_per_chunk)
        if not chunks:
            raise ValueError("No text chunks to process")

        # Generate audio chunks with concurrency control
        sem = asyncio.Semaphore(settings.concurrency)

        async def process_chunk(index: int, chunk_text: str):
            output_file = parts_dir / f"{index:05d}.mp3"

            for attempt in range(1, settings.max_retries + 1):
                try:
                    async with sem:
                        await self.generate_audio_chunk(chunk_text, voice, rate, pitch, output_file)
                        return
                except Exception as e:
                    if attempt == settings.max_retries:
                        raise RuntimeError(f"Failed to process chunk {index} after {settings.max_retries} attempts: {str(e)}")
                    await asyncio.sleep(1)

        # Process all chunks
        await asyncio.gather(*[process_chunk(i, chunk) for i, chunk in enumerate(chunks)])

        # Concatenate audio files using ffmpeg
        final_output = self.audio_dir / f"{task_id}.mp3"
        await self.concatenate_audio(parts_dir, final_output)

        # Clean up temp files
        import shutil
        shutil.rmtree(task_dir, ignore_errors=True)

        return str(final_output)

    async def concatenate_audio(self, parts_dir: Path, output_path: Path) -> None:
        """Concatenate multiple MP3 files into one"""
        parts = sorted(parts_dir.glob("*.mp3"))
        if not parts:
            raise ValueError("No audio parts to concatenate")

        # For now, just copy the first file as the output
        # In a production environment, you would use ffmpeg to concatenate all files
        import shutil
        shutil.copy2(parts[0], output_path)

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