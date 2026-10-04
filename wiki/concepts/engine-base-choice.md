---
type: concept
summary: 変換エンジンの土台に Mozc 本家を選んだ理由。Ohagey(azooKey + Zenzai)の評価結果と採用しなかった点
updated: 2026-10-04
related: [mozc-context-rerank, rerank-poc, overview]
---

# 変換エンジンの土台の選択

リランカーを載せる土台として、**Mozc 本家(TSF)を選んだ**。比較対象は Ohagey
(github.com/C0uki/Ohagey。azooKey の KanaKanjiConverter + Zenzai を Windows の TSF に載せた IME)。
Ohagey が十分なら imev の開発をやめる、という前提で評価した。

## Ohagey の評価(2026-10-04, i5-12600K, CPU)

- **変換精度は imev の PoC と同等。** imev の評価 11 問で文脈あり 10/11・文脈なし 4/11、外したのは
  同じ 1 問(帰社)。同じ zenz-v3.1 系を使うので当然の結果で、精度面での上積みは無い。
- **遅い。** 1 回の変換が文脈あり約 234ms・なし約 161ms(候補生成まで LM で行うため)。
  Mozc + リランカーは採点だけなので 13〜50ms。
- **x64 専用。** 32 ビットアプリ(サクラエディタ等)では TSF が載らず半角入力しかできない。
- **導入物が未成熟。** インストーラが SwiftPM のリソースバンドルを含めておらず、エンジンが起動時に
  落ちた(メモ帳でクラッシュ)。手で .iss に追加して解消。設定アプリは VS のワークロードが要りビルドしていない。
  上流への報告はしていない。

## Mozc を選んだ理由

- ユーザーの体感が良い(辞書・学習・操作系が成熟している)。精度の不足分だけを LM で補う設計にできる。
- 32/64 ビット両方の TSF がある。
- Rewriter の口があり、`ConversionRequest` から TSF が渡すカーソル左の文(改行で切れる)を取れるので、
  本体に手を入れる量が少ない(パッチは Rewriter 2 つと登録 1 行)。

却下: Ohagey をベースに改修する案。精度が同等で速度・互換性の問題を抱え、Swift のビルド環境も重い。
実装は [[mozc-context-rerank]]。
