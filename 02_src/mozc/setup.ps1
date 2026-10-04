# Mozc に文脈リランカーのパッチを当て、ビルドとインストールに要るファイルを揃える。
# 手順と背景は wiki/operations/mozc-build-install.md。
param(
    # google/mozc のチェックアウト(c7538e6 で検証)。UNC パス不可(Qt の configure が通らない)
    [string]$MozcRoot = 'C:\mozc',
    # インストール時に Program Files (x86)\Mozc\rerank へコピーする元
    [string]$RuntimeDir = (Join-Path $env:LOCALAPPDATA 'MozcRerank')
)
$ErrorActionPreference = 'Stop'
$tag = 'b4846'  # zenz の pre-tokenizer を持つ azooKey フォーク。ヘッダと DLL は同じタグで揃える

# 1. パッチ(当て済みなら飛ばす)
$patch = Join-Path $PSScriptRoot 'context-rerank.patch'
# PowerShell 5.1 は Stop のもとで native コマンドの stderr を例外にするので、判定だけ cmd 経由で黙らせる
function Test-Apply([string]$extra) {
    cmd /c "git -C `"$MozcRoot`" apply $extra --check `"$patch`" 2>nul"
    return $LASTEXITCODE -eq 0
}
if (Test-Apply '') {
    git -C $MozcRoot apply $patch
    if ($LASTEXITCODE -ne 0) { throw 'git apply に失敗した' }
} elseif (Test-Apply '--reverse') {
    Write-Host 'patch: 当て済み'
} else {
    throw 'パッチが当たらない(Mozc のリビジョンを確認する)'
}

# 2. llama.cpp のヘッダ(リンクはせず、llm_scorer.cc が実行時に LoadLibrary する)
$inc = Join-Path $MozcRoot 'src\rewriter\llama_api\include'
New-Item -ItemType Directory -Force $inc | Out-Null
$base = "https://raw.githubusercontent.com/azooKey/llama.cpp/$tag"
foreach ($p in 'include/llama.h', 'ggml/include/ggml.h', 'ggml/include/ggml-cpu.h',
               'ggml/include/ggml-backend.h', 'ggml/include/ggml-alloc.h', 'ggml/include/gguf.h') {
    Invoke-WebRequest "$base/$p" -OutFile (Join-Path $inc (Split-Path $p -Leaf)) -UseBasicParsing
}

# 3. ランタイム DLL とモデル
New-Item -ItemType Directory -Force $RuntimeDir | Out-Null
$tmp = Join-Path $env:TEMP "llama-$tag"
$zip = "$tmp.zip"
Invoke-WebRequest "https://github.com/azooKey/llama.cpp/releases/download/$tag/llama-$tag-bin-win-avx-x64.zip" -OutFile $zip -UseBasicParsing
Expand-Archive $zip $tmp -Force
foreach ($d in 'llama', 'ggml', 'ggml-base', 'ggml-cpu', 'ggml-rpc') {
    Copy-Item (Join-Path $tmp "$d.dll") $RuntimeDir -Force
}
$model = Join-Path $RuntimeDir 'ggml-model-Q5_K_M.gguf'
if (-not (Test-Path $model)) {
    # 中断で途中までのファイルが残ると次回の存在チェックを素通りするので、別名に落としてから改名する
    $part = "$model.part"
    Invoke-WebRequest 'https://huggingface.co/Miwa-Keita/zenz-v3.1-small-gguf/resolve/main/ggml-model-Q5_K_M.gguf' -OutFile $part -UseBasicParsing
    Move-Item $part $model -Force
}
Write-Host "runtime: $RuntimeDir"
