---
type: operation
summary: リランカー入り Mozc のビルドと入れ直し(Windows)。UNC パス不可・同版 MSI が上書きしない・反映確認はハッシュで・ESET が Chrome で止める(自己署名でも回避不可)
updated: 2026-10-05
related: [mozc-context-rerank, overview]
---

# リランカー入り Mozc のビルドと導入

[[mozc-context-rerank]] を Windows でビルドし、この PC に入れ直す手順。
Mozc 自体のビルド環境(bazelisk・LLVM・MSYS2・Qt)は Mozc の `docs/build_mozc_in_windows.md` に従う。

## 手順

1. google/mozc を **ローカルドライブ**(例 `C:\mozc`)に clone し、基準コミット(`02_src/mozc/mozc-base-commit.txt`、
   現在 c7538e6)を checkout して Qt を用意する。
2. `02_src/mozc/setup.ps1 -MozcRoot C:\mozc` — パッチ適用、llama.cpp ヘッダ、ランタイム DLL とモデル
   (`%LOCALAPPDATA%\MozcRerank`)を揃える。再実行してよい(当て済みなら飛ばす)。
3. `src` で `bazelisk build package --config release_build`(Git Bash からなら `MSYS_NO_PATHCONV=1` を付ける)。
4. `bazel-bin/win32/installer/Mozc64.msi` を通常のフォルダにコピーし、管理者で
   `02_src/mozc/reinstall.ps1 -Msi <コピー先>` を実行する。
5. 反映の確認: `C:\Program Files (x86)\Mozc\mozc_server.exe` と
   `bazel-out/x64_windows-opt-ST-*/bin/server/mozc_server.exe.exe` の sha256 が一致すること。
   次にキーを打つと新しいサーバーが起動し、`AppData\LocalLow\Mozc\rerank.log` に `load: ready` が出る。

## 基準コミットを上げるとき

`02_src/mozc/mozc-base-commit.txt` の SHA だけを書き換える。CI の `mozc-patch` ジョブがこのファイルを読み、
パッチがそのコミットに当たるかを見る。当たっても**コンパイルと挙動は CI では分からない**ので、
上の手順 1〜5 と実際の変換確認までやり直す。

## 落とし穴

- **Mozc ツリーを UNC パス・ネットワークドライブに置くと Qt の configure が通らない。** G: から C: に移した。
- **`third_party/` は `.bazelignore` に入っている。** ヘッダをそこに置くと Bazel から見えないので
  `src/rewriter/llama_api/` に置いている。素の `cc_library` も使えず `mozc_cc_library` を使う。
- **bazel-bin(シンボリックリンク)上の MSI は Windows Installer が開けない。** コピーしてから使う。
- **同じバージョンの MSI は既存ファイルを上書きしない**(ログに「Existing file is of an equal version」)。
  インストールは成功扱いで古いサーバーが残る。`reinstall.ps1` はプロセスを止め、
  アンインストール → `REINSTALLMODE=amus` で入れる。反映はハッシュで確かめる。
- **管理者で起動した PowerShell からはネットワークドライブ(割り当てた G: など)が見えない。** `reinstall.ps1` を
  ネットワークドライブ上から管理者実行すると、何も出力せずに失敗する。ローカルドライブにコピーして実行する。
- **Git Bash からは Bazel のターゲット名(`//...`)が MSYS にパス変換される。** `MSYS_NO_PATHCONV=1`。
- **ESET の「すべてのブラウザーを保護」が有効だと、Chrome では自前ビルドの Mozc が使えない。** 半角/全角に反応せず、
  Microsoft IME に切り替わることもある。他のアプリ(サクラエディタ等)では動く。ESET の保護されたブラウザは
  信頼できない DLL の読み込みを止めると見られ、自前ビルドの `mozc_tip64.dll` はこれに当たる(署名が無いことだけが
  理由ではない。下の実験)。DLL 単位の除外設定は ESET に無く、「詳細設定 → 保護 → ブラウザーの保護 → バンキングとブラウジング保護」で
  「すべてのブラウザーを保護」を無効にし、Chrome を起動し直して解消した。設定直後の 1 回目の再起動では直らず、
  その後の再起動で直った(差の原因は未確認)。同じ報告: google/mozc discussion #805。Issue #14。
  - 切り分けの記録: `chrome://conflicts` では Mozc TIP Module が「Process types: None」(IME として列挙されているが
    どのプロセスにも読み込まれていない)。Chrome は自プロセスのモジュール一覧・コマンドラインを外から読ませない
    (`tasklist /m` は N/A)ので、DLL が入ったかは外からは見えない。`--user-data-dir=<一時フォルダ>` で別インスタンスの
    Chrome を起動して試すと、普段のプロフィールを壊さずに切り分けられる。Chrome 自身の外部 DLL ブロックは
    登録済み IME を対象外にしており、原因ではなかった。
  - **自己署名では回避できない(Issue #25 の実験)。** 「すべてのブラウザーを保護」を有効にしたまま、自己署名の
    コード署名証明書で `mozc_tip64.dll` / `mozc_tip32.dll` に署名して差し替え、Chrome(再起動済み)で試した。
    (1) 署名のみ(Windows 上は `UnknownError` = ルート未信頼)→ NG。(2) 証明書を `LocalMachine\Root` と
    `TrustedPublisher` に入れ、Windows 上の署名状態を `Valid` にした → やはり NG。ESET は Windows の信頼ストアを
    見ていない(ESET 自身の DLL も自己署名で、ekrn.exe 側の信頼に頼っているという forum の指摘とも合う)。
    実験後に証明書の信頼を外し、元の DLL に戻した。
  - **未検証の手段:** 購入した正規のコード署名証明書(ESET が発行元の信頼度を見るなら通りうるが、費用が掛かり、
    通るかは試していない)、ESET へ DLL を提出して LiveGrid で許可してもらう(forum に別件の成功例。ただし
    ビルドのたびにハッシュが変わるので毎回の依頼になり、現実的でない)。どちらも個人利用の自前ビルドには見合わない
    ため、当面は「Chrome を使うときは保護を無効にする」を運用とする。
  - 差し替えの実験で、読み込み中の DLL は上書きできないが名前の変更はできるので、`Move-Item` で退避してから
    コピーすればプロセスを止めずに入れ替えられる。`Program Files (x86)\Mozc` に `*.dll.old-*` が残るので消してよい。
- TSF は mozc_tip32/64 の両方が入り、変換は共通の mozc_server で行う。リランカーはサーバー側なので
  32 ビットアプリでも同じく効く想定(32 ビットアプリでの動作は未確認)。
