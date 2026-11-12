"""Real ASR-only WAV baseline: python scripts/test_english_wav.py sample.wav.
The test must use a permission-cleared English voice recording, ideally mono 16k WAV PCM16.
"""
import asyncio
import sys
import wave
from pathlib import Path
import numpy as np
from app.config import Settings
from app.providers import Transcriber

async def main(file: Path):
    with wave.open(str(file),'rb') as w:
        if w.getframerate()!=16000 or w.getnchannels()!=1 or w.getsampwidth()!=2:
            raise SystemExit('Convert WAV to PCM16 mono 16kHz before this test')
        x=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').astype(np.float32)/32768.0
    # Set ASR_BACKEND=whisper in environment before running; no hidden default mock.
    provider=Transcriber(Settings())
    if provider.settings.asr_backend!='whisper':
        raise SystemExit('Set ASR_BACKEND=whisper to run actual model inference')
    print(await provider.transcribe(x))

if __name__=='__main__':
    asyncio.run(main(Path(sys.argv[1])))
