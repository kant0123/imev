# imev

Mozc(オープンソース日本語 IME)の変換候補を、直前に確定した文を文脈にした小型言語モデルで並べ替える構想の調査・検証リポジトリです。現在は PoC 段階で、Mozc 本体には組み込んでいません。

## 現状の結論

- **推奨構成**: zenz-v3.1-small(74MB)+ llama.cpp。Mozc 側の組み込み先は `ContextRerankRewriter`(新設)を想定しています。
- **CPU(i3-8100)での実測**: 自作の同音異義語 11 問で、文脈ありだと 10 問正解(文脈なしは 4 問)。変換 1 回あたり 8ms、専有メモリの増加は 53MB。
- **汎用 LLM**: Qwen3-0.6B / gemma-3-1b は精度では同等以下で、30ms の予算を超えます。
- **選択式(SemIf / Jev 方式)**: 小さいモデルでは精度・速度とも尤度方式に劣りました。
- **内蔵 GPU(UHD 630)**: すべて CPU より遅い結果でした。
- **未検証**: dGPU 機での評価。手順は引き継ぎ資料にあります。

詳細は [設計書](01_調査・計画/mozc-llm-rerank-設計.md) を参照してください。

## ディレクトリ

| パス | 内容 |
| --- | --- |
| `01_調査・計画/` | 設計書と [GPU 再調査の引き継ぎ](01_調査・計画/GPU再調査-引き継ぎ.md) |
| `02_src/poc/` | リランキング PoC(`context_rerank_poc.py`)、評価ハーネス、評価ケース、計測結果 |
| `wiki/` | プロジェクトの知識ベース。入口は [wiki/overview.md](wiki/overview.md) |
| `review/` | agy(Gemini)による PR レビューの仕組み |
| `docs/` / `scripts/` | 開発フロー・Wiki 運用の説明と補助スクリプト |

## 動かし方(Windows)

GPU 機での一括評価(llama.cpp とモデルの取得、ベンチ、全モデル × 方式 × CPU/GPU の計測)は次のコマンドで実行します。NVIDIA 以外の GPU では `-Backend vulkan` を指定します。

```powershell
powershell -ExecutionPolicy Bypass -File 02_src/poc/setup_eval.ps1 -Backend cuda
```

結果は `02_src/poc/results/` に出力されます。PoC を単体で動かす場合の使い方は `02_src/poc/context_rerank_poc.py` の冒頭にあります。

## 開発の進め方

作業は Issue → worktree → PR → CI → agy レビュー → マージの順に進めます。規約は [CLAUDE.md](CLAUDE.md)、流れの全体像は [docs/development_workflow.md](docs/development_workflow.md) にあります。

## ライセンス上の注意

zenz-v3.1 のモデル重みは CC-BY-SA 4.0 です。モデルを同梱するか別途ダウンロードさせるかは未決です。
