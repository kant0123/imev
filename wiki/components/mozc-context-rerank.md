---
type: component
summary: Mozc に載せた文脈リランカー(ContextRerankRewriter + LlmScorer)。02_src/mozc のパッチ。サンドボックス・学習との順序・かな候補の扱いの落とし穴
updated: 2026-10-05
related: [rerank-poc, mozc-build-install, engine-base-choice, overview]
---

# Mozc 文脈リランカー

[[rerank-poc]] の採点方式を C++ に移し、Mozc 本家の Rewriter として組み込んだもの。
変換のたびに、カーソル左の文を文脈にして上位候補を zenz-v3.1-small で採点し並べ替える。
リポジトリには google/mozc の基準コミット(`02_src/mozc/mozc-base-commit.txt`、現在 c7538e6)へのパッチとして置いている
(Mozc 本体は取り込まない)。パッチが当たるかは CI が見るが、ビルドはしない([[overview]] の「運用」)。

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
  `%USERPROFILE%\AppData\LocalLow\Mozc\rerank.log` に出す(入力の文字列は書かず、バイト数・所要時間・スコアの数値だけ)。
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
- **かな表記が正解の候補は昇格できない。** 上の「ゲキダン」対策で、表層がひらがな・カタカナだけの候補は
  採点の対象から外している。補助動詞・語尾など**ひらがなが正解**の読みでは、漢字の誤候補が先頭のまま動かない
  (読み「したい」の「死体」。Mozc の候補には「したい」が 2 番目に居るのに対象にならない)。Issue #31。
- **ライブ変換では、キー入力中の文脈に組み立て中の文字列が混ざる。** 実機の Windows Mozc はキーごとに変換する。
  同じ読みの連続した呼び出しで `ctx` がキー入力中は伸び、最後の Space の明示変換で縮む(例: 22B → 9B)。
  キー入力中は周辺テキストに組み立て中の変換済み文字列が含まれ、LM は候補自身を文脈として見ている。
  明示変換の文脈は正しい。対策は未実装(Issue #32、#8)。
- **周辺テキストは Claude デスクトップ版の入力欄からも届く。** `mozc_server` を再起動した直後(確定履歴が空)の
  最初の変換でも `ctx` が非 0 だった。周辺テキストが無いアプリでは履歴文節にフォールバックし、それも空なら採点しない
  (`converter_main` で確認。同じ文を文節ごとに確定すれば履歴が文脈になる)。
- **実機 C++ の対数確率は PoC より鈍い(原因未特定)。** 同じ入力(文脈「劇団の」・読み「こうえんが」)で、
  PoC は正解の「公演が」に -0.3、実機 C++ は -7.1。他の候補も約 -7 ずれ、順位の並びも違う。
  `Rank()` と PoC の `_sync()` のプロンプトは同じなので、llama.cpp の版差(azooKey b4846 と公式 b11352)、
  トークナイズ、KV の扱いのどれかと見ている。鈍いぶん合成式の事前(元の順位 × 300)に負けやすい。Issue #33。
- **1 回の採点は 250ms で打ち切る**(`llama_set_abort_callback`)。失敗・打ち切り時は Mozc の順位のまま。

## 診断ログ

`rerank.log` に、変換 1 回ごとに次の行が出る(数値だけ。入力の文字列は出さない)。
Mozc の候補が期待と違うとき、LM と事前のどちらが効いたかを切り分けるために使う。

- `rewrite: ctx src=surrounding|history <n>B, segs <m>` — 文脈の出どころ(カーソル左の周辺テキストか、確定履歴か)とバイト数
- `seg <i> skip: fixed | one candidate | key not hiragana | kana-only cands` — 採点しなかった文節とその理由
- `seg <i> rerank: slots … lp … cost … order …` — 採点した候補の Mozc 順位(`slots`)、LM の対数確率(`lp`)、
  合成コスト(低いほど上位。`cost`)、並べ替え後の並び(新しい位置 → `slots` の添字。`order`)

`order` が `0,1,2…` なら並べ替えは起きていない。`lp` では別の候補が上なのに `order` が動かないときは事前が効いている。
ユーザー履歴系 Rewriter はこのリランカーより後に動くので、`order` が正しいのに画面の先頭が違うときは履歴が上書きしている。

## 経緯

- 2026-10-04: Ohagey の評価を経て Mozc 本家に載せる方針にし([[engine-base-choice]])、この PC で
  ビルド・インストールした。採点は文脈 56〜60 バイトで 50ms 前後、短い文脈で 13〜35ms(i5-12600K, CPU)。
  「劇団の千秋楽の」+こうえん → 公演、「著名な研究者の」+こうえん → 講演、「街の」→ 公園を確認。
  当初はかな候補も対象にしていて「ゲキダン」問題が出たため除外した。Issue #10。
- 2026-10-05: 「文節ごとにこまめに Space しないと賢くならない」への調査(Issue #30)。`converter_main` で、
  まとめ変換と文節ごとの変換で Mozc の候補・順位・文節区切りが一致することを確認した。診断ログを足して実機で見ると、
  原因は文脈が空だったことではなく、かな候補の除外・ライブ変換中の文脈の混入・実機 C++ の採点の鈍さだった(上の「落とし穴」)。修正は Issue #31・#32・#33 に切り出した。
