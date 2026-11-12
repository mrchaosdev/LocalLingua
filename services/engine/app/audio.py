from __future__ import annotations
from dataclasses import dataclass
from math import gcd
import numpy as np
from scipy.signal import resample_poly

@dataclass(frozen=True)
class AudioFormat:
    sample_rate: int
    channels: int
    sample_format: str

    @staticmethod
    def from_message(d: dict) -> "AudioFormat":
        if d.get("type") != "audio.format":
            raise ValueError("First message must be audio.format")
        sr, ch, fmt = int(d["sample_rate"]), int(d["channels"]), d["sample_format"]
        if sr not in (16000, 44100, 48000) or not (1 <= ch <= 8) or fmt not in ("float32", "pcm16"):
            raise ValueError("Unsupported PCM stream format")
        return AudioFormat(sr, ch, fmt)

class AudioNormalizer:
    """Diagnostic resampler. Replace independent-frame resampling with stateful DSP in M3."""
    def __init__(self, fmt: AudioFormat):
        self.fmt = fmt
        self.dtype = np.dtype("<f4") if fmt.sample_format == "float32" else np.dtype("<i2")
        self.bytes_per_sample = self.dtype.itemsize * fmt.channels
        self.remainder = b""

    def convert(self, raw: bytes) -> np.ndarray:
        raw = self.remainder + raw
        byte_count = len(raw) // self.bytes_per_sample * self.bytes_per_sample
        self.remainder = raw[byte_count:]
        if not byte_count:
            return np.zeros(0, dtype=np.float32)
        a = np.frombuffer(raw[:byte_count], dtype=self.dtype)
        x = a.astype(np.float32, copy=False)
        if self.fmt.sample_format == "pcm16":
            x = x / 32768.0
        if self.fmt.channels > 1:
            x = x.reshape(-1, self.fmt.channels).mean(axis=1)
        if self.fmt.sample_rate != 16000:
            g = gcd(self.fmt.sample_rate, 16000)
            x = resample_poly(x, 16000 // g, self.fmt.sample_rate // g)
        return np.clip(x, -1, 1).astype(np.float32, copy=False)


def rms(samples: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(samples.astype(np.float64))))) if samples.size else 0.0
