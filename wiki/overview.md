---
type: concept
summary: システム全体像と各ページへの入口
updated: 2026-10-05
related: [recurring-review-findings, rerank-poc, mozc-context-rerank, engine-base-choice, mozc-build-install]
---

# imev 全体像

> このページは Wiki の入口。**新しくこのプロジェクトに関わる人間 / エージェントが
> 最初に読む 1 枚**として維持する。詳細は各ページへリンクで逃がし、ここは俯瞰に徹する。

## これは何か

Mozc(オープンソース日本語 IME)に小型の言語モデルを組み込み、直前に確定した文を文脈として
変換候補を並べ替える。PoC で方式を決めたあと、Mozc 本家に Rewriter として組み込み、
手元の PC で常用を始めた段階(配布はしていない)。

## 構成

- 候補リランキング PoC と評価ハーネス ([[rerank-poc]]) — `02_src/poc/`。llama.cpp で候補を採点し、モデル × 方式 × CPU/GPU を計測する
- Mozc 文脈リランカー ([[mozc-context-rerank]]) — `02_src/mozc/`。google/mozc へのパッチ。ビルドと導入は [[mozc-build-install]]
- 調査・設計書と引き継ぎ資料 — `01_調査・計画/`(Wiki ではなく計画資料として置いている)

## 主要な設計判断

- 土台は Mozc 本家。Ohagey(azooKey + Zenzai)は精度が同等で速度・32 ビット対応に難があった。[[engine-base-choice]]

## 触る前に知っておくこと

- mozc_server はサンドボックスで動き、ユーザープロファイル配下を読めない。ランタイムは Mozc のインストール先に置く([[mozc-context-rerank]])
- レビューで繰り返し差し戻された誤りの種類は [[recurring-review-findings]]。着手時と push 前に読む

## 運用

配布・デプロイは無い。手元の PC にビルドして入れるだけ([[mozc-build-install]])。テンプレート由来の CD 一式(`deploy/`・deploy ワークフロー)は使わないので取り除いた(Issue #18)。

- **CI(`.github/workflows/test.yml`)は Mozc をビルドしない。** Bazel + MSVC + Qt のビルドは数十分以上かかり、
  Windows ランナーに Qt とツールチェーンを揃える手間も見合わないため。代わりに、数分で回って壊れていれば確実に
  赤になるものだけを見る: パッチが基準コミット(`02_src/mozc/mozc-base-commit.txt`)の google/mozc に
  `git apply --check` で当たるか、レビュー基盤と hook のテスト、Python / シェル / PowerShell の構文、`.ps1` の BOM。
  **CI が緑でもパッチがコンパイルできる保証は無い**ので、パッチを変えたら実機での確認が要る。
- 導入当初の CI はテンプレートのまま `requirements.txt` の有無で判定していて、何も検査せずに緑になっていた
  (Issue #13 で置き換え)。どの検査も「対象 0 件で成功」に落ちないようにしてある。
- agy レビューは IME 向けのドメイン `ime`(`review/domain_invariants.json`)で回す。テンプレート既定の
  `general` は Web 向け(IDOR・N+1・DB マイグレーション)で、mozc_server を落とさない・入力内容をログに出さない
  ・キー入力経路の時間上限・サンドボックスといった、この IME で実害に直結する観点を持たなかった。
