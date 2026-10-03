"""cases.jsonl を SemIf(旧 OpenJev)の semif-score 入力に変換し、その出力を採点する。

SemIf 本家(PyTorch/BF16)の選択式スコアラーで、かな漢字の同音異義語選択を
解かせるための橋渡し。PoC の --style choice(llama.cpp 量子化版)との比較に使う。

  python semif_bridge.py export cases.jsonl semif-input.jsonl
  semif-score --mode serial --model Qwen/Qwen3.5-4B --revision <rev> \
      --input semif-input.jsonl --output semif-output.jsonl
  python semif_bridge.py score cases.jsonl semif-output.jsonl
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def load(path: str) -> list[dict]:
    return [json.loads(s) for s in Path(path).read_text(encoding="utf-8").splitlines() if s.strip()]


def export(cases_path: str, out_path: str) -> None:
    rows = []
    for i, c in enumerate(load(cases_path)):
        rows.append({
            "id": f"case{i:03d}",
            # 同じ文脈が続くと semif-score --mode serial が prefix を再利用する
            "state": f"文脈: {c['context']}\n読み: {c['reading']}",
            "question": "上の文脈の直後に続く、この読みの最も適切な漢字表記はどれですか。",
            "options": [{"id": f"o{j}", "description": cand} for j, cand in enumerate(c["candidates"])],
        })
    Path(out_path).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
                              encoding="utf-8")
    print(f"{len(rows)} rows -> {out_path}")


def score(cases_path: str, output_path: str) -> None:
    cases = load(cases_path)
    preds = {r["id"]: r for r in load(output_path)}
    ok, secs = 0, []
    for i, c in enumerate(cases):
        r = preds[f"case{i:03d}"]
        best = r["option_ids"][max(range(len(r["probabilities"])), key=r["probabilities"].__getitem__)]
        top = c["candidates"][int(best[1:])]
        ok += top == c["answer"]
        if "total_seconds" in r:
            secs.append(r["total_seconds"])
        print(f"  {'OK' if top == c['answer'] else 'NG'} {c['context']}【{top}】(正解 {c['answer']})")
    model = next(iter(preds.values())).get("model", {}).get("source", "?")
    med = sorted(secs)[len(secs) // 2] * 1e3 if secs else float("nan")
    print(f"{model}: 正解 {ok}/{len(cases)}  1 判定の中央値 {med:.1f} ms")


if __name__ == "__main__":
    {"export": export, "score": score}[sys.argv[1]](*sys.argv[2:4])
