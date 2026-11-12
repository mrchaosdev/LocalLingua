"""Runtime controls contain preferences only; never audio or transcript data."""
import os
import json
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Literal

PROFILES = {
    'fast': dict(asr_interval=0.65, partial_interval=1.3, beam_size=1, max_segment_s=7, output_tokens=100),
    'balanced': dict(asr_interval=0.85, partial_interval=1.3, beam_size=1, max_segment_s=10, output_tokens=120),
    'quality': dict(asr_interval=1.1, partial_interval=1.6, beam_size=3, max_segment_s=11, output_tokens=160),
}

class Preferences(BaseModel):
    source: Literal['discord-process-tree','system-diagnostic'] = 'discord-process-tree'
    endpoint_id: str = Field(default='',max_length=1024)
    discord_pid: int = Field(default=0,ge=0,le=4294967295)
    profile: Literal['fast','balanced','quality'] = 'balanced'
    asr_backend: Literal['mock','whisper'] = 'mock'
    translate_backend: Literal['mock','ollama'] = 'mock'
    whisper_model: str = Field(default='small.en',min_length=1,max_length=1024)
    whisper_device: Literal['cpu','cuda'] = 'cpu'
    whisper_compute: Literal['int8','int8_float16','float16','float32'] = 'int8'
    ollama_model: str = Field(default='locallingua-qwen3-4b:latest',min_length=1,max_length=200)
    vad_model_path: str = Field(default='',max_length=1024)
    overlay_font_size: int = Field(default=26,ge=16,le=48)
    overlay_opacity: float = Field(default=0.92,ge=0.35,le=1)
    overlay_english: bool = True

class PreferenceStore:
    def __init__(self, settings):
        self.directory = Path(os.getenv('LOCALLINGUA_DATA_DIR', str(Path(os.getenv('LOCALAPPDATA',str(Path.home())))/'LocalLingua')))
        self.path = self.directory/'preferences.json'
        defaults = dict(asr_backend=settings.asr_backend,translate_backend=settings.translate_backend,
                        whisper_model=settings.whisper_model,whisper_device=settings.whisper_device,
                        whisper_compute=settings.whisper_compute,ollama_model=settings.ollama_model,
                        vad_model_path=os.getenv('VAD_MODEL_PATH',''))
        self.warning = ''
        try:
            self.value = Preferences.model_validate(json.loads(self.path.read_text(encoding='utf-8-sig'))) if self.path.is_file() else Preferences(**defaults)
        except (ValueError,OSError):
            self.value = Preferences(**defaults)
            self.warning = 'Cấu hình cũ không đọc được; dùng cấu hình mặc định.'
        self.revision = 0

    def save(self, value):
        self.directory.mkdir(parents=True,exist_ok=True)
        temporary = self.path.with_suffix('.tmp')
        temporary.write_text(value.model_dump_json(indent=2),encoding='utf-8')
        temporary.replace(self.path)
        self.value = value
        self.revision += 1
