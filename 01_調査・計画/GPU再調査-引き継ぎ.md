# GPU 機での再調査 — 引き継ぎ

- 作成: 2026-10-04（前回の調査環境: Core i3-8100 4C/4T、内蔵 GPU UHD 630、dGPU なし）
- 実施済み: 2026-10-04 に RX 9060 XT 機で手順 2・3・5 を実施(手順 4 は NVIDIA が無く未実施)。結果は設計書 §2.4
- 設計の全体像: [mozc-llm-rerank-設計.md](mozc-llm-rerank-設計.md)。この文書は「GPU 機で何を測り、何を決めるか」だけを扱う

## 0. 30 秒で分かる現状

Mozc の変換候補を、直前の確定文を文脈にした小さな言語モデルで並べ替える構想です。速度予算は **変換キー 1 回あたり 10〜30ms**。i3-8100 の CPU で測った結果は次のとおりでした（評価セットは自作の同音異義語 11 問）。

| モデル | 方式 | 正解（文脈あり / なし） | 判定 1 回 | 専有メモリ増 |
| --- | --- | --- | --- | --- |
| zenz-v3.1-small（95M, 74MB） | 尤度 | **10/11** / 4/11 | **8.0ms** | +53MB |
| zenz-v3.1-xsmall（26M, 21MB） | 尤度 | 9/11 / 4/11 | **2.8ms** | 未計測（small より小） |
| Qwen3-0.6B Q4_0 | 尤度 | 9/11 / 4/11 | 46ms（うち llama.cpp 23.5ms） | +439MB |
| Qwen3-0.6B Q4_0 | 選択式（SemIf 方式） | 7/11 / 4/11 | 298ms | 同上 |
| gemma-3-1b Q4_0 | 尤度 | 10/11 / 4/11 | 113ms | +1020MB |
| 内蔵 GPU（UHD 630）全般 | — | CPU と同じ | **すべて CPU より遅い**（zenz-small 86ms、選択式 933ms） | — |

この表の生データは `02_src/poc/results/DESKTOP-80AKMUB-vulkan-20261004-0039.md`（前回 PC で `setup_eval.ps1` と同じ手順を回した結果）。GPU 機の結果はこれと並べて比べます。

方式は 2 つあります。

- **尤度方式（`plain` / `zenz`）**: 「文脈の続きとして各候補がどれだけ自然か」の確率を、候補のトークンだけ 1 バッチで流して比べます。指示に従う力は要りません。
- **選択式（`choice`）**: SemIf（旧 OpenJev）や Jev の方式です。候補を A/B/C… としてプロンプトに並べ、記号トークンの確率だけを読みます。候補がプロンプトに入るので、変換のたびに約 50〜80 トークンを流す必要があり、CPU では重くなります。

**今回の問い**は 3 つです。

1. GPU なら、大きいモデル（MiniCPM5-2B、Qwen3.5-4B）や選択式が 30ms に収まるか。
2. 収まるなら、精度は zenz-small（CPU で 9ms）を上回るか。
3. 選択式は、SemIf 本家（PyTorch/BF16）と llama.cpp の量子化版で結果が一致するか。

## 1. やること（この順で）

### 手順 1. 準備（10 分）

- Windows / Python 3.12 / git。NVIDIA なら新しめのドライバ（CUDA 12.4 ランタイムは zip に同梱されるので CUDA Toolkit は不要）。
- 空き容量 約 10GB（モデル 約 6GB + llama.cpp + venv）。

```bash
git clone https://github.com/kant0123/imev.git
```

手順 2 以降はクローンしたフォルダで実行します。

### 手順 2. 一括評価を回す（30〜60 分。大半はダウンロード）

NVIDIA の場合:

```bash
powershell -ExecutionPolicy Bypass -File 02_src/poc/setup_eval.ps1 -Backend cuda
```

AMD / Intel の GPU、または CUDA が動かない場合:

```bash
powershell -ExecutionPolicy Bypass -File 02_src/poc/setup_eval.ps1 -Backend vulkan
```

このスクリプトは次を自動で行います。作業領域は `%USERPROFILE%\imev-eval` です。

1. venv を作り、`requirements-eval.txt` を導入する
2. llama.cpp 公式ビルド `b11352` の GPU 版と CPU 版を GitHub Releases から取得する
3. モデル 6 種を Hugging Face から取得する（§3）
4. `llama-bench` で、モデルごとに CPU と GPU を比べる（1/4/8/64 トークンのバッチ）
5. PoC を「全モデル × 方式 × CPU（ngl=0）/ GPU（ngl=99）」で実行する
6. 結果を `02_src/poc/results/<ホスト名>-<backend>-<日時>.md`（表）と同名の `.jsonl`（生データ）、組み合わせごとの `.log` に書き出す

途中で止めたい・一部だけ回したい場合は、モデルを絞って実行します。

```bash
powershell -ExecutionPolicy Bypass -File 02_src/poc/setup_eval.ps1 -Backend cuda -Models zenz-small,semif-qwen3.5-4b-q4_k_m -Repeat 3
```

### 手順 3. 結果を確かめる（10 分）

`results/*.md` を開いて、次の 3 点を見ます。

- **「デバイス」節に GPU 名が出ているか。** 出ていなければ GPU が使われていません（§4 の 2 番目）。
- **`ngl=99` の行の正解数が `ngl=0` と同じか。** 量子化カーネルの差で 1 問程度ぶれるのはあり得ますが、大きく違えば結果を疑ってください。
- 末尾の「失敗した組み合わせ」が空か。空でなければ同名の `.log` を見ます。

### 手順 4. SemIf 本家での評価（任意、1〜2 時間、NVIDIA 必須）

llama.cpp の選択式は SemIf のプロンプトを日本語で模したもので、本家と同一ではありません。本家のスコアラー（PyTorch/BF16）で同じ問題を解かせて比較します。

```bash
git clone https://github.com/TheoLeeCJ/SemIf-OpenJev.git
```

クローンしたフォルダで、同リポジトリの `docs/REPRODUCE.md` に従って venv と CUDA 版 PyTorch を入れ、`pytest -q` が通ることを確認します。そのうえで、問題を SemIf 形式に変換します（imev のフォルダで実行）。

```bash
python 02_src/poc/semif_bridge.py export 02_src/poc/cases.jsonl semif-input.jsonl
```

SemIf 側の venv で採点させます（SemIf のフォルダで実行。`semif-input.jsonl` のパスは適宜変えてください）。

```bash
semif-score --mode serial --model Qwen/Qwen3.5-4B --revision 851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a --input semif-input.jsonl --output semif-output-4b.jsonl
```

`--model Qwen/Qwen3-0.6B --revision c1899de289a04d12100db370d81485cdf75e47ca` と `--model openbmb/MiniCPM5-2B --revision 12a3808a956f869c767195e9266b59c4d21d92e2` でも同様に実行します。最後に正解数と 1 判定の時間を出します（imev のフォルダで実行）。

```bash
python 02_src/poc/semif_bridge.py score 02_src/poc/cases.jsonl semif-output-4b.jsonl
```

- `semif-score` は既存の出力ファイルを上書きしません。出力名は毎回変えてください。
- 時間（`total_seconds`）は Python 込みです。IME 予算との比較には手順 2 の llama.cpp の数字を使い、こちらは精度の基準として扱います。
- SemIf 本家の汎用ベンチ（shape777 など）は、IME の判断には不要です。

### 手順 5. 記録する

1. `results/` の `.md` と `.jsonl` をコミットする（`.log` は失敗の調査用。必要なものだけ）。
2. 設計書の §2.1（モデル表）、§2.3（CPU と GPU）、§4（PoC 結果）に GPU 機の数字を追記する。手順 4 をやった場合は SemIf 本家の結果も載せる。
3. §2 の判断基準に照らした結論を、設計書 §1 のサマリーに 1〜2 行で反映する。

## 2. 判断基準

| 結果 | 結論 |
| --- | --- |
| GPU でも zenz-small（CPU）より遅い、または精度が上回らない | 構成は変えない。GPU は使わない |
| 尤度方式の 2B / 4B が GPU で rank 中央値 30ms 以下、かつ正解が zenz を上回る | 「dGPU 搭載機だけの上位版」として設計書に追加する。常駐 VRAM と、他アプリ（ゲーム等）と GPU を取り合うときの遅延も確認する |
| 選択式が GPU で 30ms 以下、かつ尤度方式より明確に正確 | 選択式を変換キー押下時のみの再判定に使う案を検討する（文脈は確定時に先読み） |
| SemIf 本家と llama.cpp の選択式で正解が大きく違う | 量子化かプロンプトの差。PoC のプロンプト（`_chat_prompt`）を SemIf の英語テンプレートに寄せて再測定する |

注意: 11 問は精度の優劣を言える規模ではありません。GPU で有望な組み合わせが出たら、先に `cases.jsonl` を数百問に増やしてから結論を出してください。形式は 1 行 1 問の JSON（`reading` / `candidates` / `context` / `answer`）です。

## 3. 評価対象モデル（`run_eval.py` の `MODELS`）

| キー | 中身 | 方式 | 備考 |
| --- | --- | --- | --- |
| `zenz-small` | zenz-v3.1-small Q5_K_M（74MB） | zenz | 現在の推奨。CC-BY-SA 4.0 |
| `zenz-xsmall` | zenz-v3.1-xsmall Q5_K_M（21MB） | zenz | 低スペック機向けの予備。CPU で 9/11・2.8ms |
| `qwen3-0.6b-q4_0` | Qwen3-0.6B Q4_0（442MiB） | plain / choice | i3-8100 で評価済み |
| `semif-qwen3-0.6b-q8_0` | Qwen3-0.6B Q8_0（639MB） | plain / choice | SemIf / openjev.com がスマホ向けに使う版 |
| `semif-minicpm5-2b-q4_k_m` | MiniCPM5-2B Q4_K_M（1.56GB） | plain / choice | SemIf のデスクトップ向け。未評価 |
| `semif-qwen3.5-4b-q4_k_m` | Qwen3.5-4B Q4_K_M（3.01GB） | plain / choice | SemIf の主力。未評価。**再帰層あり**（§4） |

`semif-*` の revision は SemIf の `manifests/models.json` に固定されたものと同じです。モデルを足すときは `MODELS` に 1 行追加します。

## 4. ハマりどころ（全部、実際に踏んだもの）

- **zenz は本家 llama.cpp でそのままは読めない。** GGUF の pre-tokenizer 名 `gpt2-small-japanese-char` が未登録のためです。PoC は `tokenizer.ggml.pre=default` の上書きで、`llama-bench` はこのキーを消したコピー（`*-nopre.gguf`、自動生成）で回避しています。
- **GPU を使うには公式ビルドの DLL 差し替えが必要。** pip の llama-cpp-python は CPU 版なので、`LLAMA_CPP_LIB_PATH` で公式リリースの DLL を読ませています（`run_eval.py` が自動設定）。さらに公式ビルドは GPU バックエンドが別 DLL で、`ggml_backend_load_all_from_path` を呼ばないと CPU しか使われません（PoC の `load_gpu_backends`）。
- **llama-cpp-python 0.3.36 と llama.cpp b11352 の組で ABI 互換を確認済み。** どちらかを上げると構造体がずれて落ちる可能性があります。上げるときは、まず CPU で正解数が変わらないことを確かめてください。
- **CUDA 経路はこの調査では未実行です**（前回の PC に NVIDIA が無い）。同じ仕組みの Vulkan 経路は動作確認済みです。CUDA で DLL が読めない場合は、zip に `cudart` の DLL が同じフォルダへ展開されているか確認し、だめなら `-Backend vulkan` で代替してください。
- **Qwen3.5 は再帰層を含むハイブリッド構造で、KV を途中位置まで巻き戻せない**（`llama_memory_seq_rm` が失敗する）。PoC は全再計算に切り替えて `[warn]` を出します。尤度方式は影響を受けにくい一方、選択式は毎回全部を流し直すので遅く出ます。実運用ではスナップショット（`llama_state_seq_get_data` / `set_data`）で代替する必要があり、その実装コストも判断材料です。
- **GPU 版 DLL では `ngl=0` でも GPU が使われる。** llama.cpp は GPU バックエンドがあると、32 トークン以上のバッチを重みが CPU 側にあっても自動で GPU に回します（op_offload）。前回の PC ではこれで CPU の選択式が 335ms → 1080ms と汚れました。`run_eval.py` は `ngl=0` の計測に CPU 専用ビルドを使うようにしてあります。手で比べるときも同じにしてください。
- **Vulkan は初回にシェーダのコンパイルが入る。** 1 回目だけ極端に遅いことがあります。PoC は 2 回目以降の中央値を記録しています。
- **語彙の大きいモデルはメモリを食う。** logits バッファが「n_batch × 語彙数 × 4 バイト」確保されます。PoC は n_batch=64 にしています（Qwen3 で 512 にすると +300MB）。
- **日本語 Windows の pip は requirements を cp932 で読む。** `requirements-eval.txt` に日本語を書くと導入が失敗します。

## 5. ファイル一覧

| ファイル | 役割 |
| --- | --- |
| `02_src/poc/setup_eval.ps1` | 入口。venv 作成と依存導入のあと `run_eval.py` を呼ぶ |
| `02_src/poc/run_eval.py` | 取得・ベンチ・PoC 総当たり・結果表の作成 |
| `02_src/poc/context_rerank_poc.py` | PoC 本体。`--style zenz/plain/choice`、`--ngl`、`--cases`、`--out` |
| `02_src/poc/cases.jsonl` | 評価セット（11 問） |
| `02_src/poc/semif_bridge.py` | cases ⇄ SemIf の入出力変換と採点 |
| `02_src/poc/requirements-eval.txt` | 依存（llama-cpp-python は 0.3.36 固定） |
| `02_src/poc/results/` | 測定結果。前回 PC（i3-8100 + UHD 630）の結果も置いてある |

## 6. 未決事項（GPU の結果と独立に決める必要があるもの）

- zenz の重みのライセンス（CC-BY-SA 4.0）。Mozc に同梱して配布するか、別ダウンロードにするか。
