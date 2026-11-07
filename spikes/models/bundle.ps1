# THROWAWAY spike S1. Run from spikes/models: builds the exe, runs it, prints its size.
$ErrorActionPreference = "Stop"
$nvidia = ".venv/Lib/site-packages/nvidia"
uv run pyinstaller --noconfirm --onedir --name s1_bundle `
    --collect-all onnx_asr --collect-all onnxruntime `
    --collect-submodules huggingface_hub `
    --add-binary "$nvidia/cu13/bin/x86_64/*.dll;." `
    --add-binary "$nvidia/cudnn/bin/*.dll;." `
    bundle_check.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

$output = & dist/s1_bundle/s1_bundle.exe ../../eval/audio/01.wav
$code = $LASTEXITCODE
$bytes = (Get-ChildItem dist/s1_bundle -Recurse -File | Measure-Object Length -Sum).Sum
$size = "bundle size: {0:N2} GB" -f ($bytes / 1GB)
New-Item -ItemType Directory -Force results | Out-Null
@($output) + "exit code: $code" + $size | Tee-Object results/bundle.txt
