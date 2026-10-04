---
type: component
summary: Mozc に載せた文脈リランカー(ContextRerankRewriter + LlmScorer)。02_src/mozc のパッチ。サンドボックス・学習との順序・かな候補の扱いの落とし穴
updated: 2026-10-04
related: [rerank-poc, mozc-build-install, engine-base-choice, overview]
---

# Mozc 文脈リランカー

[[rerank-poc]] の採点方式を C++ に移し、Mozc 本家の Rewriter として組み込んだもの。
変換のたびに、カーソル左の文を文脈にして上位候補を zenz-v3.1-small で採点し並べ替える。
リポジトリには google/mozc c7538e6 へのパッチとして置いている(Mozc 本体は取り込まない)。

## 責務

- する: 変換(Space)時の各文節の上位 5 候補の並べ替え。
- しない: 予測・サジェスト(`capability()` は CONVERSION のみ)、候補の追加・削除、
  確定時の KV 更新(設計書 §3.3 の `Finish()` フックは未実装。毎回最長共通接頭辞で同期する)。

## 入口となるファイル

すべて `02_src/mozc/context-rerank.patch` の中(パッチ適用後の Mozc ツリーでのパス)。

| パス | 役割 |
| --- | --- |
| `src/rewriter/context_rerank_rewriter.cc ContextRerankRewriter::Rewrite()` | 文脈の決定、対象候補の選別、LM スコアと Mozc の順位の合成 |
| `src/rewriter/llm_scorer.cc LlmScorer::Impl::Load()` | llama.dll の動的ロード、モデル読み込み(別スレッド)、ログ |
| `src/rewriter/llm_scorer.cc LlmScorer::Impl::Rank()` | zenz プロンプトの組み立て、`seq_cp` 分岐で候補を 1 回の decode で採点 |
| `src/rewriter/rewriter.cc Rewriter::Rewriter()` | 登録位置。ユーザー履歴系 Rewriter の直前 |
| `02_src/mozc/setup.ps1` | パッチ適用・ヘッダ・ランタイム DLL・モデルの取得 |

## 依存関係

- 依存している: azooKey/llama.cpp b4846 の DLL とヘッダ、Hugging Face の zenz-v3.1-small(Q5_K_M)
- 依存されている: なし
- 導入手順は [[mozc-build-install]]、Mozc を土台に選んだ理由は [[engine-base-choice]]

## 落とし穴

すべて実際に踏んだもの。

- **mozc_server は低整合性のサンドボックスで動く。** ユーザープロファイル配下(`%LOCALAPPDATA%` など)の
  DLL もモデルも読めず、`LoadLibrary` はエラー 126 になる。ランタイムは実行ファイルと同じ
  `Program Files (x86)\Mozc\rerank` に置く。ログも `%LOCALAPPDATA%` には書けないので
  `%USERPROFILE%\AppData\LocalLow\Mozc\rerank.log` に出す(文字列は書かず、バイト数と所要時間だけ)。
- **llama.dll は ggml-rpc.dll にも依存する。** 欠けても 126 で、どの DLL が無いのかは出ない。
- **ユーザー履歴が LM より後に効く。** 登録位置を履歴系 Rewriter の前にしているので、
  一度確定した候補(テストで繰り返し確定した「記者」など)は LM が何を言っても先頭に戻る。
  ユーザーの明示的な選択を優先するための意図した順序。動作確認は未学習の語か、学習履歴を消してから行う。
- **かなだけの候補は並べ替えない。** プロンプトに読みをカタカナで入れるため、LM は読みをそのまま写す
  「ゲキダン」に高い確率を付ける。対象に入れていたときは単独の「げきだん」が「ゲキダン」になった。
- **文脈が空なら採点しない。** 文脈なしの LM は Mozc 自身の言語モデルと情報が重なるだけで、
  上の誤りを起こす余地だけが残る。
- **合成式は `-500 × logprob + 300 × 元の順位`。** 500 は Mozc のコスト単位(-500 × ln p)。
  300 は Mozc の順位を保つための事前。環境変数 `MOZC_RERANK_PRIOR` で変えられるが、サーバーは
  サンドボックス下で起動されるので、渡すにはユーザー環境変数にしてサーバーを再起動する。
- **1 回の採点は 250ms で打ち切る**(`llama_set_abort_callback`)。失敗・打ち切り時は Mozc の順位のまま。

## 経緯

- 2026-10-04: Ohagey の評価を経て Mozc 本家に載せる方針にし([[engine-base-choice]])、この PC で
  ビルド・インストールした。採点は文脈 56〜60 バイトで 50ms 前後、短い文脈で 13〜35ms(i5-12600K, CPU)。
  「劇団の千秋楽の」+こうえん → 公演、「著名な研究者の」+こうえん → 講演、「街の」→ 公園を確認。
  当初はかな候補も対象にしていて「ゲキダン」問題が出たため除外した。Issue #10。
