"""GPU 機での再評価を一括で回す: llama.cpp 公式ビルドとモデルを取得し、
llama-bench(CPU vs GPU)と PoC(全モデル × 方式 × CPU/GPU)を実行して結果表を書く。

  python run_eval.py --backend cuda            # NVIDIA
  python run_eval.py --backend vulkan          # AMD / Intel / NVIDIA 共通
  python run_eval.py --backend cuda --models zenz-small,qwen3-0.6b-q4_0 --repeat 3   # 一部だけ

作業領域(モデル・バイナリ、約 7GB)は --work(既定 ~/imev-eval)、結果は
02_src/poc/results/<ホスト名>-<backend>-<日付>.{md,jsonl} に出る。Windows 前提
(Linux では llama.cpp を自前ビルドし --lib-dir / --bench-dir で場所を渡す)。
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import platform
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
POC = HERE / "context_rerank_poc.py"
# llama-cpp-python 0.3.36 の ctypes 定義と ABI が一致することを確認済みのビルド。
# 上げる場合は CPU で PoC が通るか(正解率が変わらないか)を先に確かめる。
LLAMA_BUILD = "b11352"
RELEASE = f"https://github.com/ggml-org/llama.cpp/releases/download/{LLAMA_BUILD}"
ASSETS = {
    "cpu": [f"llama-{LLAMA_BUILD}-bin-win-cpu-x64.zip"],
    "vulkan": [f"llama-{LLAMA_BUILD}-bin-win-vulkan-x64.zip"],
    "cuda": [f"llama-{LLAMA_BUILD}-bin-win-cuda-12.4-x64.zip", "cudart-llama-bin-win-cuda-12.4-x64.zip"],
}

# (キー, HF リポジトリ, ファイル名 or 末尾一致パターン, revision, PoC の方式)
# semif-* は SemIf(旧 OpenJev)がブラウザ版で固定している GGUF と同じもの(manifests/models.json)
MODELS = [
    ("zenz-small", "Miwa-Keita/zenz-v3.1-small-gguf", "ggml-model-Q5_K_M.gguf", None, ["zenz"]),
    ("zenz-xsmall", "Miwa-Keita/zenz-v3.1-xsmall-gguf", ".gguf", None, ["zenz"]),
    ("qwen3-0.6b-q4_0", "bartowski/Qwen_Qwen3-0.6B-GGUF", "Qwen_Qwen3-0.6B-Q4_0.gguf", None, ["plain", "choice"]),
    ("semif-qwen3-0.6b-q8_0", "Qwen/Qwen3-0.6B-GGUF", "Q8_0.gguf",
     "23749fefcc72300e3a2ad315e1317431b06b590a", ["plain", "choice"]),
    ("semif-minicpm5-2b-q4_k_m", "openbmb/MiniCPM5-2B-GGUF", "Q4_K_M.gguf",
     "2079a22f3beaa4e306449978533478fe0522f4b3", ["plain", "choice"]),
    ("semif-qwen3.5-4b-q4_k_m", "bartowski/Qwen_Qwen3.5-4B-GGUF", "Qwen_Qwen3.5-4B-Q4_K_M.gguf",
     "4168f45a16a1290d65a4ec0fa312ae917a4c15d6", ["plain", "choice"]),
]


def sh(cmd: list[str], env: dict | None = None, timeout: int = 7200) -> str:
    print("$", " ".join(cmd), flush=True)
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=env, timeout=timeout)
    if p.returncode != 0:
        print(p.stdout[-3000:], p.stderr[-3000:], sep="\n")
    return p.stdout + ("" if p.returncode == 0 else f"\n[exit {p.returncode}]\n{p.stderr[-1500:]}")


def fetch_llama(work: Path, backend: str) -> Path:
    dst = work / "llama.cpp" / f"{LLAMA_BUILD}-{backend}"
    if (dst / "llama-bench.exe").exists():
        return dst
    dst.mkdir(parents=True, exist_ok=True)
    for name in ASSETS[backend]:
        z = work / "llama.cpp" / name
        if not z.exists():
            print("download", name, flush=True)
            urllib.request.urlretrieve(f"{RELEASE}/{name}", z)
        with zipfile.ZipFile(z) as f:
            f.extractall(dst)  # cudart の DLL も同じフォルダに置く
    return dst


def fetch_models(work: Path, only: set[str] | None) -> list[dict]:
    from huggingface_hub import hf_hub_download, list_repo_files
    out = []
    for key, repo, pat, rev, styles in MODELS:
        if only and key not in only:
            continue
        files = [f for f in list_repo_files(repo, revision=rev) if f.endswith(pat)]
        if not files:
            print(f"[skip] {repo} に {pat} が無い", flush=True)
            continue
        path = Path(hf_hub_download(repo, files[0], revision=rev, local_dir=work / "models" / key))
        bench = path
        if "zenz" in styles:
            # llama-bench は kv_override を取れないので、未知の pre-tokenizer 名を消したコピーを使う
            bench = path.with_name(path.stem + "-nopre.gguf")
            if not bench.exists():
                sh([sys.executable, "-m", "gguf.scripts.gguf_new_metadata", "--remove-metadata",
                    "tokenizer.ggml.pre", "--force", str(path), str(bench)])
        out.append({"key": key, "path": str(path), "bench": str(bench), "styles": styles,
                    "mb": round(path.stat().st_size / 2**20)})
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", choices=["cuda", "vulkan", "cpu"], required=True)
    ap.add_argument("--work", default=str(Path.home() / "imev-eval"))
    ap.add_argument("--models", help="カンマ区切りのキーで絞る(既定: 全部)")
    ap.add_argument("--threads", type=int, default=min(8, os.cpu_count() or 4))
    ap.add_argument("--repeat", type=int, default=5)
    ap.add_argument("--skip-bench", action="store_true")
    args = ap.parse_args()

    work = Path(args.work); work.mkdir(parents=True, exist_ok=True)
    gpu = fetch_llama(work, args.backend)
    cpu = fetch_llama(work, "cpu")
    models = fetch_models(work, set(args.models.split(",")) if args.models else None)

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M")
    res_dir = HERE / "results"; res_dir.mkdir(exist_ok=True)
    base = res_dir / f"{platform.node()}-{args.backend}-{stamp}"
    jsonl, md = base.with_suffix(".jsonl"), base.with_suffix(".md")

    lines = [f"# 再評価結果 {platform.node()} / {args.backend} / {stamp}", "",
             f"- CPU: {platform.processor()} / threads={args.threads}",
             f"- llama.cpp {LLAMA_BUILD}, llama-cpp-python のバインディング + 公式 DLL", ""]
    devs = sh([str(gpu / "llama-cli.exe"), "--list-devices"])
    lines += ["## デバイス", "```", devs.strip(), "```", ""]

    if not args.skip_bench:
        lines += ["## llama-bench(文脈 32 トークン後に 1/4/8/64 トークンを 1 バッチ)", "",
                  "ms/バッチ = トークン数 ÷ t/s。64 は選択式プロンプトの読み+候補部分に相当。", ""]
        for m in models:
            for name, exe, extra in [("CPU", cpu, ["-t", str(args.threads)]), ("GPU", gpu, ["-ngl", "99"])]:
                out = sh([str(exe / "llama-bench.exe"), "-m", m["bench"], "-p", "1,4,8,64", "-n", "0",
                          "-d", "32", "-r", "5", "-o", "md"] + extra)
                lines += [f"### {m['key']} — {name}", "", out.strip(), ""]

    for m in models:
        for style in m["styles"]:
            for ngl in (0, 99):
                # ngl=0 でも GPU 版 DLL だと 32 トークン以上のバッチは自動で GPU に回される
                # (op_offload)。CPU の基準値は CPU 専用ビルドで測る。
                env = dict(os.environ, LLAMA_CPP_LIB_PATH=str(gpu if ngl else cpu), PYTHONIOENCODING="utf-8")
                out = sh([sys.executable, str(POC), m["path"], "--style", style, "--ngl", str(ngl),
                          "--threads", str(args.threads), "--repeat", str(args.repeat),
                          "--quiet", "--out", str(jsonl), "--label", m["key"]], env=env)
                (base.parent / f"{base.name}-{m['key']}-{style}-ngl{ngl}.log").write_text(out, encoding="utf-8")

    recs = [json.loads(s) for s in jsonl.read_text(encoding="utf-8").splitlines()] if jsonl.exists() else []
    size = {m["key"]: m["mb"] for m in models}
    lines += ["## PoC(cases.jsonl, rank = 変換キー押下時の処理時間)", "",
              "| モデル | MB | 方式 | ngl | 正解 | 文脈なし | rank 中央値 ms | rank 最大 ms | commit ms | 1 打鍵 ms |",
              "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for r in recs:
        lines.append(f"| {r['model']} | {size.get(r['model'], '')} | {r['style']} | {r['ngl']} | "
                     f"{r['acc']}/{r['n_cases']} | {r['acc_no_ctx']}/{r['n_cases']} | {r['rank_ms']} | "
                     f"{r['rank_max_ms']} | {r['commit_ms']} | {r['key_ms']} |")
    missing = [f"{m['key']}/{s}/ngl{g}" for m in models for s in m["styles"] for g in (0, 99)
               if not any(r["model"] == m["key"] and r["style"] == s and r["ngl"] == g for r in recs)]
    if missing:
        lines += ["", "失敗した組み合わせ(同名の .log を参照): " + ", ".join(missing)]
    md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n==>", md)


if __name__ == "__main__":
    main()
