"""文脈つき変換候補リランキングの最小 PoC (llama.cpp / KV キャッシュ)。

生成はしない。確定済み文脈を seq 0 の KV キャッシュに載せておき、変換時は
候補トークンだけを 1 回の llama_decode でまとめて teacher-forcing し、
log P(候補 | 文脈[, 読み]) を得て並べ替える。

  pip install llama-cpp-python numpy
  python context_rerank_poc.py <model.gguf> [--style zenz|plain|choice] [--threads N] [--ngl N]

--style zenz   : zenz-v3 系 (U+EE02 文脈 U+EE00 ヨミ U+EE01 出力) の条件付き変換モデル
--style plain  : 汎用 LM (Qwen / Gemma 等)。文脈の続きとして候補表層の尤度を採点する
--style choice : SemIf(旧 OpenJev)/ Jev 方式。候補を A/B/C… の選択肢としてチャット
                 プロンプトに並べ、記号トークンの logits だけを softmax する(forward 1 回)
--ngl N        : N 層を GPU に載せる。GPU 版 llama.cpp の DLL を使うには環境変数
                 LLAMA_CPP_LIB_PATH にそのフォルダを指定する(handoff 文書参照)
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import platform
import statistics
import time
from pathlib import Path

import llama_cpp as L
import numpy as np

CTX, INPUT, OUTPUT = chr(0xEE02), chr(0xEE00), chr(0xEE01)  # zenz-v3 の制御文字
LETTERS = "ABCDEFGH"


def to_katakana(s: str) -> str:
    return "".join(chr(ord(c) + 0x60) if "ぁ" <= c <= "ゖ" else c for c in s)


def log_softmax(x: np.ndarray) -> np.ndarray:
    x = x.astype(np.float64)
    m = x.max()
    return x - (m + np.log(np.exp(x - m).sum()))


def load_gpu_backends() -> None:
    """公式リリースの llama.cpp は GPU バックエンドを別 DLL で持ち、明示的に
    ロードしないと CPU しか使われない。LLAMA_CPP_LIB_PATH 指定時だけ読み込む。"""
    lib_dir = os.environ.get("LLAMA_CPP_LIB_PATH")
    if not lib_dir:
        return
    win = os.name == "nt"
    ggml = ctypes.CDLL(str(Path(lib_dir) / ("ggml.dll" if win else "libggml.so")))
    base = ctypes.CDLL(str(Path(lib_dir) / ("ggml-base.dll" if win else "libggml-base.so")))
    # 引数なしの ggml_backend_load_all() は python.exe 側のフォルダを探すので、DLL の場所を渡す
    ggml.ggml_backend_load_all_from_path.argtypes = [ctypes.c_char_p]
    ggml.ggml_backend_load_all_from_path(str(lib_dir).encode())
    ggml.ggml_backend_dev_count.restype = ctypes.c_size_t
    ggml.ggml_backend_dev_get.restype = ctypes.c_void_p
    ggml.ggml_backend_dev_get.argtypes = [ctypes.c_size_t]
    base.ggml_backend_dev_description.restype = ctypes.c_char_p
    base.ggml_backend_dev_description.argtypes = [ctypes.c_void_p]
    devs = [base.ggml_backend_dev_description(ggml.ggml_backend_dev_get(i)).decode()
            for i in range(ggml.ggml_backend_dev_count())]
    print("backend devices:", " / ".join(devs))


class ContextScorer:
    """seq 0 = 確定文脈(+読み)の KV キャッシュ。seq 1..N = 候補ごとの一時分岐。"""

    def __init__(self, model_path: str, style: str, n_threads: int = 4,
                 n_ctx: int = 1024, n_batch: int = 64, max_candidates: int = 8,
                 context_chars: tuple[int, int] = (60, 120), n_gpu_layers: int = 0):
        self.style = style
        self.max_candidates = max_candidates
        self.ctx_lo, self.ctx_hi = context_chars
        self.context = ""          # 確定済みテキスト(末尾のみ保持)
        self.reading = ""          # 未確定の読み(zenz / choice で使用)
        self.options: list[str] = []  # choice でプロンプトに並べる候補
        self.prefix: list[int] = []  # 現在 seq 0 の KV に載っているトークン列
        self.prefix_logits: np.ndarray | None = None  # prefix 直後の次トークン logits
        self.decoded_tokens = 0    # 直近の操作で実際に forward したトークン数

        self._log_cb = L.llama_log_callback(lambda *_: None)
        L.llama_log_set(self._log_cb, None)
        L.llama_backend_init()
        mp = L.llama_model_default_params()
        mp.n_gpu_layers = n_gpu_layers
        if style == "zenz":
            # zenz の GGUF は pre-tokenizer 名が 'gpt2-small-japanese-char' で、本家
            # llama.cpp は未知の名前として読み込みを拒否する。語彙は文字単位なので
            # 'default' に差し替えれば同じ分割になる(azooKey は fork 側で対応している)。
            self._kv = (L.llama_model_kv_override * 2)()
            self._kv[0].key = b"tokenizer.ggml.pre"
            self._kv[0].tag = L.LLAMA_KV_OVERRIDE_TYPE_STR
            self._kv[0].value.val_str = b"default"
            mp.kv_overrides = self._kv
        self.model = L.llama_model_load_from_file(model_path.encode(), mp)
        if not self.model:
            raise RuntimeError(f"failed to load {model_path}")
        cp = L.llama_context_default_params()
        cp.n_ctx = n_ctx
        # logits バッファは n_batch × 語彙数 × 4B 確保される。Qwen3 (語彙 15 万) で
        # n_batch=512 だと 300MB 超になるので、候補採点に足りる幅に絞る。
        cp.n_batch = n_batch
        self.n_batch = n_batch
        cp.n_seq_max = max_candidates + 1
        cp.kv_unified = True  # 全 seq が 1 本の KV を共有 → seq_cp がメタデータ操作で済む
        cp.n_threads = cp.n_threads_batch = n_threads
        self.ctx = L.llama_init_from_model(self.model, cp)
        self.vocab = L.llama_model_get_vocab(self.model)
        self.n_vocab = L.llama_vocab_n_tokens(self.vocab)
        self.mem = L.llama_get_memory(self.ctx)
        self.batch = L.llama_batch_init(n_batch, 0, 1)
        self.bos = ([L.llama_vocab_bos(self.vocab)]
                    if L.llama_vocab_get_add_bos(self.vocab) else [])
        if style == "choice":
            tmpl = L.llama_model_chat_template(self.model, None)
            if not tmpl:
                raise RuntimeError("choice には chat template 入りの instruct モデルが必要")
            self.chat_template = tmpl
            # 各記号の先頭トークン。前に空白が付く表記にならないよう単独でトークン化する
            self.letter_ids = [self._tok(c)[0] for c in LETTERS]

    # ---- 低レベル -------------------------------------------------------
    def _tok(self, text: str) -> list[int]:
        if self.style == "zenz":  # zenz の語彙に半角空白・改行は無い
            text = text.replace(" ", "　").replace("\n", "")
        b = text.encode("utf-8")
        buf = (L.llama_token * (len(b) + 8))()
        n = L.llama_tokenize(self.vocab, b, len(b), buf, len(buf), False, True)
        return list(buf[:n])

    def _decode(self, items: list[tuple[int, int, int]]) -> None:
        """items = [(token, pos, seq_id)]。全位置の logits を出力させる。"""
        for i, (t, p, s) in enumerate(items):
            self.batch.token[i] = t
            self.batch.pos[i] = p
            self.batch.n_seq_id[i] = 1
            self.batch.seq_id[i][0] = s
            self.batch.logits[i] = 1
        self.batch.n_tokens = len(items)
        if L.llama_decode(self.ctx, self.batch) != 0:
            raise RuntimeError("llama_decode failed")
        self.decoded_tokens += len(items)

    def _logits(self, i: int) -> np.ndarray:
        p = L.llama_get_logits_ith(self.ctx, i)
        return np.ctypeslib.as_array(p, shape=(self.n_vocab,)).copy()

    def _rollback(self, pos: int) -> int:
        """seq 0 の pos 以降を捨てる。再帰層を持つモデル(Qwen3.5 等のハイブリッド)は
        途中位置への巻き戻しができず seq_rm が False を返すので、全消去して 0 から
        流し直す(遅い)。実運用ではスナップショット(llama_state_seq_get/set_data)で代替する。"""
        if pos >= len(self.prefix) or L.llama_memory_seq_rm(self.mem, 0, pos, -1):
            return pos
        if not getattr(self, "_warned", False):
            print("  [warn] 部分ロールバック不可(再帰層あり) → 全再計算にフォールバック")
            self._warned = True
        L.llama_memory_seq_rm(self.mem, 0, -1, -1)
        return 0

    def _chat_prompt(self) -> str:
        # 文脈を先頭に置き、確定ごとに変わらない部分を最長にして KV を再利用させる
        user = (f"文脈: {self.context or '(なし)'}\n"
                f"上の文脈の直後に続く、読み「{self.reading}」の最も適切な表記を選んでください。\n"
                + "".join(f"{LETTERS[i]}. {o}\n" for i, o in enumerate(self.options))
                + "記号 1 文字だけで答えてください。")
        msg = (L.llama_chat_message * 1)()
        msg[0].role, msg[0].content = b"user", user.encode()
        buf = ctypes.create_string_buffer(8192)
        n = L.llama_chat_apply_template(self.chat_template, msg, 1, True, buf, len(buf))
        prompt = buf.raw[:n].decode()
        if b"<think>" in self.chat_template:  # Qwen3 系: 思考を空にして即答させる
            prompt += "<think>\n\n</think>\n\n"
        return prompt

    def _sync(self) -> None:
        """seq 0 の KV を「文脈(+読み)」に一致させる。共通接頭辞は再利用し、
        不一致以降だけ捨てて(=ロールバック)差分トークンだけ forward する。"""
        if self.style == "zenz":
            head = self._tok(CTX + self.context) if self.context else []
            target = self.bos + head + self._tok(INPUT + to_katakana(self.reading) + OUTPUT)
        elif self.style == "choice":
            target = self.bos + self._tok(self._chat_prompt())
        else:
            target = (self.bos + self._tok(self.context)) or self._tok("\n")
        lcp = 0
        while lcp < min(len(target), len(self.prefix)) and target[lcp] == self.prefix[lcp]:
            lcp += 1
        if lcp == len(target) == len(self.prefix):
            return
        lcp = min(lcp, len(target) - 1)  # 末尾 logits が要るので最低 1 トークンは流す
        lcp = self._rollback(lcp)
        items = [(t, lcp + i, 0) for i, t in enumerate(target[lcp:])]
        for s in range(0, len(items), self.n_batch):  # 長い文脈は n_batch ごとに分割
            chunk = items[s:s + self.n_batch]
            self._decode(chunk)
        self.prefix_logits = self._logits(len(chunk) - 1)
        self.prefix = target

    # ---- 公開 API -------------------------------------------------------
    def commit(self, text: str) -> None:
        """確定イベント。確定文字列を文脈に足し、KV を先回りで更新する。"""
        self.context += text
        if len(self.context) > self.ctx_hi:      # 窓あふれ時だけ作り直す(ヒステリシス)
            self.context = self.context[-self.ctx_lo:]
        self.reading = ""
        self.options = []
        self.decoded_tokens = 0
        self._sync()  # choice でも文脈部分までは確定時に流しておける

    def set_reading(self, kana: str) -> None:
        """未確定の読みが変わった(打鍵)。zenz では読みの差分だけ forward する。"""
        self.reading = kana
        self.decoded_tokens = 0
        if self.style == "zenz":
            self._sync()

    def forget_candidates(self) -> None:
        """計測用: KV を「文脈まで」に巻き戻し、次の rank で読み・候補部分を流し直させる。"""
        reading, options = self.reading, self.options
        self.reading, self.options = "", []
        if self.style == "zenz":
            target = self.bos + (self._tok(CTX + self.context) if self.context else [])
        elif self.style == "choice":
            target = self.bos + self._tok(self._chat_prompt())
        else:
            target = self.prefix
        lcp = 0
        while lcp < min(len(target), len(self.prefix)) and target[lcp] == self.prefix[lcp]:
            lcp += 1
        self.prefix = self.prefix[:self._rollback(lcp)]
        self.reading, self.options = reading, options

    def reset(self) -> None:
        self.context = self.reading = ""
        self.options = []
        self.prefix, self.prefix_logits = [], None
        L.llama_memory_clear(self.mem, True)

    def rank(self, candidates: list[str]) -> list[tuple[str, float]]:
        """候補を対数スコアの降順で返す。seq 0 は変更しない。"""
        assert 0 < len(candidates) <= self.max_candidates
        self.decoded_tokens = 0
        if self.style == "choice":
            self.options = list(candidates)
            self._sync()
            lp = log_softmax(self.prefix_logits[self.letter_ids[:len(candidates)]])
            return sorted(zip(candidates, map(float, lp)), key=lambda x: -x[1])
        self._sync()
        base = len(self.prefix)
        toks = [self._tok(c) for c in candidates]
        items, first_row = [], []
        for i, ts in enumerate(toks):
            L.llama_memory_seq_cp(self.mem, 0, i + 1, -1, -1)  # prefix を共有して分岐
            first_row.append(len(items))
            # 最終トークンの「次」は不要なので流さない。1 トークン候補は forward ゼロ。
            items += [(t, base + k, i + 1) for k, t in enumerate(ts[:-1])]
        assert len(items) <= self.n_batch, "候補トークンが n_batch を超えた"
        if items:
            self._decode(items)
        scores = []
        for i, ts in enumerate(toks):
            lp = log_softmax(self.prefix_logits)[ts[0]]
            for k in range(1, len(ts)):
                lp += log_softmax(self._logits(first_row[i] + k - 1))[ts[k]]
            scores.append(float(lp))
            L.llama_memory_seq_rm(self.mem, i + 1, -1, -1)  # 分岐を破棄(ロールバック)
        assert L.llama_memory_seq_pos_max(self.mem, 0) == base - 1
        return sorted(zip(candidates, scores), key=lambda x: -x[1])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("--style", choices=["zenz", "plain", "choice"], default="zenz")
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--ngl", type=int, default=0, help="GPU に載せる層数 (99 = 全部)")
    ap.add_argument("--cases", default=str(Path(__file__).with_name("cases.jsonl")))
    ap.add_argument("--repeat", type=int, default=20, help="rank の計測反復回数")
    ap.add_argument("--out", help="結果を 1 行 JSON で追記するファイル")
    ap.add_argument("--quiet", action="store_true", help="ケースごとの行を出さない")
    ap.add_argument("--label", help="--out の記録に付けるモデル名(既定: ファイル名)")
    args = ap.parse_args()

    cases = [json.loads(s) for s in Path(args.cases).read_text(encoding="utf-8").splitlines() if s.strip()]
    load_gpu_backends()
    t0 = time.perf_counter()
    sc = ContextScorer(args.model, args.style, n_threads=args.threads, n_gpu_layers=args.ngl)
    load_ms = 1e3 * (time.perf_counter() - t0)
    print(f"load {load_ms:.0f} ms  style={args.style} threads={args.threads} ngl={args.ngl}")

    ok = base_hit = 0
    commit_ms, type_ms, rank_ms = [], [], []
    for c in cases:
        reading, cands, context, want = c["reading"], c["candidates"], c["context"], c["answer"]
        sc.reset()
        sc.set_reading(reading)
        no_ctx = sc.rank(cands)[0][0]
        sc.reset()
        t = time.perf_counter(); sc.commit(context); t_commit = time.perf_counter() - t
        n_commit = sc.decoded_tokens
        # 打鍵を 1 文字ずつ模擬: 読みが伸びるたびに差分だけ forward される
        t = time.perf_counter()
        for j in range(1, len(reading) + 1):
            sc.set_reading(reading[:j])
        t_type = (time.perf_counter() - t) / len(reading)
        # rank = 変換キー押下時の処理。zenz/plain は読みまで流し済みの状態から、
        # choice は文脈まで流し済みの状態から、読み・候補部分を流す時間を測る。
        if args.style == "choice":
            sc.forget_candidates()
        t = time.perf_counter(); ranked = sc.rank(cands); first = time.perf_counter() - t
        n_rank = sc.decoded_tokens
        times = []
        for _ in range(args.repeat):
            if args.style == "choice":
                sc.forget_candidates()
            t = time.perf_counter(); sc.rank(cands); times.append(time.perf_counter() - t)
        top = ranked[0][0]
        ok += top == want; base_hit += no_ctx == want
        commit_ms.append(1e3 * t_commit); type_ms.append(1e3 * t_type)
        rank_ms.append(1e3 * statistics.median(times))
        if not args.quiet:
            print(f"  {'OK' if top == want else 'NG'} {context}【{top}】(正解 {want}, 文脈なし {no_ctx})  "
                  + " ".join(f"{k}:{s:.2f}" for k, s in ranked)
                  + f"  | commit {1e3 * t_commit:.1f}ms/{n_commit}tok"
                  f" key {1e3 * t_type:.1f}ms rank {rank_ms[-1]:.1f}ms/{n_rank}tok"
                  f" (初回 {1e3 * first:.1f}ms)")

    # 確定を重ねても KV が差分更新で済むこと・rank が seq 0 を汚さないことの確認
    sc.reset()
    sc.commit("新聞社の取材を受けた。")
    sc.commit("質問してきた")
    inc = sc.decoded_tokens
    sc.set_reading("きしゃ")
    probe = cases[0]["candidates"]
    a = sc.rank(probe); b = sc.rank(probe)
    assert a == b, "rank must be idempotent"
    n = len(cases)
    print(f"\n2 回目の commit で forward したのは {inc} トークン / rank は冪等: OK")
    print(f"正解率 文脈あり {ok}/{n}  文脈なし {base_hit}/{n}")
    print(f"中央値 commit {statistics.median(commit_ms):.1f} ms | "
          f"1 打鍵 {statistics.median(type_ms):.1f} ms | rank {statistics.median(rank_ms):.1f} ms "
          f"(最大 {max(rank_ms):.1f} ms)")
    if args.out:
        rec = {"host": platform.node(), "cpu": platform.processor(),
               "lib": os.environ.get("LLAMA_CPP_LIB_PATH", "llama-cpp-python bundled"),
               "model": args.label or Path(args.model).name, "style": args.style, "threads": args.threads,
               "ngl": args.ngl, "load_ms": round(load_ms), "n_cases": n, "acc": ok, "acc_no_ctx": base_hit,
               "commit_ms": round(statistics.median(commit_ms), 1),
               "key_ms": round(statistics.median(type_ms), 1),
               "rank_ms": round(statistics.median(rank_ms), 1), "rank_max_ms": round(max(rank_ms), 1)}
        with open(args.out, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
