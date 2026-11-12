"""Unit checks never inherit the owner's real GPU profile or private configuration."""
import atexit
import os
import tempfile

_settings=tempfile.TemporaryDirectory(prefix='locallingua-unit-')
atexit.register(_settings.cleanup)
os.environ.update(LOCALLINGUA_DATA_DIR=_settings.name,ASR_BACKEND='mock',TRANSLATE_BACKEND='mock',
                  VAD_MODEL_PATH='',OFFLINE_MODE='1',WHISPER_DEVICE='cpu',WHISPER_COMPUTE='int8')
