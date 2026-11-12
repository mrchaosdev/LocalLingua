from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import soxr

@dataclass(frozen=True)
class AudioFormat:
    sample_rate: int
    channels: int
    sample_format: str

    @staticmethod
    def from_message(d):
        if d.get('type') != 'audio.format':
            raise ValueError('First message must be audio.format')
        sr, ch, fmt = d['sample_rate'], d['channels'], d['sample_format']
        if type(sr) is not int or sr not in (16000, 44100, 48000):
            raise ValueError('Unsupported sample rate')
        if type(ch) is not int or not 1 <= ch <= 8 or fmt not in ('float32', 'pcm16'):
            raise ValueError('Unsupported PCM stream format')
        return AudioFormat(sr, ch, fmt)

class AudioNormalizer:
    """Streaming bandlimited conversion; filter state survives frame boundaries."""
    def __init__(self, fmt):
        self.fmt = fmt
        self.dtype = np.dtype('<f4' if fmt.sample_format == 'float32' else '<i2')
        self.bytes_per_sample = self.dtype.itemsize * fmt.channels
        self.remainder = b''
        self.resampler = (soxr.ResampleStream(fmt.sample_rate, 16000, 1, dtype='float32', quality='HQ')
                          if fmt.sample_rate != 16000 else None)

    def convert(self, raw):
        raw = self.remainder + raw
        count = len(raw) // self.bytes_per_sample * self.bytes_per_sample
        self.remainder = raw[count:]
        if not count:
            return np.zeros(0, dtype=np.float32)
        x = np.frombuffer(raw[:count], dtype=self.dtype).astype(np.float32)
        if self.fmt.sample_format == 'pcm16':
            x /= 32768.0
        if not np.isfinite(x).all():
            raise ValueError('Non-finite audio samples')
        x = x.reshape(-1, self.fmt.channels).mean(axis=1)
        if self.resampler:
            x = self.resampler.resample_chunk(x)
        return np.clip(x, -1, 1).astype(np.float32, copy=False)

    def finish(self):
        if self.remainder:
            raise ValueError('Truncated PCM sample')
        if self.resampler:
            return self.resampler.resample_chunk(np.zeros(0, np.float32), last=True)
        return np.zeros(0, np.float32)

def rms(samples):
    return float(np.sqrt(np.mean(np.square(samples.astype(np.float64))))) if samples.size else 0.0
