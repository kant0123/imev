# 再評価結果 DESKTOP-80AKMUB / vulkan / 20261004-0039

- CPU: Intel64 Family 6 Model 158 Stepping 11, GenuineIntel / threads=4
- llama.cpp b11352, llama-cpp-python のバインディング + 公式 DLL

## デバイス
```
Available devices:
  Vulkan0: Intel(R) UHD Graphics 630 (12115 MiB, 11347 MiB free)
```

## llama-bench(文脈 32 トークン後に 1/4/8/64 トークンを 1 バッチ)

ms/バッチ = トークン数 ÷ t/s。64 は選択式プロンプトの読み+候補部分に相当。

### zenz-small — CPU

| model                          |       size |     params | backend    | threads |            test |                  t/s |
| ------------------------------ | ---------: | ---------: | ---------- | ------: | --------------: | -------------------: |
| gpt2 0.1B Q5_K - Medium        |  70.26 MiB |    95.06 M | CPU        |       4 |       pp1 @ d32 |       244.91 ± 54.21 |
| gpt2 0.1B Q5_K - Medium        |  70.26 MiB |    95.06 M | CPU        |       4 |       pp4 @ d32 |       539.24 ± 98.39 |
| gpt2 0.1B Q5_K - Medium        |  70.26 MiB |    95.06 M | CPU        |       4 |       pp8 @ d32 |       497.65 ± 49.32 |
| gpt2 0.1B Q5_K - Medium        |  70.26 MiB |    95.06 M | CPU        |       4 |      pp64 @ d32 |      1181.45 ± 34.89 |

build: 4e2713c16 (11352)

### zenz-small — GPU

| model                          |       size |     params | backend    | ngl |            test |                  t/s |
| ------------------------------ | ---------: | ---------: | ---------- | --: | --------------: | -------------------: |
| gpt2 0.1B Q5_K - Medium        |  70.26 MiB |    95.06 M | Vulkan     |  99 |       pp1 @ d32 |         84.91 ± 3.52 |
| gpt2 0.1B Q5_K - Medium        |  70.26 MiB |    95.06 M | Vulkan     |  99 |       pp4 @ d32 |         51.76 ± 3.55 |
| gpt2 0.1B Q5_K - Medium        |  70.26 MiB |    95.06 M | Vulkan     |  99 |       pp8 @ d32 |         43.95 ± 3.33 |
| gpt2 0.1B Q5_K - Medium        |  70.26 MiB |    95.06 M | Vulkan     |  99 |      pp64 @ d32 |        389.95 ± 8.91 |

build: 4e2713c16 (11352)

### zenz-xsmall — CPU

| model                          |       size |     params | backend    | threads |            test |                  t/s |
| ------------------------------ | ---------: | ---------: | ---------- | ------: | --------------: | -------------------: |
| gpt2 ?B Q5_K - Medium          |  19.81 MiB |    25.58 M | CPU        |       4 |       pp1 @ d32 |     1039.47 ± 138.59 |
| gpt2 ?B Q5_K - Medium          |  19.81 MiB |    25.58 M | CPU        |       4 |       pp4 @ d32 |     1448.11 ± 626.08 |
| gpt2 ?B Q5_K - Medium          |  19.81 MiB |    25.58 M | CPU        |       4 |       pp8 @ d32 |     2031.37 ± 279.27 |
| gpt2 ?B Q5_K - Medium          |  19.81 MiB |    25.58 M | CPU        |       4 |      pp64 @ d32 |     4967.98 ± 315.11 |

build: 4e2713c16 (11352)

### zenz-xsmall — GPU

| model                          |       size |     params | backend    | ngl |            test |                  t/s |
| ------------------------------ | ---------: | ---------: | ---------- | --: | --------------: | -------------------: |
| gpt2 ?B Q5_K - Medium          |  19.81 MiB |    25.58 M | Vulkan     |  99 |       pp1 @ d32 |       295.08 ± 50.55 |
| gpt2 ?B Q5_K - Medium          |  19.81 MiB |    25.58 M | Vulkan     |  99 |       pp4 @ d32 |        180.83 ± 6.06 |
| gpt2 ?B Q5_K - Medium          |  19.81 MiB |    25.58 M | Vulkan     |  99 |       pp8 @ d32 |       207.84 ± 12.05 |
| gpt2 ?B Q5_K - Medium          |  19.81 MiB |    25.58 M | Vulkan     |  99 |      pp64 @ d32 |      1749.65 ± 40.63 |

build: 4e2713c16 (11352)

### qwen3-0.6b-q4_0 — CPU

| model                          |       size |     params | backend    | threads |            test |                  t/s |
| ------------------------------ | ---------: | ---------: | ---------- | ------: | --------------: | -------------------: |
| qwen3 0.6B Q4_0                | 442.24 MiB |   751.63 M | CPU        |       4 |       pp1 @ d32 |         54.65 ± 2.73 |
| qwen3 0.6B Q4_0                | 442.24 MiB |   751.63 M | CPU        |       4 |       pp4 @ d32 |        153.79 ± 4.37 |
| qwen3 0.6B Q4_0                | 442.24 MiB |   751.63 M | CPU        |       4 |       pp8 @ d32 |        185.93 ± 5.53 |
| qwen3 0.6B Q4_0                | 442.24 MiB |   751.63 M | CPU        |       4 |      pp64 @ d32 |       277.18 ± 12.45 |

build: 4e2713c16 (11352)

### qwen3-0.6b-q4_0 — GPU

| model                          |       size |     params | backend    | ngl |            test |                  t/s |
| ------------------------------ | ---------: | ---------: | ---------- | --: | --------------: | -------------------: |
| qwen3 0.6B Q4_0                | 442.24 MiB |   751.63 M | Vulkan     |  99 |       pp1 @ d32 |         25.75 ± 1.33 |
| qwen3 0.6B Q4_0                | 442.24 MiB |   751.63 M | Vulkan     |  99 |       pp4 @ d32 |         51.34 ± 0.45 |
| qwen3 0.6B Q4_0                | 442.24 MiB |   751.63 M | Vulkan     |  99 |       pp8 @ d32 |         40.37 ± 0.24 |
| qwen3 0.6B Q4_0                | 442.24 MiB |   751.63 M | Vulkan     |  99 |      pp64 @ d32 |         90.64 ± 1.60 |

build: 4e2713c16 (11352)

## PoC(cases.jsonl, rank = 変換キー押下時の処理時間)

| モデル | MB | 方式 | ngl | 正解 | 文脈なし | rank 中央値 ms | rank 最大 ms | commit ms | 1 打鍵 ms |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| zenz-small | 70 | zenz | 0 | 10/11 | 4/11 | 8.0 | 14.7 | 30.4 | 8.1 |
| zenz-small | 70 | zenz | 99 | 10/11 | 4/11 | 86.3 | 95.3 | 136.2 | 86.9 |
| zenz-xsmall | 20 | zenz | 0 | 9/11 | 4/11 | 2.8 | 4.3 | 7.8 | 2.3 |
| zenz-xsmall | 20 | zenz | 99 | 9/11 | 4/11 | 24.0 | 25.0 | 40.6 | 23.6 |
| qwen3-0.6b-q4_0 | 448 | plain | 0 | 9/11 | 4/11 | 46.2 | 49.0 | 65.9 | 0.0 |
| qwen3-0.6b-q4_0 | 448 | plain | 99 | 9/11 | 4/11 | 90.2 | 122.5 | 775.7 | 0.0 |
| qwen3-0.6b-q4_0 | 448 | choice | 0 | 7/11 | 4/11 | 298.1 | 543.6 | 290.7 | 0.0 |
| qwen3-0.6b-q4_0 | 448 | choice | 99 | 7/11 | 4/11 | 932.8 | 949.2 | 927.9 | 0.0 |
