# Mozc × 超軽量 LM による文脈考慮リランキング — 調査・設計

- 調査日: 2026-10-03
- Mozc の参照コミット: `google/mozc@c7538e6`（2026-10-02）。以下の `path:行` はこのコミット基準
- 実測環境: Intel Core i3-8100（4C/4T, AVX2, 2017 年）/ Windows 11 / llama-cpp-python 0.3.36（CPU ビルド）
- PoC: [`02_src/poc/context_rerank_poc.py`](../02_src/poc/context_rerank_poc.py)（実行済み。結果は §4）

## 1. エグゼクティブサマリー

**推奨構成: zenz-v3.1-small（95M, GGUF 74MB）+ llama.cpp（libllama を静的リンク）+ Mozc の Rewriter として組み込み。**

| 項目 | 結論 | 根拠 |
| --- | --- | --- |
| モデル | **zenz-v3.1-small**（GPT-2 系 95.1M、かな漢字変換専用、`文脈→読み→出力` 形式） | i3-8100 で rank 中央値 **8.9ms**（最大 12.4ms）、常駐 **+96MB**。同音異義語 11 問で文脈あり 10/11・文脈なし 4/11（§4） |
| ランタイム | **llama.cpp** | C API で `seq_cp`/`seq_rm` による KV の分岐・ロールバックが 1 行。LoRA の動的ロードも同 API |
| 判定方式 | 候補の全トークンを **1 回の `llama_decode` で teacher-forcing** し、log P を合算 | 候補は複数トークンなので「次トークン 1 個」では足りない。1 トークン候補だけなら forward ゼロ（Jev 型の logits 参照のみ） |
| 再ランク位置 | `Rewriter::Rewriter()` に **`ContextRerankRewriter`** を追加（`UserSegmentHistoryRewriter` の直前） | Space 変換・サジェスト両方を通る。ユーザー学習が LM の結果を上書きできる順序 |
| 確定フック | 同 Rewriter の **`Finish()`**（`Converter::FinishConversion` から呼ばれる） | Enter 確定・サジェスト確定・ひらがな確定のすべてが通る唯一の合流点 |
| パーソナライズ | **案A を必須、案B は静的プロファイルのみ、案C は後回し** | §5 |

**dGPU 機での再評価（2026-10-04, RX 9060 XT + i5-12600K, §2.4）:** 推奨構成は変えません。zenz-small は CPU でも 6.3ms で、GPU（1.9ms）は要りません。尤度方式の Qwen3.5-4B は GPU で rank 中央値 29.1ms・11/11 と zenz（10/11）を上回りましたが、30ms ぎりぎり・差は 1 問・11 問のみのため、「dGPU 搭載機だけの上位版」候補として保留し、評価セット拡充後に再判断します。選択式は尤度方式より明確には正確でなく、採用しません。

依頼内容からの修正点が 3 つあります。

1. **汎用 LM は 0.6B が上限で、それも予算の縁です。** Qwen3-0.6B（Q4_0, 442MiB）は同じ PoC で llama.cpp の計算部分が 23.5ms（判定全体は Python 込みで 48ms）、正解 9/11 でした。C++ なら 25〜30ms 程度と見込まれ、30ms にぎりぎり収まります。ただ zenz（8.7ms・10/11）より遅く精度も上回りません。gemma-3-1b（720MB）は 113ms・常駐 +1.1GB で対象外です。
   内蔵 GPU（UHD 630, Vulkan）は**すべての条件で CPU より遅く**、使いません（§2.3）。
2. **Jev / OpenJev / clef-flash はモデル候補になりません。** OpenJev は Qwen3.5-4B（重み約 8GB、VRAM 24GB 以上）、clef-flash は Qwen3.5-9B ベースの 9B マルチモーダルで、どちらも常駐 300〜800MB に収まりません。採用するのは「生成せず logits を読む」という方式だけです。SmolLM2 は英語専用で対象外です。
3. **zenz は本家 llama.cpp でそのまま読めません。** GGUF の pre-tokenizer 名 `gpt2-small-japanese-char` が未登録でロードに失敗します。`tokenizer.ggml.pre=default` をメタデータ上書きすれば読め、文字単位の分割も正しいことを確認済みです（PoC に実装）。

判断が必要な点: zenz の重みは **CC-BY-SA 4.0** です。Mozc（BSD-3）に同梱して配布する場合は表示義務と、重みを改変（LoRA 統合など）して配布する際の継承義務が生じます。別ダウンロードにするか同梱するかは配布形態に合わせて決めてください。

## 2. モデル＆ランタイム比較

### 2.1 モデル

| モデル | パラメータ / GGUF | 常駐メモリ | レイテンシ（rank 1 回） | 日本語・同音異義語 | 判定 |
| --- | --- | --- | --- | --- | --- |
| **zenz-v3.1-small** | 95.1M / Q5_K_M 74MB | **+96MB（実測）** | **8.9ms（実測, 4 スレッド）** / 16ms（2 スレッド） | 変換専用に学習。読みで条件付けできる。11 問中 10 | **採用** |
| zenz-v3.1-xsmall | 25.6M / Q5_K_M 21MB | 未実測（small より小） | **2.8ms（実測, 4 スレッド）** | Android オフライン変換向けの縮小版。11 問中 9 | 低スペック機向けの予備 |
| Qwen3-0.6B | 0.75B（埋め込み込み）/ Q4_0 442MiB, Q4_K_M 456MiB | **専有 +410〜440MB（実測）**。重みのメモリマップを含む作業セットは +700MB | **計算 23.5ms / 全体 48ms（実測, Python 込み）**。C++ 推定 25〜30ms | 119 言語対応の汎用 LM。読みの条件付けは不可（表層の尤度のみ）。11 問中 9（Q4_0 と Q4_K_M で同じ） | 予算の縁。zenz を上回る点が無く、次点 |
| sarashina2.2-0.5b | 0.5B / GGUF サイズ未確認 | 同上 | 同上 | 日本語特化（MIT）。公称で Qwen2.5-0.5B を上回る | 同上。0.5B 級を試すならこちらが第一候補 |
| gemma-3-1b-it QAT | 1B / Q4_0 720MB | **+1137MB（実測）** | **113ms（実測）** | 11 問中 10（zenz と同数） | 不採用（速度・メモリとも超過） |
| MiniCPM5-2B | 2.5B / Q4_K_M 1.45GiB | 約 +1.5GB（GGUF サイズ） | CPU 105ms / **dGPU 21.6ms**（§2.4） | 尤度 9/11（CPU）・8/11（GPU） | 不採用（zenz を上回らない） |
| Qwen3.5-4B | 4.3B / Q4_K_M 2.80GiB | 約 +2.9GB（VRAM 想定） | CPU 275ms / **dGPU 29.1ms**（§2.4） | 尤度 11/11 | dGPU 機限定の上位版候補（保留） |
| SmolLM2-135M / 360M | — | — | — | 英語専用 | 対象外 |
| OpenJev（Qwen3.5-4B）/ clef-flash（9B） | 重み約 8GB / 9B | VRAM 24GB 以上 | GPU 前提 | — | 対象外（方式のみ参考） |

- 11 問は自作の小さなセットで、精度の優劣を言える規模ではありません。zenz と 1B 汎用 LM が同数だったという事実は「この用途に 10 倍のモデルは要らない」ことの傍証にとどまります。
- zenz 系の既存評価（v2 時点・作者公表）: 曖昧性の高い自作 150 問で 従来 56 → Zenzai 100（GPT-4o は 110）、Anthy コーパス 1,745 文で Zenzai 1,179 / Google IME API 1,104。
- zenz が外した 1 問は「これから**帰社**」→「貴社」。低頻度語が文脈だけでは勝てない例で、§5 の案A（Mozc コストとの統合）で補う対象です。

### 2.2 ランタイム

| ランタイム | Mozc への組み込み | KV キャッシュの保持・ロールバック・差分入力 | その他 | 判定 |
| --- | --- | --- | --- | --- |
| **llama.cpp**（libllama, MIT） | C API。CPU のみなら依存なしで静的リンク可。ビルドは CMake なので Bazel 側は `rules_foreign_cc` か事前ビルド済みライブラリの取り込み | **最良。** `llama_memory_seq_cp`（分岐）/ `llama_memory_seq_rm`（位置指定で削除＝ロールバック）/ `llama_state_seq_save_file`（永続化）。`kv_unified=true` なら分岐はメタデータ操作のみ | LoRA を `llama_adapter_lora_init` で実行時ロード。`abort_callback` で締め切り超過時に中断可 | **採用** |
| ONNX Runtime | C/C++ API。DLL 10MB 超。モデルを past_key_values 入出力つきでエクスポートする必要 | KV は入出力テンソルとしてアプリが持つ。保持・分岐は「テンソルを取っておく」だけで自然だが、ステップごとに連結コピーが走り、複数候補の同時採点はバッチ次元の複製が要る | DirectML/CoreML は 100M 級・数トークンでは GPU 起動と転送のほうが高くつく | 次点 |
| Candle（Rust） | C++ から FFI（cxx 等）と `rules_rust` が必要 | KV はモデル構造体内。分岐・巻き戻しは自前実装 | Mozc のビルド系統に Rust を足すコストが大きい | 不採用 |

### 2.3 CPU と内蔵 GPU の比較（実測）

llama.cpp 公式ビルド b11352 の `llama-bench` で、文脈 32 トークンの後に 1/4/8 トークンを 1 回で流す時間を測りました。リランクの 1 回分（候補トークンをまとめて 1 バッチ）に相当します。数値は「1 バッチあたりの ms」（= トークン数 ÷ t/s）。

| モデル | CPU 4 スレッド 1 / 4 / 8 tok | 内蔵 GPU（UHD 630, Vulkan）1 / 4 / 8 tok |
| --- | --- | --- |
| zenz-v3.1-small Q5_K_M | **8.7 / 8.2 / 15.1** | 12.2 / 80.3 / 166 |
| Qwen3-0.6B Q4_0 | 19.8 / 24.7 / 38.9 | 38.1 / 116 / 194 |
| Qwen3-0.6B Q4_K_M | 21.4 / 23.6 / 40.5 | 42.0 / 538 / 847 |

- **内蔵 GPU はすべての条件で CPU より遅い。** 数トークンの小さなバッチでは、GPU への投入と同期の固定費が計算量を上回ります。UHD 630 は CPU とメモリ帯域も共有しているので、重みの読み出しも速くなりません。Q4_K_M は Vulkan 上で特に遅い（4 トークンで 538ms）。
- CPU の結果は、1→4 トークンでほとんど時間が増えません。候補をまとめて 1 バッチで採点する設計が効いています。
- 未検証: より新しい内蔵 GPU（Intel Xe / Arc 世代、Radeon 780M 等）や NPU、Intel 向けの OpenVINO ビルド（公式リリースに同梱あり）。「GPU があれば使う」ではなく、**起動時に CPU とミニベンチで比べて速い方を選ぶ**方式にしておけば、機種差を吸収できます。
- Qwen3 は語彙が 15 万語あり、候補トークンごとに「語彙全体への射影」（約 1.5 億パラメータ相当）が走ります。llama-bench は最後の 1 トークンしか射影しないので、実際のリランクはこの表より重くなります（PoC 実測で 2 トークン 23.5ms）。zenz は語彙 6,000 なのでこの差がほぼありません。

### 2.4 dGPU 機での再測定（RX 9060 XT）

環境: i5-12600K（10C/16T、`threads=8`）/ RX 9060 XT 16GB（Vulkan）/ RAM 48GB。llama.cpp b11352、他に GPU を使うタスクが動いていない状態で `setup_eval.ps1 -Backend vulkan` を実行（途中で別タスクと重なった回は破棄して取り直し）。生データは `02_src/poc/results/DESKTOP-R9O3S3K-vulkan-20261004-0125.{md,jsonl}`。デバイス節に RX 9060 XT が出ており、失敗した組み合わせは無し。尤度方式（`zenz` / `plain`）の rank 中央値（ms）と正解数:

| モデル | CPU（ngl=0） | dGPU（ngl=99） | 正解 CPU / GPU |
| --- | ---: | ---: | --- |
| zenz-v3.1-small | 6.3 | **1.9** | 10/11 / 10/11 |
| zenz-v3.1-xsmall | 1.6 | 1.2 | 9/11 / 9/11 |
| Qwen3-0.6B Q4_0 | 33.1 | 13.4 | 9/11 / 9/11 |
| Qwen3-0.6B Q8_0 | 68.4 | 43.5 | 9/11 / 9/11 |
| MiniCPM5-2B Q4_K_M | 104.7 | 21.6 | 9/11 / 8/11 |
| Qwen3.5-4B Q4_K_M | 275.1 | **29.1**（最大 35.8） | 11/11 / 11/11 |

選択式（`choice`、GPU）: Qwen3-0.6B Q4_0 12.0ms・7/11、Q8_0 16.2ms・6/11、MiniCPM5-2B 24.4ms・6/11、Qwen3.5-4B 80.3ms・11/11（CPU はそれぞれ 114 / 254 / 394 / 1140ms）。

引き継ぎ書 §2 の判断基準に当てはめた結論:

- **GPU は dGPU なら効く**（前回の UHD 630 とは逆）。ただし zenz-small は CPU でも 6.3ms で予算内なので、GPU を使う理由にならない。推奨構成は変えない。
- **尤度方式の Qwen3.5-4B**: 中央値 29.1ms 以下かつ 11/11 で zenz（10/11）を上回る条件は満たすが、最大 35.8ms と余裕が無く、差は 1 問。11 問では優劣を言えないため、**評価セットの拡充（数百問）後に「dGPU 機限定の上位版」として再判断**する。その際、常駐 VRAM（約 3GB）と他アプリ（ゲーム等）との GPU 競合時の遅延を測る。
- **選択式**: 30ms 以下に収まるのは 0.6B〜2B だけで、正解は 6〜7/11 と尤度方式（9/11）以下。4B は 11/11 だが 80ms で、尤度方式と同数。尤度方式より明確に正確とは言えず、採用しない。
- 4B の選択式では再帰層のため KV 巻き戻しが「全再計算」に切り替わる（`[warn]` を確認）。尤度方式の rank は影響を受けなかった。
- MiniCPM5-2B の尤度方式は CPU 9/11、GPU 8/11 と 1 問ぶれた。量子化カーネルの差の範囲と見ているが、問題数が少なく原因は未確認。
- SemIf 本家（PyTorch/BF16）との一致確認（引き継ぎ書 手順 4）は NVIDIA が無いため未実施。

## 3. Mozc 連携設計

### 3.1 変換パイプラインとフック位置

```
Session::Commit … session/session.cc:1803
└ Session::CommitInternal … :1773
   └ EngineConverter::Commit … engine/engine_converter.cc:718
      └ Converter::FinishConversion … converter/converter.cc:313
         ├ rewriter_->Finish(req, segments) … :356   ← 【確定フック】
         └ predictor_->Finish(...) … :357

Converter::StartConversion … converter/converter.cc:178
└ ApplyConversion … :544
   ├ immutable_converter_->Convert()      ラティス構築 + ビタビ + N-best
   ├ MaybeApplyPredictionToConversion()   ユーザー履歴予測のマージ
   └ ApplyPostProcessing … :293
      └ RewriteAndSuppressCandidates … :883
         └ rewriter_->Rewrite(req, segments) … :902   ← 【リランク】
```

### 3.2 リランカー: `ContextRerankRewriter`

- 新規: `src/rewriter/context_rerank_rewriter.{h,cc}`。`RewriterInterface`（`rewriter/rewriter_interface.h`）を実装する。
- 登録: `Rewriter::Rewriter()`（`rewriter/rewriter.cc:131`）の **168 行目 `if (absl::GetFlag(FLAGS_use_history_rewriter))` の直前**に `AddRewriter(...)`。
  - `VariantsRewriter` 等が候補を出し揃えた後で、`UserBoundaryHistoryRewriter` / `UserSegmentHistoryRewriter` より前。ユーザーが明示的に選び直した結果（既存学習）が LM の順位を上書きします。逆順にすると学習が効かない IME になります。
  - 末尾の `EnvironmentalFilterRewriter` / `RemoveRedundantCandidateRewriter` より前なので、後始末もそのまま効きます。
- `capability()`: `CONVERSION | SUGGESTION`。サジェスト要求は打鍵ごとに来るので、ここで読みの差分を KV に流しておけば Space 時点では読みが載った状態になります（PoC の `set_reading` に相当。実測 1 打鍵 8.6ms）。
- `Rewrite()` の処理:
  1. 対象セグメントの上位 K 候補（K ≤ 5。`UserSegmentHistoryRewriter` の `kMaxRerankSize = 5` に合わせる）を取り出す。候補が 1 つ、または 1 位が数値・記号・絵文字などのときは何もしない。
  2. 文脈文字列を決める（§3.4）。
  3. 複数文節のときは「対象文節の候補 + 後続文節の 1 位」を連結した文字列を採点する。文節単体だと右側の情報（「きしゃ**が走る**」）を使えないため。
  4. `log P` をコストに換算して既存コストと合成し、並べ替える。Mozc のコストは `-500 * log(prob)`（`prediction/dictionary_decoder.cc:340`）なので、**`llm_cost = -500 * logprob` で同じ単位**になります。
- `Rewrite()` は `const` です。KV を持つ採点器は Rewriter のメンバにせず、mutex つきの別オブジェクト（`engine::Modules` に持たせるかプロセス内シングルトン）にします。
- 締め切り: 20ms を超えたら `abort_callback` で中断し、Mozc の元の順序をそのまま返します。LM が無い・壊れている場合も同じ経路です（フェイルオープン）。

### 3.3 確定フック: `Finish()`

- `ContextRerankRewriter::Finish(const ConversionRequest&, const Segments&)` で、確定された `segment.candidate(0).value` を連結して採点器に渡す。`FinishConversion` は Enter 確定（`EngineConverter::Commit` :745）、サジェスト確定（:811）、未変換確定（`CommitPreedit` :953）のすべてから呼ばれます。
- KV の更新は**ワーカースレッドに投げて即リターン**します。確定のたびに 30〜70ms（実測: 20〜30 トークンの文脈で中央値 33ms）ブロックすると Enter が重くなります。更新が終わる前に次の変換が来ても、§3.4 の同期方式なら残りを変換側が流すだけで結果は変わりません。
- `UserSegmentHistoryRewriter::IsAvailable` / `Finish`（`rewriter/user_segment_history_rewriter.cc:619, :694`）と同じ条件で止める: `request.incognito_mode()`、`history_learning_level != DEFAULT_HISTORY`、パスワード欄(ただし Windows ではパスワード欄を判別できる信号が確認できていない。§3.4「文脈の区切り」の調査結果 4。判別できない前提で、永続化はせずメモリ上のバッファも短く保つ)。
- 併せて実装するフック: `Revert()`（確定取り消し → 文脈を巻き戻す）、`Clear()`（「履歴を消去」→ 文脈・ログ・アダプタを消す）。
- このとき「LM の 1 位とユーザーの選択が違った」事例を §5 案C 用にログへ追記します。

### 3.4 文脈の決め方と KV の同期

Rewriter はどのセッション（アプリ）から呼ばれたかを知りません。そこで **KV をセッション ID ではなくトークン列で同期**します。毎回「今あるべきプレフィックス」を作り、KV 上のトークン列との最長共通接頭辞までを再利用して残りだけ流す方式です（PoC の `_sync`）。同じアプリで打ち続ける限りコストはゼロ、アプリを切り替えたら自動的に作り直しになります。

文脈文字列の出どころ(優先順。Windows では `preceding_text` が最大 20 文字しか来ないため、文脈の主役は自前バッファ。区切りの原則は次の「文脈の区切り」節):

1. 自前のローリングバッファ（`Finish` で追記、60〜120 文字）。ただし `segments.history_segments()` の連結文字列がバッファの末尾と一致するときだけ信用する。Mozc 自身も `EngineConverter::OnStartComposition`（`engine/engine_converter.cc:1839`）で同じ整合チェックをして履歴を捨てています。
2. `request.context().preceding_text()`（`protocol/commands.proto:496`）。Windows では最大 20 文字しか来ないため、自前バッファが同じ入力先のものか確かめる照合や、単独で使う場合の短い縮退文脈として使います。`ConversionRequest::GetSurroundingContext()`（`request/conversion_request.h:225`）は改行で切った版を返します。
3. どちらも無ければ history segments のみ（最大 4 文節。`converter/segments.cc:406`）。

#### 文脈の区切り(基本方針・安全原則)

文脈は「同じ入力先の直前の文章」だけが価値を持つ。別のテキストボックスやウィンドウの文を混ぜると、文脈なしより悪化しうる。以下は Mozc の実装詳細に依存しない方針で、実装調査(Issue #8)の結果で変わるのは手段だけ。

- **原則: 誤った文脈は、文脈なしより悪い。** 同じ入力先と確認できない文脈は使わず、捨てる。迷ったら文脈なしで採点するか、LM を使わず Mozc の元の順序を返す(フェイルオープン、§3.2)。
- **優先順位:** 上の §3.4 のリストのとおり(バッファ → `preceding_text` → 履歴セグメントのみ → 文脈なし)。上位が使えないときだけ下位に落とす。
- **バッファを捨てる契機(手段は Issue #8 で確認):** フォーカス・入力先の変更、シークレットモード・パスワード欄、`Revert` / `Clear`、整合検査の不一致、一定時間の経過(閾値は未定。測って決める)。
- **持ち越さない:** 入力先をまたいで文脈を引き継がない。入力先ごとにバッファを別々に持つ案は、入力先を識別できると確認できてから判断する(未確定)。
- **記録の扱い:** 捨てた文脈は、案C のログにも残さない。

**実装調査の結果(Issue #8。`google/mozc@c7538e6`、パスは `src/` 基準):**

1. **Windows は `preceding_text` を渡すが、最大 20 文字。** `win32/tip/tip_surrounding_text.cc` の `kMaxSurroundingLength = 20`。`win32/tip/tip_keyevent_handler.cc FillMozcContextForOnKey()` が `OnKey` のたびに埋める。TSF のフルコンテキストが取れないとき(`TipTransitoryExtension::AsFullContext` が null)は IMM32 の document feed に落ち、`TipSurroundingText::Get()` が失敗すれば埋まらない。→ `preceding_text` は「入力先の同一性の確認」には使えるが、文脈そのものは**自前のローリングバッファが主**になる。どのアプリで埋まらないかは実機未確認。
2. **フォーカス変更の信号は `Context.revision` として届く。** `win32/tip/tip_text_service.cc OnSetFocus()` が `IncrementFocusRevision()` し、`FillMozcContextCommon()` が `revision` に詰める。`protocol/commands.proto:531` が「フォーカスが変わったら更新し、変換器は履歴を捨てること」と定めている。Mozc 自身は `engine/engine_converter.cc OnStartComposition()` で revision が変わり、かつ `preceding_text` と履歴が整合しないときに履歴を捨てる。→ 区切りの契機は revision の変化。Rewriter の `Rewrite()` / `Finish()` は `ConversionRequest::context()`(`request/conversion_request.h:170`)経由で `revision` を読める。
3. **Rewriter は 1 プロセスに 1 つ、全セッション共有。** `session/session_handler.h` の `SessionHandler` が `engine_` を 1 つ持ち、各 `Session` は `engine.CreateEngineConverter()`(`session/session.cc:226`)で自分の `EngineConverter` を作る(履歴セグメントはセッションごと)。`SessionHandler::MaybeReloadEngine()` で engine ごと差し替わりうるため、採点器は Rewriter の外に持ち、差し替えに耐える設計にする。複数アプリが同時に打つので、バッファは入力先(revision と対応する単位)ごとに分けるか、切り替わったら捨てる。
4. **シークレット・パスワードの信号は弱い。** `incognito_mode` は設定(`Config`)かリクエスト単位のフラグで、入力欄ごとの検出ではない(`request/conversion_request.h:195`)。パスワード欄は `Context.input_field_type == PASSWORD`(`protocol/commands.proto`)で表現でき、`Session` はこれを見て確定する(`session/session.cc CommitIfPassword()`)が、Windows の TSF クライアントがこの値を詰める箇所は `win32/` に見つからなかった(`tip_input_mode_manager.cc:66` に InputScope のコメントがあるのみで未確認)。→ Windows ではパスワード欄を確実に判別できない前提で、**文脈・読み・確定結果のいずれも永続化しない**(案C のログは、パスワード欄を判別できる手段が確認できるまで無効にする)。メモリ上のバッファも、確定後すぐ使い切れる長さ(§3.4 の 60〜120 文字)を超えて持たない。

方針への反映: 優先順位はバッファを主にした(Windows の `preceding_text` が 20 文字までのため)。リセット契機は「`revision` の変化」を第一にし、時間減衰を併用する。入力先ごとの別バッファは `revision` が単位なら実現できるが、同じ入力先に戻っても `revision` は増え続けるため(再利用されない)、戻ったときの文脈復元はできない。

### 3.5 もう 1 つの口: `SupplementalModelInterface`

Mozc には外部モデル用の差し込み口 `engine::SupplementalModelInterface`（`engine/supplemental_model_interface.h`）が既にあり、`RescoreResults(request, span<Result>)` がサジェスト経路の `DictionaryPredictor::MaybeRescoreResults`（`prediction/dictionary_predictor.cc:1090`）から呼ばれます。OSS 版は空のスタブで、`ModulesPresetBuilder::PresetSupplementalModel`（`engine/modules.cc:255`）で差し替えられます。

ただし Space 変換の経路では `PostCorrect` しか呼ばれず、それも実験フラグ付きです（`converter/converter.cc:665`）。したがって**主経路は Rewriter**、`RescoreResults` はサジェスト候補の順位まで文脈で直したくなった段階の追加口、という位置づけにします。採点器本体は両方から共有できるよう Rewriter の外に置きます。

## 4. PoC

[`02_src/poc/context_rerank_poc.py`](../02_src/poc/context_rerank_poc.py)（約 360 行）。llama-cpp-python の高レベル API は使わず、C++ 実装にそのまま写せるよう `llama.h` と 1 対 1 の低レベル関数だけで書いています。

```bash
pip install llama-cpp-python numpy
```

```bash
python 02_src/poc/context_rerank_poc.py ggml-model-Q5_K_M.gguf --style zenz --threads 4
```

モデルは Hugging Face の `Miwa-Keita/zenz-v3.1-small-gguf`。汎用 LM で試す場合は `--style plain`。

### 4.1 仕組み

| 操作 | llama.cpp の呼び出し | 意味 |
| --- | --- | --- |
| `commit(text)` | `llama_memory_seq_rm(mem, 0, lcp, -1)` → 差分を `llama_decode` | 確定文を seq 0 の KV に追記。末尾 logits を保存 |
| `set_reading(kana)` | 同上 | 読みが伸びた分だけ forward（zenz 形式のみ） |
| `rank(cands)` | 候補 i ごとに `llama_memory_seq_cp(mem, 0, i+1, -1, -1)` → 全候補のトークンを 1 バッチで `llama_decode` → `llama_get_logits_ith` | プレフィックスを共有したまま候補ごとに分岐し、1 回の forward で全候補を採点 |
| 後始末 | `llama_memory_seq_rm(mem, i+1, -1, -1)` | 分岐を破棄。seq 0 は無傷（`seq_pos_max` で検証） |

プロンプトは zenz-v3 形式の `<文脈><ヨミ(カタカナ)><出力>`。文脈が先頭にあるので、確定時に文脈部分の KV を作っておけます。各候補の最終トークンは「その次」を予測する必要がないので流しません。

### 4.2 実行結果（zenz-v3.1-small, 4 スレッド, i3-8100）

```
[きしゃ] 文脈なしの 1 位: 記者
  OK 新聞社の取材を受けた。質問してきた【記者】  記者:-0.00 貴社:-6.71 帰社:-10.32 汽車:-10.72
  OK 平素より大変お世話になっております。さて、【貴社】  貴社:-0.05 記者:-3.22 帰社:-6.38 汽車:-6.96
  OK 鉄道博物館で蒸気機関車を見た。昔の【汽車】  汽車:-0.12 記者:-2.33 貴社:-5.09 帰社:-11.71
  NG 外出先での打ち合わせが終わったので、これから【貴社】(正解 帰社)  貴社:-0.57 帰社:-1.61 …
[こうえん] 公園 / 講演 / 公演 の 3 文脈すべて OK
[いどう]   異動 / 移動 の 2 文脈とも OK
[かんしん] 関心 / 感心 の 2 文脈とも OK

2 回目の commit で forward したのは 12 トークンのみ / rank は冪等: OK
正解率 文脈あり 10/11  文脈なし 4/11
```

| スレッド数 | commit（中央値） | 1 打鍵 | rank（中央値 / 最大） |
| --- | --- | --- | --- |
| 1 | 104.5ms | 27.6ms | 27.9ms / 33.6ms |
| 2 | 67.6ms | 15.7ms | 16.3ms / 21.3ms |
| 4 | 32.9ms | 8.6ms | **8.9ms / 12.4ms** |

同じ PoC でのモデル比較（4 スレッド、i3-8100）:

| モデル | 文脈あり | 文脈なし | rank 中央値（うち llama.cpp） | 専有メモリ増 |
| --- | --- | --- | --- | --- |
| zenz-v3.1-small Q5_K_M | 10/11 | 4/11 | 8.7ms（7.9ms） | +53MB（作業セット +95MB） |
| Qwen3-0.6B Q4_0 | 9/11 | 4/11 | 49.8ms（23.5ms） | +439MB（作業セット +717MB） |
| Qwen3-0.6B Q4_K_M | 9/11 | 4/11 | 48.3ms | +412MB（作業セット +704MB） |
| gemma-3-1b-it QAT Q4_0 | 10/11 | 4/11 | 113ms | +1020MB |
| Qwen3-0.6B Q4_0（選択式 = SemIf 方式） | 7/11 | 4/11 | 298ms | 同上 |

選択式は候補をプロンプトに並べる分、変換のたびに約 50〜80 トークンを流すため CPU では重くなります。dGPU 機（RX 9060 XT）での再測定は §2.4、再評価の手順は [GPU再調査-引き継ぎ.md](GPU再調査-引き継ぎ.md) にあります。

Qwen3 が落としたのは「帰社」と「人事で大阪支社に**異動**」→「移動」の 2 問です。Qwen3 の rank のうち llama.cpp 以外の約 16〜25ms は、Python で語彙 15 万語分の log-softmax を計算している時間で、C++ 実装では無視できる大きさになります。

注意: logits バッファは「n_batch × 語彙数 × 4 バイト」確保されます。Qwen3 で n_batch=512 にすると 300MB を超えたため、PoC は n_batch=64 にしています（専有 +710MB → +439MB）。

- commit は確定文 16〜31 トークン分。ワーカースレッドで流すので体感には乗りません。
- 計測は Python 経由（logits の numpy コピーと 6000 語彙の softmax を含む）。C++ ではこの分だけ縮みます。
- 他プロセスの負荷がある状態では同じ設定で rank 中央値 18ms・最大 54ms まで振れました。締め切りつきフェイルオープン（§3.2）はこのために必要です。
- zenz は制御文字 ``〜`` がそれぞれ 3 バイトトークンに分かれるため、読みを 1 文字足すたびに `` の 3 トークンを流し直しています。`` を候補側のバッチに回せば 1 打鍵あたりの forward は 1 トークンに減らせます（未実装）。

### 4.3 PoC が示していないこと

- 評価は 11 問のみ。採否を決める前に、同音異義語を含む文脈つきテストセット（数百問）で Mozc 単体との勝敗と「悪化させた件数」を測る必要があります。Mozc 側には `converter/quality_regression_*` の枠組みがあります。
- Mozc のコストとの合成（§5 案A）と λ の調整は未実装です。
- 候補は手で与えています。実際の Mozc N-best（文節区切りが違う候補を含む）での挙動は未確認です。

## 5. パーソナライズ

**結論: 案A を最初から入れる。案B は「変わらないプロファイル」に限って使う。案C は案A のログが溜まり、効果が測れてから。**

候補を作るのは辞書（ユーザー辞書を含む）で、LM は並べ替えるだけです。したがって未知の固有名詞を「出せるようにする」のは従来どおりユーザー辞書と履歴学習の仕事で、パーソナライズの論点は「LM がユーザーの語を不当に下げないこと」に絞られます。

### 案A: Mozc スコアとのアンサンブル — 必須

```
score(c) = mozc_cost(c) + λ · (−500 · logP_LM(c | 文脈, 読み))
```

- 単位が揃っているので線形和で済みます。λ は評価セットで決め、初期値は 0.5 前後から。
- **入れ替えは「LM の 1 位と Mozc の 1 位の差がしきい値以上」のときだけ**にします。僅差で順位が毎回揺れると学習済みの指の動きを壊します。
- LM に触らせない候補: `USER_DICTIONARY` 属性つき、ユーザー履歴由来（`USER_HISTORY_PREDICTION`）、`NO_LEARNING` 系。これらは Mozc 側の順位を固定します。
- Rewriter の順序（§3.2）により、ユーザーが一度選び直した候補は次回から `UserSegmentHistoryRewriter` が 1 位に上げます。LM のミス（例: 帰社→貴社）はこの既存機構で 1 回の訂正で直ります。追加実装は不要です。

### 案B: In-Context Learning — 静的プロファイルのみ採用

- zenz-v3 は ``（プロファイル）を学習済みで、``（トピック）等は実験的扱いです。条件は文脈より前に置きます（正確な並びは azooKey の Zenz 実装で要確認）。
- **プレフィックスの先頭に置いて変えないものだけ**が KV キャッシュと両立します。「氏名・所属・職種」程度の短いプロファイルは起動時に 1 回流し、`llama_state_seq_save_file` で保存しておけば次回起動時の再計算も不要です。
- 「直近の確定履歴」を別枠で差し込む必要はありません。それは既に文脈（§3.4）として入っています。
- 「頻出単語リスト」を動的に差し込む案は不採用とします。リストが変わるたびに以降の KV が全滅し、95M のモデルが長いリストを使いこなせる保証もなく、同じ効果は案A の固定ルールで確実に得られます。

### 案C: ログからの LoRA 適応 — 後回し

- ログ: `Finish()` で（文脈・読み・候補リスト・LM の 1 位・ユーザーの選択）を、不一致のときだけローカルに保存。シークレットモードとパスワード欄では保存しない。ただし Windows ではパスワード欄を判別できる信号が確認できていない(§3.4「文脈の区切り」の調査結果 4)ため、**判別手段が確認できるまでログ保存は無効**にする。`Clear()` でログとアダプタを消す。
- 学習: zenz の本来の目的関数（`文脈 + 読み → 選ばれた表層` の交差エントロピー）で足ります。候補集合上の softmax 損失にすれば「選ばれなかった候補を下げる」選好学習になり、DPO を持ち出す必要はありません。
- 実行: llama.cpp 側に保守された学習機能は無い前提で、学習は別プロセス（PyTorch + PEFT）で行い、GGUF の LoRA に変換して `llama_adapter_lora_init` / `llama_set_adapters_lora` で読み込みます。95M なら CPU でも現実的ですが、PyTorch をエンドユーザー環境に配る重さが最大の障害です。
- 安全弁: ログの一部を検証用に残し、適応後に悪化したらアダプタを捨てる。
- 後回しにする理由: 案A の時点で「訂正は 1 回で効く」ため、案C の上積みは「同じ傾向の未見の語にも汎化する」部分だけです。それがどれだけあるかは案A のログを見ないと分かりません。

## 6. 進め方

1. **評価セットを作る**（文脈つき同音異義語、数百問）。Mozc 単体・zenz-small・xsmall を同じセットで比較し、λ としきい値を決める。
2. 採点器を C++ で実装（PoC の `ContextScorer` を `llama.h` に写す）。締め切りと中断を入れる。
3. `ContextRerankRewriter` を追加し、`converter_main`（`converter/converter_main.cc`）で対話確認 → `mozc_server` に組み込む。
4. ライセンスと配布形態（同梱か別ダウンロードか）を確定する。
5. 案B の静的プロファイル、続いて案C の要否判断。

## 出典

- Mozc ソース: <https://github.com/google/mozc>（`c7538e6`）
- zenz-v3.1-small: <https://huggingface.co/Miwa-Keita/zenz-v3.1-small-gguf> / xsmall: <https://huggingface.co/Miwa-Keita/zenz-v3.1-xsmall-gguf>
- zenz のプロンプト形式: <https://github.com/azooKey/AzooKeyKanaKanjiConverter/blob/main/Docs/zenzai.md>
- Zenzai の仕組みと評価: <https://zenn.dev/azookey/articles/ea15bacf81521e>
- llama.cpp API: <https://github.com/ggml-org/llama.cpp/blob/master/include/llama.h>
- Qwen3-0.6B GGUF のサイズ: <https://huggingface.co/bartowski/Qwen_Qwen3-0.6B-GGUF>
- sarashina2.2: <https://huggingface.co/sbintuitions>
- SmolLM2: <https://huggingface.co/HuggingFaceTB/SmolLM2-135M>
- Jev / OpenJev: <https://note.com/stardusthouse/n/n031246d6668f> / <https://www.nobodywho.ai/posts/jev-in-25-lines/>
- clef-flash: <https://huggingface.co/Cloudflare/clef-flash>
