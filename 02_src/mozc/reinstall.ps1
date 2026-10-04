# ビルドした Mozc64.msi を入れ直し、リランカーのランタイムを配置する。管理者で実行する。
# 同じバージョンの MSI は既存ファイルを上書きしないため、プロセスを止めてから
# アンインストール → REINSTALLMODE=amus で入れる。背景は wiki/operations/mozc-build-install.md。
param(
    [Parameter(Mandatory)] [string]$Msi,
    [string]$RuntimeDir = (Join-Path $env:LOCALAPPDATA 'MozcRerank')
)
$ErrorActionPreference = 'Stop'
$procs = 'mozc_server', 'mozc_renderer', 'mozc_cache_service', 'mozc_broker'

Get-Process $procs -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Process msiexec.exe -ArgumentList '/x', $Msi, '/passive', '/norestart' -Wait
Get-Process $procs -ErrorAction SilentlyContinue | Stop-Process -Force
$p = Start-Process msiexec.exe -ArgumentList '/i', $Msi, 'REINSTALLMODE=amus', '/passive', '/norestart' -Wait -PassThru
if ($p.ExitCode -ne 0) { throw "msiexec exit $($p.ExitCode)" }

# サーバーは低整合性のサンドボックスで動き、ユーザープロファイル配下を読めない。
# 実行ファイルと同じ場所(<exe dir>\rerank)なら読める。
$dst = Join-Path ${env:ProgramFiles(x86)} 'Mozc\rerank'
New-Item -ItemType Directory -Force $dst | Out-Null
Copy-Item (Join-Path $RuntimeDir '*') $dst -Force
# 次のキー入力で新しいサーバーが起動する
Get-Process mozc_server -ErrorAction SilentlyContinue | Stop-Process -Force
Write-Host "installed: $dst"
