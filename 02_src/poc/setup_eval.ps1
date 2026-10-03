# GPU 機での再評価を 1 コマンドで回す(venv 作成 → 依存導入 → run_eval.py)。
#   powershell -ExecutionPolicy Bypass -File 02_src\poc\setup_eval.ps1 -Backend cuda
# 作業領域は $HOME\imev-eval(約 7GB)、結果は 02_src\poc\results\ に出る。
param(
    [ValidateSet('cuda', 'vulkan', 'cpu')][string]$Backend = 'cuda',
    [string]$Models = '',
    [int]$Repeat = 5,
    [switch]$SkipBench
)
$ErrorActionPreference = 'Stop'
$work = Join-Path $HOME 'imev-eval'
$venv = Join-Path $work 'venv'
$py = Join-Path $venv 'Scripts\python.exe'
if (-not (Test-Path $py)) {
    New-Item -ItemType Directory -Force $work | Out-Null
    # llama-cpp-python 0.3.36 の CPU wheel は 3.12 で確認済み
    if (Get-Command py -ErrorAction SilentlyContinue) { py -3.12 -m venv $venv } else { python -m venv $venv }
}
& $py -m pip install -q -r (Join-Path $PSScriptRoot 'requirements-eval.txt')
if ($LASTEXITCODE -ne 0) { throw 'pip install failed' }
$runArgs = @((Join-Path $PSScriptRoot 'run_eval.py'), '--backend', $Backend, '--work', $work, '--repeat', $Repeat)
if ($Models) { $runArgs += @('--models', $Models) }
if ($SkipBench) { $runArgs += '--skip-bench' }
$env:PYTHONIOENCODING = 'utf-8'
& $py @runArgs
