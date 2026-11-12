import numpy as np
from app.audio import AudioFormat, AudioNormalizer, rms

def test_pcm16_stereo_to_mono():
    fmt = AudioFormat.from_message({'type':'audio.format','sample_rate':16000,'channels':2,'sample_format':'pcm16'})
    # L=+0.5, R=-0.5 => near zero after downmix.
    raw=np.array([16384,-16384]*320,dtype='<i2').tobytes()
    y=AudioNormalizer(fmt).convert(raw)
    assert y.size==320
    assert np.max(np.abs(y))<1e-6

def test_float32_resample():
    fmt=AudioFormat.from_message({'type':'audio.format','sample_rate':48000,'channels':1,'sample_format':'float32'})
    t=np.arange(4800,dtype=np.float32)/48000.0
    data=np.sin(2*np.pi*440*t).astype('<f4').tobytes()
    y=AudioNormalizer(fmt).convert(data)
    assert abs(y.size-1600)<3
    assert 0.4 < rms(y)<0.9

def test_unsupported_format():
    try:
        AudioFormat.from_message({'type':'audio.format','sample_rate':12345,'channels':2,'sample_format':'float32'})
    except ValueError: pass
    else: raise AssertionError('must reject unknown sampling rate')
