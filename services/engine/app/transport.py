"""Wire v2: <4sIQQQQ little endian + PCM. Native QPC ns is calibrated in handshake."""
import struct
from dataclasses import dataclass

HEADER = struct.Struct('<4sIQQQQ')

@dataclass
class CaptureFrame:
    sequence: int
    sample_index: int
    end_ns: int
    dropped: int
    pcm: bytes

    @classmethod
    def parse(cls, raw):
        if len(raw)<HEADER.size: raise ValueError('Short audio frame')
        magic,size,seq,index,end,drops = HEADER.unpack_from(raw)
        if magic != b'LLA2' or size != len(raw)-HEADER.size: raise ValueError('Invalid framed PCM')
        return cls(seq,index,end,drops,raw[HEADER.size:])
