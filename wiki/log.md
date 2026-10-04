# Log

Wiki に対して何を・いつ行ったかの追記専用ログ。**新しいエントリは末尾に足す**(既存行は書き換えない)。

各エントリは `## [YYYY-MM-DD] <種別> | <一行要約>` で始める。種別は以下の 3 つ。

| 種別 | 意味 |
| --- | --- |
| `ingest` | 実装・変更の内容を Wiki に反映した |
| `query` | 調査・分析の結果を Wiki のページとして還元した |
| `lint` | 健康診断を行い、矛盾・陳腐化・孤立ページを修正した |

直近の動きは次のコマンドで追える。

```bash
grep "^## \[" wiki/log.md | tail -5
```

---

<!-- 記入例(実際のエントリを追記したらこのコメントは削除してよい)

## [2026-08-11] ingest | PR #123 エピソード進捗の一括更新に対応
- 更新: [[episode-progress]], [[db-naming]]
- 新規: [[bulk-update-transaction]]
- 備考: 一括更新はトランザクション境界が従来と異なる。[[batch-updater]] からの相互リンクを追加。

## [2026-08-12] lint | 孤立ページと陳腐化した記述の整理
- 更新: [[index]], [[deploy]]
- 削除: なし
- 発見: [[legacy-import]] は被リンク 0。実装も削除済みのためページを削除した。

-->

## [2026-10-03] ingest | エージェントルール汎用テンプレート(agy レビュー付き)を導入
- 更新: [[overview]], [[recurring-review-findings]]
- 備考: テンプレート(kant0123/ai-coding-template の bc84ddf)をコピーして Wiki の骨組みを作った。テンプレート自身の log エントリ(PR #33〜#35)は別リポジトリの履歴なので持ち込んでいない。[[recurring-review-findings]] の実例はテンプレート側の PR 番号のまま残してある。

## [2026-10-04] ingest | PR #2 候補リランキング PoC と GPU 再調査用の評価ハーネスを追加
- 新規: [[rerank-poc]]
- 更新: [[overview]], [[recurring-review-findings]]
- 備考: i3-8100 + UHD 630 での実測を元に、zenz の読み込み・GPU DLL の差し替え・op_offload・再帰層モデルの巻き戻し不可など、踏んだ落とし穴を [[rerank-poc]] に記録した。Issue #1。

## [2026-10-04] ingest | PR #7 dGPU 機(RX 9060 XT)での再測定結果を反映
- 更新: [[rerank-poc]]
- 備考: GPU 競合で汚れた回を破棄して取り直した経緯と、dGPU でも推奨構成は変わらない結論を記録。Issue #5。

## [2026-10-04] ingest | PR #12 Mozc に文脈リランカーを載せるパッチと導入手順を追加
- 新規: [[mozc-context-rerank]], [[mozc-build-install]], [[engine-base-choice]]
- 更新: [[overview]], [[rerank-poc]], [[recurring-review-findings]]
- 備考: Ohagey を評価(精度は PoC と同等、遅く x64 専用)したうえで Mozc 本家に載せた。サンドボックスで DLL が読めない・同版 MSI が上書きしない・ユーザー履歴が LM より後に効く・かな候補を LM が過大評価する、を踏んで記録。Issue #10。

## [2026-10-04] ingest | PR #19 テンプレートの Web 前提をデスクトップ IME 向けに調整(CI・agy レビューのドメイン)
- 更新: [[overview]], [[mozc-build-install]], [[mozc-context-rerank]], [[recurring-review-findings]]
- 備考: CI は requirements.txt が無いと何も検査せず緑になっていた。パッチの当たり・テスト・構文・BOM を見る形に置き換え、Mozc のビルドは CI に載せない判断を [[overview]] に記録。agy レビューの既定ドメインを Web 向けの general から ime に変えた。Issue #13。

## [2026-10-05] ingest | PR #21 使っていないテンプレート由来の CD 一式と記入例を取り除く
- 更新: [[overview]], [[recurring-review-findings]]
- 備考: `deploy/`・deploy ワークフロー・テンプレート用の `scripts/setup.*`、docs と review/README の CD 前提の記述(本番同居・`/healthz`・方式 B)を削除。branch-protection.json の必須チェック名を旧 `test` から現行の `checks` / `mozc-patch` に直した(未適用。main は保護されていない)。Issue #18。

## [2026-10-05] ingest | PR #23 main のブランチ保護の適用を記録
- 更新: [[overview]], [[recurring-review-findings]]
- 備考: 必須チェック `checks` / `mozc-patch` で main を保護した(Issue #18 の項目の「未適用」はこの時点で古くなった)。保護は GitHub 側の設定でファイルから見えないため、適用済みであることとジョブ名を変えるときの注意を overview と test.yml に残し、必須チェック名とジョブ名の一致を CI(checks ジョブ)でも検査するようにした。Issue #22。

## [2026-10-05] ingest | PR #24 Chrome で自前ビルドの Mozc が使えない原因(ESET)を導入手順に記録
- 更新: [[mozc-build-install]]
- 備考: コードの不具合ではなく、ESET の「すべてのブラウザーを保護」が署名の無い `mozc_tip64.dll` を Chrome に読み込ませていなかった。ESET に DLL の除外設定は無く、保護を無効にして解消。Issue #14。
