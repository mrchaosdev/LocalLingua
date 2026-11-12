from dataclasses import dataclass
import os
from urllib.parse import urlparse
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

@dataclass(frozen=True)
class Settings:
    offline_mode: bool = os.getenv("OFFLINE_MODE", "1") == "1"
    asr_backend: str = os.getenv("ASR_BACKEND", "mock").lower()
    translate_backend: str = os.getenv("TRANSLATE_BACKEND", "mock").lower()
    whisper_model: str = os.getenv("WHISPER_MODEL", "small.en")
    whisper_device: str = os.getenv("WHISPER_DEVICE", "cpu")
    whisper_compute: str = os.getenv("WHISPER_COMPUTE", "int8")
    ollama_url: str = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "hf.co/Qwen/Qwen3-4B-GGUF:Q4_K_M")
    rms_threshold: float = float(os.getenv("AUDIO_RMS_THRESHOLD", "0.006"))

    def __post_init__(self):
        endpoint = urlparse(self.ollama_url)
        if endpoint.scheme != 'http' or endpoint.hostname not in ('127.0.0.1', 'localhost', '::1') or endpoint.username or endpoint.password:
            raise ValueError('OLLAMA_URL must be an unauthenticated local HTTP endpoint')
