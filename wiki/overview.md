---
type: concept
summary: システム全体像と各ページへの入口
updated: 2026-10-04
related: [recurring-review-findings, rerank-poc, mozc-context-rerank, engine-base-choice]
---

# imev 全体像

> このページは Wiki の入口。**新しくこのプロジェクトに関わる人間 / エージェントが
> 最初に読む 1 枚**として維持する。詳細は各ページへリンクで逃がし、ここは俯瞰に徹する。
> プレースホルダーを実プロジェクトの値に置き換えて使う。

## これは何か

Mozc(オープンソース日本語 IME)に小型の言語モデルを組み込み、直前に確定した文を文脈として
変換候補を並べ替える。PoC で方式を決めたあと、Mozc 本家に Rewriter として組み込み、
手元の PC で常用を始めた段階(配布はしていない)。

## 構成

- 候補リランキング PoC と評価ハーネス ([[rerank-poc]]) — `02_src/poc/`。llama.cpp で候補を採点し、モデル × 方式 × CPU/GPU を計測する
- Mozc 文脈リランカー ([[mozc-context-rerank]]) — `02_src/mozc/`。google/mozc へのパッチ。ビルドと導入は [[mozc-build-install]]
- 調査・設計書と引き継ぎ資料 — `01_調査・計画/`(Wiki ではなく計画資料として置いている)

<!-- 例:
- Web アプリ本体 ([[web-app]]) — Flask。リクエストを受けて DB を読み書きする
- 夜間バッチ ([[batch-updater]]) — 外部 API から最新情報を取得して DB を更新する
- 通知 ([[notification]]) — バッチの結果を外部サービスへ送る。失敗しても本体は止めない
-->

## 主要な設計判断

- 土台は Mozc 本家。Ohagey(azooKey + Zenzai)は精度が同等で速度・32 ビット対応に難があった。[[engine-base-choice]]

<!-- 例:
- DB は <engine> を使う。理由と、途中で変えられなくなった経緯は [[db-choice]]
- 外部送信は best-effort。[[error-handling-policy]]
-->

## 触る前に知っておくこと

<初見で必ず踏む落とし穴を 3〜5 個。詳細は各ページへ>

- mozc_server はサンドボックスで動き、ユーザープロファイル配下を読めない。ランタイムは Mozc のインストール先に置く([[mozc-context-rerank]])
- レビューで繰り返し差し戻された誤りの種類は [[recurring-review-findings]]。着手時と push 前に読む

## 運用

<デプロイ・バックアップ・監視の入口。詳細は operations/ の各ページへ>
