# オプション ワークフロー

このディレクトリのファイルは **`.github/workflows/` に置かない限り実行されない**
(GitHub Actions は `.github/workflows/` 直下のみを見る)。導入したいものだけ
`.github/workflows/` にコピーする。

| ファイル | 用途 | 前提 |
| --- | --- | --- |
| [label-hygiene.yml](label-hygiene.yml) | Issue クローズ時に `status:blocked` ラベルを自動除去 | GitHub Issues / Projects 連携を使っている |
| [wiki-check.yml](wiki-check.yml) | PR に `wiki/` の更新が含まれているかを確認(既定は警告のみ) | ナレッジ Wiki を運用している。`wiki:skip` ラベルで個別に除外 |
| [wiki-lint.yml](wiki-lint.yml) | `wiki/` の中身の整合性を機械チェック(リンク切れ・孤立ページ・`index.md` の掲載漏れ・frontmatter・`related` の片方向参照)。違反があれば落ちる | ナレッジ Wiki を運用している。`scripts/wiki-lint.js` と Node.js |

`wiki-check` と `wiki-lint` は役割が違うので併用できる。前者は「**Ingest したか**」
(PR に `wiki/` の更新が含まれるか)、後者は「**Wiki の中身が整合しているか**」を見る。

**`wiki-lint` をテストのワークフローに相乗りさせないこと。**
相乗りさせると Wiki の不整合 1 件でテスト全体が赤くなり、コードの失敗と区別できなくなる。

導入手順の詳細は [docs/development_workflow.md](../../docs/development_workflow.md) を参照。
