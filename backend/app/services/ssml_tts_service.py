"""
Custom SSML-enabled TTS service that bypasses edge-tts XML escaping
"""
import asyncio
import aiohttp
import ssl
import time
import uuid
import json
from pathlib import Path
from typing import Dict, Optional
from xml.sax.saxutils import escape, unescape

# Edge TTS constants
WSS_URL = "wss://speech.platform.bing.com/consumer/speech/synthesize/readaloud/edge/v1?TrustedClientToken=6A5AA1D4EAFF4E9FB37E23D68491D6F4"
WSS_HEADERS = {
    "Pragma": "no-cache",
    "Cache-Control": "no-cache",
    "Origin": "chrome-extension://jdiccldimpdaibmpdkjnbmckianbfoldm",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36 Edg/107.0.1418.56",
}

class DRM:
    """Simplified DRM handling for edge-tts compatibility"""

    @staticmethod
    def generate_sec_ms_gec() -> str:
        """Generate a simplified SEC-MS-GEC token"""
        return "13.0.0"

    @staticmethod
    def headers_with_muid(base_headers: Dict[str, str]) -> Dict[str, str]:
        """Add required headers"""
        headers = base_headers.copy()
        headers["X-MMS-Client-User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36 Edg/107.0.1418.56"
        return headers

class SSMLCommunicate:
    """Custom communication class for SSML support"""

    def __init__(self, ssml: str):
        if not isinstance(ssml, str):
            raise TypeError("ssml must be str")

        self.ssml = ssml
        self.session_timeout = aiohttp.ClientTimeout(
            total=None,
            connect=10,
            sock_connect=10,
            sock_read=60,
        )

    def get_headers_and_data(self, data: bytes, header_length: int):
        """Parse headers and data from response"""
        headers = {}
        for line in data[:header_length].split(b"\r\n"):
            if b":" in line:
                key, value = line.split(b":", 1)
                headers[key] = value
        return headers, data[header_length + 2:]

    def connect_id(self) -> str:
        """Generate connection ID"""
        return uuid.uuid4().hex

    def date_to_string(self) -> str:
        """Generate date string"""
        return time.strftime(
            "%a %b %d %Y %H:%M:%S GMT+0000 (Coordinated Universal Time)",
            time.gmtime()
        )

    def ssml_headers_plus_data(self, request_id: str, timestamp: str, ssml: str) -> str:
        """Create headers and data for SSML request"""
        return (
            f"X-RequestId:{request_id}\r\n"
            f"Content-Type:application/ssml+xml\r\n"
            f"X-Timestamp:{timestamp}Z\r\n"
            "Path:ssml\r\n\r\n"
            f"{ssml}"
        )

    def command_headers_plus_data(self, request_id: str, timestamp: str, config: str) -> str:
        """Create headers and data for command request"""
        return (
            f"X-RequestId:{request_id}\r\n"
            "Content-Type:application/json; charset=utf-8\r\n"
            f"X-Timestamp:{timestamp}Z\r\n"
            "Path:control.config\r\n\r\n"
            f"{config}"
        )

    async def save(self, output_file: str) -> None:
        """Save audio to file"""
        audio_data = b""

        async def send_command_request(websocket):
            """Send command request to configure TTS"""
            config = json.dumps({
                "context": {
                    "synthesis": {
                        "audio": {
                            "outputFormat": "audio-24khz-48kbitrate-mono-mp3"
                        }
                    }
                }
            })

            await websocket.send_str(
                self.command_headers_plus_data(
                    self.connect_id(),
                    self.date_to_string(),
                    config
                )
            )

        async def send_ssml_request(websocket):
            """Send SSML request"""
            await websocket.send_str(
                self.ssml_headers_plus_data(
                    self.connect_id(),
                    self.date_to_string(),
                    self.ssml
                )
            )

        ssl_ctx = ssl.create_default_context()

        async with aiohttp.ClientSession(
            trust_env=True,
            timeout=self.session_timeout,
        ) as session, session.ws_connect(
            f"{WSS_URL}&ConnectionId={self.connect_id()}&Sec-MS-GEC={DRM.generate_sec_ms_gec()}&Sec-MS-GEC-Version=13.0.0",
            compress=15,
            headers=DRM.headers_with_muid(WSS_HEADERS),
            ssl=ssl_ctx,
        ) as websocket:

            await send_command_request(websocket)
            await send_ssml_request(websocket)

            audio_was_received = False

            async for received in websocket:
                if received.type == aiohttp.WSMsgType.TEXT:
                    encoded_data = received.data.encode("utf-8")
                    try:
                        header_length = encoded_data.find(b"\r\n\r\n")
                        if header_length > 0:
                            parameters, data = self.get_headers_and_data(encoded_data, header_length)
                            path = parameters.get(b"Path", None)

                            if path == b"audio":
                                audio_data += data
                                audio_was_received = True
                    except:
                        continue

                elif received.type == aiohttp.WSMsgType.ERROR:
                    raise RuntimeError(f"WebSocket error: {received}")

            if not audio_was_received:
                raise RuntimeError("No audio data received")

        # Save the audio data
        with open(output_file, "wb") as f:
            f.write(audio_data)


# Simple wrapper for backward compatibility
def ssml_communicate(ssml: str, output_file: str) -> None:
    """Synchronous wrapper for SSML communication"""
    async def async_save():
        communicator = SSMLCommunicate(ssml)
        await communicator.save(output_file)

    # 检查是否已经在事件循环中
    try:
        loop = asyncio.get_running_loop()
        # 如果已经在运行事件循环，使用run_until_complete
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(lambda: asyncio.run(async_save()))
            future.result()
    except RuntimeError:
        # 没有运行的事件循环，使用asyncio.run
        asyncio.run(async_save())