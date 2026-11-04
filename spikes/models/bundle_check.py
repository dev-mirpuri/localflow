"""THROWAWAY spike S1. Entry point for the PyInstaller exe: does a bundled Parakeet run on CUDA?"""

import sys
import time

import onnx_asr
import onnxruntime as ort

ort.set_default_logger_severity(3)
ort.preload_dlls(directory=getattr(sys, "_MEIPASS", None))
model = onnx_asr.load_model("nemo-parakeet-tdt-0.6b-v2", providers=["CUDAExecutionProvider"])
providers = model.asr._encoder.get_providers()
print("providers:", providers)
model.recognize(sys.argv[1])
start = time.perf_counter()
text = model.recognize(sys.argv[1])
print(f"warm transcribe: {time.perf_counter() - start:.3f} s")
print("transcript:", text)
sys.exit(0 if providers[0] == "CUDAExecutionProvider" else 1)
