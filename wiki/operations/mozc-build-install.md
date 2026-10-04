---
type: operation
summary: リランカー入り Mozc のビルドと入れ直し(Windows)。UNC パス不可・同版 MSI が上書きしない・反映確認はハッシュで
updated: 2026-10-04
related: [mozc-context-rerank]
---

# リランカー入り Mozc のビルドと導入

[[mozc-context-rerank]] を Windows でビルドし、この PC に入れ直す手順。
Mozc 自体のビルド環境(bazelisk・LLVM・MSYS2・Qt)は Mozc の `docs/build_mozc_in_windows.md` に従う。

## 手順

1. google/mozc を **ローカルドライブ**(例 `C:\mozc`)に clone し、c7538e6 を checkout して Qt を用意する。
2. `02_src/mozc/setup.ps1 -MozcRoot C:\mozc` — パッチ適用、llama.cpp ヘッダ、ランタイム DLL とモデル
   (`%LOCALAPPDATA%\MozcRerank`)を揃える。再実行してよい(当て済みなら飛ばす)。
3. `src` で `bazelisk build package --config release_build`(Git Bash からなら `MSYS_NO_PATHCONV=1` を付ける)。
4. `bazel-bin/win32/installer/Mozc64.msi` を通常のフォルダにコピーし、管理者で
   `02_src/mozc/reinstall.ps1 -Msi <コピー先>` を実行する。
5. 反映の確認: `C:\Program Files (x86)\Mozc\mozc_server.exe` と
   `bazel-out/x64_windows-opt-ST-*/bin/server/mozc_server.exe.exe` の sha256 が一致すること。
   次にキーを打つと新しいサーバーが起動し、`AppData\LocalLow\Mozc\rerank.log` に `load: ready` が出る。

## 落とし穴

- **Mozc ツリーを UNC パス・ネットワークドライブに置くと Qt の configure が通らない。** G: から C: に移した。
- **`third_party/` は `.bazelignore` に入っている。** ヘッダをそこに置くと Bazel から見えないので
  `src/rewriter/llama_api/` に置いている。素の `cc_library` も使えず `mozc_cc_library` を使う。
- **bazel-bin(シンボリックリンク)上の MSI は Windows Installer が開けない。** コピーしてから使う。
- **同じバージョンの MSI は既存ファイルを上書きしない**(ログに「Existing file is of an equal version」)。
  インストールは成功扱いで古いサーバーが残る。`reinstall.ps1` はプロセスを止め、
  アンインストール → `REINSTALLMODE=amus` で入れる。反映はハッシュで確かめる。
- **Git Bash からは Bazel のターゲット名(`//...`)が MSYS にパス変換される。** `MSYS_NO_PATHCONV=1`。
- TSF は mozc_tip32/64 の両方が入り、変換は共通の mozc_server で行う。リランカーはサーバー側なので
  32 ビットアプリでも同じく効く想定(32 ビットアプリでの動作は未確認)。
