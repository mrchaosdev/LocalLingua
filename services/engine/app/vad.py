"""Local ONNX Silero VAD adapter. No model download or remote code execution."""
import numpy as np

class SileroVad:
    def __init__(self, path):
        import onnxruntime as ort
        options = ort.SessionOptions()
        options.inter_op_num_threads = options.intra_op_num_threads = 1
        self.session = ort.InferenceSession(path, sess_options=options, providers=['CPUExecutionProvider'])
        self.reset()

    def reset(self):
        self.state = np.zeros((2, 1, 128), np.float32)
        self.context = np.zeros((1, 64), np.float32)

    def probability(self, samples):
        if samples.size != 512:
            raise ValueError('Silero requires exactly 512 samples at 16kHz')
        audio = np.concatenate((self.context, samples.reshape(1, 512)), axis=1)
        output, self.state = self.session.run(None, dict(input=audio, state=self.state, sr=np.array(16000, np.int64)))
        self.context = audio[:, -64:].copy()
        return float(output[0, 0])
