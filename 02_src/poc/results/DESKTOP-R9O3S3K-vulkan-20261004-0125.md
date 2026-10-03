# 再評価結果 DESKTOP-R9O3S3K / vulkan / 20261004-0125

- CPU: Intel64 Family 6 Model 151 Stepping 2, GenuineIntel / threads=8
- llama.cpp b11352, llama-cpp-python のバインディング + 公式 DLL

## デバイス
```
Available devices:
  Vulkan0: AMD Radeon RX 9060 XT (16304 MiB, 15416 MiB free)
  Vulkan1: Intel(R) UHD Graphics 770 (24457 MiB, 31762 MiB free)
```

## llama-bench(文脈 32 トークン後に 1/4/8/64 トークンを 1 バッチ)

ms/バッチ = トークン数 ÷ t/s。64 は選択式プロンプトの読み+候補部分に相当。

### zenz-small — CPU

| model                          |       size |     params | backend    | threads |            test |                  t/s |
| ------------------------------ | ---------: | ---------: | ---------- | ------: | --------------: | -------------------: |
| gpt2 0.1B Q5_K - Medium        |  70.26 MiB |    95.06 M | CPU        |       8 |       pp1 @ d32 |       209.94 ± 38.02 |
| gpt2 0.1B Q5_K - Medium        |  70.26 MiB |    95.06 M | CPU        |       8 |       pp4 @ d32 |      756.29 ± 168.17 |
| gpt2 0.1B Q5_K - Medium        |  70.26 MiB |    95.06 M | CPU        |       8 |       pp8 @ d32 |       840.35 ± 93.85 |
| gpt2 0.1B Q5_K - Medium        |  70.26 MiB |    95.06 M | CPU        |       8 |      pp64 @ d32 |     2201.68 ± 179.64 |

build: 4e2713c16 (11352)

### zenz-small — GPU

| model                          |       size |     params | backend    | ngl |            test |                  t/s |
| ------------------------------ | ---------: | ---------: | ---------- | --: | --------------: | -------------------: |
| gpt2 0.1B Q5_K - Medium        |  70.26 MiB |    95.06 M | Vulkan     |  99 |       pp1 @ d32 |      848.25 ± 180.14 |
| gpt2 0.1B Q5_K - Medium        |  70.26 MiB |    95.06 M | Vulkan     |  99 |       pp4 @ d32 |     2785.06 ± 101.38 |
| gpt2 0.1B Q5_K - Medium        |  70.26 MiB |    95.06 M | Vulkan     |  99 |       pp8 @ d32 |     4183.00 ± 133.30 |
| gpt2 0.1B Q5_K - Medium        |  70.26 MiB |    95.06 M | Vulkan     |  99 |      pp64 @ d32 |    16908.98 ± 274.27 |

build: 4e2713c16 (11352)

### zenz-xsmall — CPU

| model                          |       size |     params | backend    | threads |            test |                  t/s |
| ------------------------------ | ---------: | ---------: | ---------- | ------: | --------------: | -------------------: |
| gpt2 ?B Q5_K - Medium          |  19.81 MiB |    25.58 M | CPU        |       8 |       pp1 @ d32 |     2018.40 ± 753.15 |
| gpt2 ?B Q5_K - Medium          |  19.81 MiB |    25.58 M | CPU        |       8 |       pp4 @ d32 |     4341.11 ± 934.40 |
| gpt2 ?B Q5_K - Medium          |  19.81 MiB |    25.58 M | CPU        |       8 |       pp8 @ d32 |     3449.14 ± 416.74 |
| gpt2 ?B Q5_K - Medium          |  19.81 MiB |    25.58 M | CPU        |       8 |      pp64 @ d32 |     9062.15 ± 263.28 |

build: 4e2713c16 (11352)

### zenz-xsmall — GPU

| model                          |       size |     params | backend    | ngl |            test |                  t/s |
| ------------------------------ | ---------: | ---------: | ---------- | --: | --------------: | -------------------: |
| gpt2 ?B Q5_K - Medium          |  19.81 MiB |    25.58 M | Vulkan     |  99 |       pp1 @ d32 |     1574.94 ± 370.53 |
| gpt2 ?B Q5_K - Medium          |  19.81 MiB |    25.58 M | Vulkan     |  99 |       pp4 @ d32 |     5142.60 ± 901.73 |
| gpt2 ?B Q5_K - Medium          |  19.81 MiB |    25.58 M | Vulkan     |  99 |       pp8 @ d32 |     9023.98 ± 827.51 |
| gpt2 ?B Q5_K - Medium          |  19.81 MiB |    25.58 M | Vulkan     |  99 |      pp64 @ d32 |   47874.25 ± 3404.88 |

build: 4e2713c16 (11352)

### qwen3-0.6b-q4_0 — CPU

| model                          |       size |     params | backend    | threads |            test |                  t/s |
| ------------------------------ | ---------: | ---------: | ---------- | ------: | --------------: | -------------------: |
| qwen3 0.6B Q4_0                | 442.24 MiB |   751.63 M | CPU        |       8 |       pp1 @ d32 |         49.17 ± 6.82 |
| qwen3 0.6B Q4_0                | 442.24 MiB |   751.63 M | CPU        |       8 |       pp4 @ d32 |       190.04 ± 11.39 |
| qwen3 0.6B Q4_0                | 442.24 MiB |   751.63 M | CPU        |       8 |       pp8 @ d32 |       302.16 ± 21.40 |
| qwen3 0.6B Q4_0                | 442.24 MiB |   751.63 M | CPU        |       8 |      pp64 @ d32 |       667.35 ± 20.54 |

build: 4e2713c16 (11352)

### qwen3-0.6b-q4_0 — GPU

| model                          |       size |     params | backend    | ngl |            test |                  t/s |
| ------------------------------ | ---------: | ---------: | ---------- | --: | --------------: | -------------------: |
| qwen3 0.6B Q4_0                | 442.24 MiB |   751.63 M | Vulkan     |  99 |       pp1 @ d32 |       360.81 ± 62.91 |
| qwen3 0.6B Q4_0                | 442.24 MiB |   751.63 M | Vulkan     |  99 |       pp4 @ d32 |       1019.48 ± 8.28 |
| qwen3 0.6B Q4_0                | 442.24 MiB |   751.63 M | Vulkan     |  99 |       pp8 @ d32 |      1365.20 ± 19.40 |
| qwen3 0.6B Q4_0                | 442.24 MiB |   751.63 M | Vulkan     |  99 |      pp64 @ d32 |      7372.42 ± 93.57 |

build: 4e2713c16 (11352)

### semif-qwen3-0.6b-q8_0 — CPU

| model                          |       size |     params | backend    | threads |            test |                  t/s |
| ------------------------------ | ---------: | ---------: | ---------- | ------: | --------------: | -------------------: |
| qwen3 0.6B Q8_0                | 604.15 MiB |   596.05 M | CPU        |       8 |       pp1 @ d32 |         34.19 ± 1.40 |
| qwen3 0.6B Q8_0                | 604.15 MiB |   596.05 M | CPU        |       8 |       pp4 @ d32 |       106.71 ± 13.33 |
| qwen3 0.6B Q8_0                | 604.15 MiB |   596.05 M | CPU        |       8 |       pp8 @ d32 |        183.08 ± 8.10 |
| qwen3 0.6B Q8_0                | 604.15 MiB |   596.05 M | CPU        |       8 |      pp64 @ d32 |       347.14 ± 16.65 |

build: 4e2713c16 (11352)

### semif-qwen3-0.6b-q8_0 — GPU

| model                          |       size |     params | backend    | ngl |            test |                  t/s |
| ------------------------------ | ---------: | ---------: | ---------- | --: | --------------: | -------------------: |
| qwen3 0.6B Q8_0                | 604.15 MiB |   596.05 M | Vulkan     |  99 |       pp1 @ d32 |       277.96 ± 38.45 |
| qwen3 0.6B Q8_0                | 604.15 MiB |   596.05 M | Vulkan     |  99 |       pp4 @ d32 |        974.45 ± 4.42 |
| qwen3 0.6B Q8_0                | 604.15 MiB |   596.05 M | Vulkan     |  99 |       pp8 @ d32 |      1279.74 ± 13.88 |
| qwen3 0.6B Q8_0                | 604.15 MiB |   596.05 M | Vulkan     |  99 |      pp64 @ d32 |      6745.29 ± 98.91 |

build: 4e2713c16 (11352)

### semif-minicpm5-2b-q4_k_m — CPU

| model                          |       size |     params | backend    | threads |            test |                  t/s |
| ------------------------------ | ---------: | ---------: | ---------- | ------: | --------------: | -------------------: |
| llama ?B Q4_K - Medium         |   1.45 GiB |     2.52 B | CPU        |       8 |       pp1 @ d32 |         14.86 ± 0.44 |
| llama ?B Q4_K - Medium         |   1.45 GiB |     2.52 B | CPU        |       8 |       pp4 @ d32 |         50.39 ± 6.06 |
| llama ?B Q4_K - Medium         |   1.45 GiB |     2.52 B | CPU        |       8 |       pp8 @ d32 |         85.63 ± 3.43 |
| llama ?B Q4_K - Medium         |   1.45 GiB |     2.52 B | CPU        |       8 |      pp64 @ d32 |        178.22 ± 3.38 |

build: 4e2713c16 (11352)

### semif-minicpm5-2b-q4_k_m — GPU

| model                          |       size |     params | backend    | ngl |            test |                  t/s |
| ------------------------------ | ---------: | ---------: | ---------- | --: | --------------: | -------------------: |
| llama ?B Q4_K - Medium         |   1.45 GiB |     2.52 B | Vulkan     |  99 |       pp1 @ d32 |       144.61 ± 13.54 |
| llama ?B Q4_K - Medium         |   1.45 GiB |     2.52 B | Vulkan     |  99 |       pp4 @ d32 |        394.34 ± 1.87 |
| llama ?B Q4_K - Medium         |   1.45 GiB |     2.52 B | Vulkan     |  99 |       pp8 @ d32 |        549.96 ± 6.12 |
| llama ?B Q4_K - Medium         |   1.45 GiB |     2.52 B | Vulkan     |  99 |      pp64 @ d32 |      2351.15 ± 13.33 |

build: 4e2713c16 (11352)

### semif-qwen3.5-4b-q4_k_m — CPU

| model                          |       size |     params | backend    | threads |            test |                  t/s |
| ------------------------------ | ---------: | ---------: | ---------- | ------: | --------------: | -------------------: |
| qwen35 4B Q4_K - Medium        |   2.80 GiB |     4.33 B | CPU        |       8 |       pp1 @ d32 |          6.69 ± 0.15 |
| qwen35 4B Q4_K - Medium        |   2.80 GiB |     4.33 B | CPU        |       8 |       pp4 @ d32 |         24.20 ± 0.58 |
| qwen35 4B Q4_K - Medium        |   2.80 GiB |     4.33 B | CPU        |       8 |       pp8 @ d32 |         25.25 ± 5.44 |
| qwen35 4B Q4_K - Medium        |   2.80 GiB |     4.33 B | CPU        |       8 |      pp64 @ d32 |         72.96 ± 5.10 |

build: 4e2713c16 (11352)

### semif-qwen3.5-4b-q4_k_m — GPU

| model                          |       size |     params | backend    | ngl |            test |                  t/s |
| ------------------------------ | ---------: | ---------: | ---------- | --: | --------------: | -------------------: |
| qwen35 4B Q4_K - Medium        |   2.80 GiB |     4.33 B | Vulkan     |  99 |       pp1 @ d32 |         75.54 ± 6.36 |
| qwen35 4B Q4_K - Medium        |   2.80 GiB |     4.33 B | Vulkan     |  99 |       pp4 @ d32 |       200.62 ± 20.39 |
| qwen35 4B Q4_K - Medium        |   2.80 GiB |     4.33 B | Vulkan     |  99 |       pp8 @ d32 |        277.22 ± 9.93 |
| qwen35 4B Q4_K - Medium        |   2.80 GiB |     4.33 B | Vulkan     |  99 |      pp64 @ d32 |      1226.02 ± 24.38 |

build: 4e2713c16 (11352)

## PoC(cases.jsonl, rank = 変換キー押下時の処理時間)

| モデル | MB | 方式 | ngl | 正解 | 文脈なし | rank 中央値 ms | rank 最大 ms | commit ms | 1 打鍵 ms |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| zenz-small | 70 | zenz | 0 | 10/11 | 4/11 | 6.3 | 7.2 | 16.3 | 5.8 |
| zenz-small | 70 | zenz | 99 | 10/11 | 4/11 | 1.9 | 2.0 | 4.8 | 1.8 |
| zenz-xsmall | 20 | zenz | 0 | 9/11 | 4/11 | 1.6 | 2.0 | 4.9 | 1.3 |
| zenz-xsmall | 20 | zenz | 99 | 9/11 | 4/11 | 1.2 | 1.8 | 3.3 | 1.2 |
| qwen3-0.6b-q4_0 | 448 | plain | 0 | 9/11 | 4/11 | 33.1 | 35.0 | 31.2 | 0.0 |
| qwen3-0.6b-q4_0 | 448 | plain | 99 | 9/11 | 4/11 | 13.4 | 15.9 | 12.0 | 0.0 |
| qwen3-0.6b-q4_0 | 448 | choice | 0 | 7/11 | 4/11 | 113.6 | 124.0 | 113.4 | 0.0 |
| qwen3-0.6b-q4_0 | 448 | choice | 99 | 7/11 | 4/11 | 12.0 | 14.7 | 14.2 | 0.0 |
| semif-qwen3-0.6b-q8_0 | 610 | plain | 0 | 9/11 | 4/11 | 68.4 | 95.6 | 71.7 | 0.0 |
| semif-qwen3-0.6b-q8_0 | 610 | plain | 99 | 9/11 | 4/11 | 43.5 | 54.7 | 21.8 | 0.0 |
| semif-qwen3-0.6b-q8_0 | 610 | choice | 0 | 6/11 | 4/11 | 253.8 | 314.3 | 255.8 | 0.0 |
| semif-qwen3-0.6b-q8_0 | 610 | choice | 99 | 6/11 | 4/11 | 16.2 | 18.3 | 18.7 | 0.0 |
| semif-minicpm5-2b-q4_k_m | 1489 | plain | 0 | 9/11 | 4/11 | 104.7 | 121.5 | 152.6 | 0.0 |
| semif-minicpm5-2b-q4_k_m | 1489 | plain | 99 | 8/11 | 4/11 | 21.6 | 24.2 | 35.1 | 0.0 |
| semif-minicpm5-2b-q4_k_m | 1489 | choice | 0 | 6/11 | 4/11 | 394.2 | 427.5 | 422.4 | 0.0 |
| semif-minicpm5-2b-q4_k_m | 1489 | choice | 99 | 6/11 | 4/11 | 24.4 | 33.2 | 28.0 | 0.0 |
| semif-qwen3.5-4b-q4_k_m | 2873 | plain | 0 | 11/11 | 4/11 | 275.1 | 312.5 | 289.7 | 0.0 |
| semif-qwen3.5-4b-q4_k_m | 2873 | plain | 99 | 11/11 | 4/11 | 29.1 | 35.8 | 58.6 | 0.0 |
| semif-qwen3.5-4b-q4_k_m | 2873 | choice | 0 | 11/11 | 4/11 | 1139.6 | 1270.4 | 768.4 | 0.0 |
| semif-qwen3.5-4b-q4_k_m | 2873 | choice | 99 | 11/11 | 4/11 | 80.3 | 120.7 | 44.3 | 0.0 |
