import struct
import pytest
from app.transport import CaptureFrame
from app.export import export_captions

def test_frame_metadata_and_size_validation():
    raw=struct.pack('<4sIQQQQ',b'LLA2',4,7,320,123400000,2)+b'\x00'*4
    frame=CaptureFrame.parse(raw)
    assert (frame.sequence,frame.sample_index,frame.end_ns,frame.dropped)==(7,320,123400000,2)
    with pytest.raises(ValueError):CaptureFrame.parse(raw[:-1])

def test_srt_uses_source_time_and_rejects_untimed_demo():
    event=dict(phase='translation.final',created_at_ms=1,english='Do not launch.',vietnamese='Không ra mắt.',audio_start_ms=200,audio_end_ms=1700)
    assert '00:00:00,000 --> 00:00:01,500' in export_captions([event],'srt')
    event.pop('audio_start_ms')
    with pytest.raises(ValueError):export_captions([event],'srt')
