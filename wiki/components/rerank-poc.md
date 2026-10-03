---
type: component
summary: 文脈つき候補リランキングの PoC と評価ハーネス(02_src/poc)。llama.cpp の KV 操作・GPU DLL 差し替え・zenz 読み込みの落とし穴
updated: 2026-10-04
related: [overview]
---

# 候補リランキング PoC と評価ハーネス

Mozc の変換候補を、直前の確定文を文脈にした小型 LM で並べ替える構想の検証コード。
Mozc 本体にはまだ組み込んでいない。設計の全体と Mozc 側のフック位置は
`01_調査・計画/mozc-llm-rerank-設計.md`、GPU 機での再評価手順は `01_調査・計画/GPU再調査-引き継ぎ.md`。

## 責務

- 確定文を KV キャッシュに先読みし、変換時は候補トークンだけを 1 バッチで流して並べ替える(生成はしない)
- 方式の比較: 尤度方式(`zenz` / `plain`)と、SemIf(旧 OpenJev)/ Jev 型の選択式(`choice`)
- モデル × 方式 × CPU/GPU の総当たり計測と結果表の作成

Mozc への組み込み(C++ 化、Rewriter 追加)はしない。

## 入口となるファイル

| パス | 役割 |
| --- | --- |
| `02_src/poc/context_rerank_poc.py:178 _sync()` | KV を「今あるべきプレフィックス」に最長共通接頭辞で合わせる。確定・打鍵・巻き戻しはすべてここを通る |
| `02_src/poc/context_rerank_poc.py:242 rank()` | 候補ごとに `seq_cp` で分岐し 1 回の decode で採点、`seq_rm` で破棄 |
| `02_src/poc/run_eval.py:101 main()` | 公式 llama.cpp とモデルの取得、llama-bench、PoC 総当たり、`results/` への表出力 |
| `02_src/poc/setup_eval.ps1` | 別 PC での入口(venv 作成 → 依存導入 → `run_eval.py`) |
| `02_src/poc/semif_bridge.py:23 export()` | `cases.jsonl` を SemIf 本家の `semif-score` 入力に変換し、出力を採点する |

## 依存関係

- 依存している: llama-cpp-python 0.3.36(ctypes バインディングのみ)、llama.cpp 公式リリース b11352 の DLL、Hugging Face のモデル
- 依存されている: なし(Mozc 組み込み前)

## 落とし穴

すべて実際に踏んだもの。

- **zenz の GGUF は本家 llama.cpp で読めない。** pre-tokenizer 名 `gpt2-small-japanese-char` が未登録でロードが失敗する。語彙は文字単位なので `tokenizer.ggml.pre=default` の上書きで正しく分割される(`ContextScorer.__init__()` の `kv_overrides`)。`llama-bench` は上書きを受け取れないので、`run_eval.py fetch_models()` がこのキーを消したコピー(`*-nopre.gguf`)を作る。
- **公式ビルドの GPU バックエンドは別 DLL で、明示的にロードしないと CPU しか使われない。** しかも引数なしの `ggml_backend_load_all()` は python.exe のフォルダを探すので、DLL のフォルダを `ggml_backend_load_all_from_path()` に渡す必要がある(`load_gpu_backends()`)。`ggml_backend_dev_description` は `ggml.dll` ではなく `ggml-base.dll` にある。
- **GPU 版 DLL では `ngl=0` でも GPU が使われる(op_offload)。** 32 トークン以上のバッチは重みが CPU 側でも自動で GPU に回る。i3-8100 + UHD 630 では選択式の CPU 計測が 335ms → 1080ms に汚れた。CPU の基準値は CPU 専用ビルドで測る(`run_eval.py main()` が ngl ごとに DLL を切り替える)。
- **llama-cpp-python と llama.cpp DLL の版は組で固定する。** 0.3.36 × b11352 で ABI 互換を確認済み。片方だけ上げると構造体がずれうる。
- **再帰層を持つモデル(Qwen3.5 系)は KV を途中位置まで巻き戻せない。** `llama_memory_seq_rm` の部分削除が False を返し、そのまま decode すると失敗する。`_rollback()` は全消去して流し直す(遅い)。候補の分岐(`seq_cp` で丸ごと複製)は動く。
- **logits バッファは n_batch × 語彙数 × 4 バイト確保される。** 語彙 15 万の Qwen3 で n_batch=512 にすると +300MB。PoC は 64。
- **日本語 Windows の pip は requirements を cp932 で読む。** `requirements-eval.txt` に日本語コメントを書くと導入が失敗する。

## 経緯

- 2026-10-03〜04: i3-8100(4C/4T)で測定。zenz-v3.1-small が rank 8.7ms・11 問中 10 で最良。Qwen3-0.6B は尤度方式 9/11・48ms、選択式 7/11・335ms。内蔵 GPU(UHD 630, Vulkan)はすべての条件で CPU より遅かった。数値は `02_src/poc/results/` と設計書 §2〜§4。Issue #1。
