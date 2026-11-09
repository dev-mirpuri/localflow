# PyInstaller: the Engine as a folder with one exe, dist/localflow-engine/localflow-engine.exe.
# Built by `npm --prefix app run build:win`; models aren't bundled (Parakeet downloads on first run).
from PyInstaller.utils.hooks import collect_all, collect_submodules

nvidia = ".venv/Lib/site-packages/nvidia"
# Into the exe's folder, where speech.load_speech() preloads them from.
binaries = [(f"{nvidia}/cu13/bin/x86_64/*.dll", "."), (f"{nvidia}/cudnn/bin/*.dll", ".")]
datas = []
hiddenimports = collect_submodules("huggingface_hub")
for package in ("onnx_asr", "onnxruntime"):
    package_datas, package_binaries, package_imports = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_imports

a = Analysis(
    ["src/localflow_engine/__main__.py"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
)
exe = EXE(PYZ(a.pure), a.scripts, exclude_binaries=True, name="localflow-engine", console=True)
coll = COLLECT(exe, a.binaries, a.datas, name="localflow-engine")
