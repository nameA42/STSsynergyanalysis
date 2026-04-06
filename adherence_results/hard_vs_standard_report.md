# Five-Mask Comparison Report

Model accuracy across five pair-set masks of increasing difficulty/specificity.

**Hard** = edge-case pairs (hand-curated, n=77) + uncertain pairs (decimal/integer GT sign flip, n=12, overlap=3)  
**Light Hard** = pairs where row ∈ {Berserk, Exhume, Havoc, Sentinel, True Grit} or col ∈ {Double Tap, Fiend Fire, Havoc, Sentinel, True Grit} — minus hard  
**Standard** = all − hard  
**Light Standard** = all − hard − light hard  


## Summary: Accuracy and Macro F1

| Model            |     All (n=5625)      |      Hard (n=86)      |   Standard (n=5539)   |  Light Hard (n=686)   | Light Standard (n=4853) |
|------------------|-----------------------|-----------------------|-----------------------|-----------------------|-----------------------|
|                  |        Acc     MacF1 |        Acc     MacF1 |        Acc     MacF1 |        Acc     MacF1 |        Acc     MacF1 |
|------------------|-----------------------|-----------------------|-----------------------|-----------------------|-----------------------|
| gpt4o            |      80.5%     56.3% |      53.5%     48.1% |      80.9%     56.3% |      72.3%     50.2% |      82.2%     57.0% |
| gpt54            |      80.1%     56.0% |      53.5%     44.8% |      80.5%     56.1% |      68.5%     49.1% |      82.2%     56.6% |
| gemini10pro      |      42.9%     32.6% |      36.0%     28.9% |      43.0%     32.6% |      43.0%     32.9% |      43.0%     32.5% |
| gemini15flash    |      76.3%     49.7% |      47.7%     40.8% |      76.8%     49.7% |      70.0%     46.3% |      77.7%     50.0% |
| gpt4omini        |      68.1%     46.6% |      43.0%     37.5% |      68.5%     46.6% |      58.9%     40.4% |      69.9%     47.6% |
| gpt4ominift      |      79.4%     50.7% |      51.2%     39.1% |      79.8%     50.9% |      72.6%     44.6% |      80.8%     52.1% |
| gemini3flash     |      82.3%     60.4% |      54.7%     46.3% |      82.7%     60.7% |      71.0%     50.9% |      84.4%     62.1% |
| llama4maverick   |      74.0%     53.3% |      55.8%     51.5% |      74.3%     53.1% |      65.3%     49.6% |      75.5%     53.3% |

---

## All (n=5625)

Every pair in the 75×75 matrix.

| Model | n | Accuracy | Macro F1 | F1(−1) | F1(0) | F1(+1) |
|-------|---|----------|----------|--------|-------|--------|
| gpt4o | 5625 | 80.5% | 56.3% | 16.5% | 87.9% | 64.5% |
| gpt54 | 5625 | 80.1% | 56.0% | 14.4% | 87.8% | 65.7% |
| gemini10pro | 5625 | 42.9% | 32.6% | 11.1% | 51.1% | 35.7% |
| gemini15flash | 5625 | 76.3% | 49.7% | 16.5% | 85.5% | 47.1% |
| gpt4omini | 5625 | 68.1% | 46.6% | 15.6% | 78.4% | 45.9% |
| gpt4ominift | 5625 | 79.4% | 50.7% | 12.9% | 87.6% | 51.6% |
| gemini3flash | 5625 | 82.3% | 60.4% | 20.7% | 88.9% | 71.7% |
| llama4maverick | 5625 | 74.0% | 53.3% | 23.5% | 82.8% | 53.7% |

---

## Hard (n=86)

Edge-case pairs (hand-curated as non-obvious) plus uncertain pairs (where decimal GT and integer GT sign disagree). The most challenging subset.

| Model | n | Accuracy | Macro F1 | F1(−1) | F1(0) | F1(+1) |
|-------|---|----------|----------|--------|-------|--------|
| gpt4o | 86 | 53.5% | 48.1% | 33.3% | 59.5% | 51.4% |
| gpt54 | 86 | 53.5% | 44.8% | 16.7% | 62.8% | 54.8% |
| gemini10pro | 86 | 36.0% | 28.9% | 10.5% | 29.0% | 47.2% |
| gemini15flash | 86 | 47.7% | 40.8% | 26.7% | 56.2% | 39.3% |
| gpt4omini | 86 | 43.0% | 37.5% | 21.1% | 49.4% | 42.1% |
| gpt4ominift | 86 | 51.2% | 39.1% | 11.1% | 62.6% | 43.6% |
| gemini3flash | 86 | 54.7% | 46.3% | 14.8% | 57.5% | 66.7% |
| llama4maverick | 86 | 55.8% | 51.5% | 40.0% | 56.8% | 57.8% |

---

## Standard (n=5539)

All pairs not in the hard set. Represents typical pair difficulty.

| Model | n | Accuracy | Macro F1 | F1(−1) | F1(0) | F1(+1) |
|-------|---|----------|----------|--------|-------|--------|
| gpt4o | 5539 | 80.9% | 56.3% | 15.8% | 88.1% | 64.9% |
| gpt54 | 5539 | 80.5% | 56.1% | 14.3% | 88.1% | 66.1% |
| gemini10pro | 5539 | 43.0% | 32.6% | 11.1% | 51.3% | 35.5% |
| gemini15flash | 5539 | 76.8% | 49.7% | 16.0% | 85.8% | 47.3% |
| gpt4omini | 5539 | 68.5% | 46.6% | 15.2% | 78.7% | 46.0% |
| gpt4ominift | 5539 | 79.8% | 50.9% | 13.0% | 87.8% | 51.8% |
| gemini3flash | 5539 | 82.7% | 60.7% | 20.9% | 89.1% | 71.9% |
| llama4maverick | 5539 | 74.3% | 53.1% | 22.8% | 83.0% | 53.5% |

---

## Light Hard (n=686)

Pairs involving cards in rows {Berserk, Exhume, Havoc, Sentinel, True Grit} or columns {Double Tap, Fiend Fire, Havoc, Sentinel, True Grit}, after removing the hard set. A mid-tier difficulty band.

| Model | n | Accuracy | Macro F1 | F1(−1) | F1(0) | F1(+1) |
|-------|---|----------|----------|--------|-------|--------|
| gpt4o | 686 | 72.3% | 50.2% | 17.1% | 82.6% | 50.9% |
| gpt54 | 686 | 68.5% | 49.1% | 20.1% | 79.9% | 47.3% |
| gemini10pro | 686 | 43.0% | 32.9% | 11.8% | 54.0% | 32.8% |
| gemini15flash | 686 | 70.0% | 46.3% | 20.2% | 81.4% | 37.2% |
| gpt4omini | 686 | 58.9% | 40.4% | 12.9% | 71.1% | 37.1% |
| gpt4ominift | 686 | 72.6% | 44.6% | 6.7% | 83.1% | 44.0% |
| gemini3flash | 686 | 71.0% | 50.9% | 19.2% | 81.8% | 51.7% |
| llama4maverick | 686 | 65.3% | 49.6% | 30.3% | 75.9% | 42.7% |

---

## Light Standard (n=4853)

All pairs after removing both hard and light hard. The cleanest, least ambiguous subset.

| Model | n | Accuracy | Macro F1 | F1(−1) | F1(0) | F1(+1) |
|-------|---|----------|----------|--------|-------|--------|
| gpt4o | 4853 | 82.2% | 57.0% | 15.4% | 88.9% | 66.7% |
| gpt54 | 4853 | 82.2% | 56.6% | 12.2% | 89.1% | 68.4% |
| gemini10pro | 4853 | 43.0% | 32.5% | 10.9% | 50.9% | 35.8% |
| gemini15flash | 4853 | 77.7% | 50.0% | 14.7% | 86.5% | 48.7% |
| gpt4omini | 4853 | 69.9% | 47.6% | 15.8% | 79.7% | 47.4% |
| gpt4ominift | 4853 | 80.8% | 52.1% | 14.7% | 88.5% | 53.0% |
| gemini3flash | 4853 | 84.4% | 62.1% | 21.4% | 90.1% | 74.6% |
| llama4maverick | 4853 | 75.5% | 53.3% | 20.8% | 84.0% | 55.2% |

---

## Deltas vs All

How much each mask deviates from the full-dataset baseline (positive = better than all).

### Hard minus All

| Model | dAcc | dMacroF1 | dF1(−1) | dF1(0) | dF1(+1) |
|-------|------|----------|---------|--------|---------|
| gpt4o | -27.03pp | -8.18pp | +16.84pp | -28.33pp | -13.04pp |
| gpt54 | -26.64pp | -11.21pp | +2.29pp | -25.02pp | -10.89pp |
| gemini10pro | -6.89pp | -3.71pp | -0.53pp | -22.07pp | +11.46pp |
| gemini15flash | -28.65pp | -8.93pp | +10.21pp | -29.27pp | -7.72pp |
| gpt4omini | -25.10pp | -9.11pp | +5.50pp | -29.07pp | -3.77pp |
| gpt4ominift | -28.21pp | -11.55pp | -1.79pp | -24.94pp | -7.93pp |
| gemini3flash | -27.62pp | -14.07pp | -5.84pp | -31.32pp | -5.05pp |
| llama4maverick | -18.18pp | -1.79pp | +16.47pp | -26.02pp | +4.17pp |

### Standard minus All

| Model | dAcc | dMacroF1 | dF1(−1) | dF1(0) | dF1(+1) |
|-------|------|----------|---------|--------|---------|
| gpt4o | +0.42pp | +0.02pp | -0.67pp | +0.28pp | +0.45pp |
| gpt54 | +0.41pp | +0.17pp | -0.10pp | +0.25pp | +0.36pp |
| gemini10pro | +0.11pp | -0.00pp | +0.02pp | +0.22pp | -0.25pp |
| gemini15flash | +0.44pp | +0.05pp | -0.41pp | +0.32pp | +0.24pp |
| gpt4omini | +0.39pp | +0.03pp | -0.31pp | +0.28pp | +0.10pp |
| gpt4ominift | +0.44pp | +0.21pp | +0.11pp | +0.28pp | +0.23pp |
| gemini3flash | +0.43pp | +0.25pp | +0.28pp | +0.27pp | +0.19pp |
| llama4maverick | +0.28pp | -0.22pp | -0.76pp | +0.24pp | -0.13pp |

### Light Hard minus All

| Model | dAcc | dMacroF1 | dF1(−1) | dF1(0) | dF1(+1) |
|-------|------|----------|---------|--------|---------|
| gpt4o | -8.21pp | -6.07pp | +0.65pp | -5.28pp | -13.59pp |
| gpt54 | -11.61pp | -6.84pp | +5.75pp | -7.89pp | -18.39pp |
| gemini10pro | +0.07pp | +0.22pp | +0.71pp | +2.87pp | -2.91pp |
| gemini15flash | -6.35pp | -3.41pp | +3.77pp | -4.15pp | -9.84pp |
| gpt4omini | -9.23pp | -6.23pp | -2.65pp | -7.27pp | -8.76pp |
| gpt4ominift | -6.78pp | -6.11pp | -6.24pp | -4.52pp | -7.57pp |
| gemini3flash | -11.28pp | -9.51pp | -1.45pp | -7.08pp | -19.99pp |
| llama4maverick | -8.68pp | -3.70pp | +6.77pp | -6.86pp | -11.01pp |

### Light Standard minus All

| Model | dAcc | dMacroF1 | dF1(−1) | dF1(0) | dF1(+1) |
|-------|------|----------|---------|--------|---------|
| gpt4o | +1.64pp | +0.74pp | -1.06pp | +1.04pp | +2.24pp |
| gpt54 | +2.11pp | +0.63pp | -2.15pp | +1.33pp | +2.70pp |
| gemini10pro | +0.11pp | -0.08pp | -0.16pp | -0.17pp | +0.08pp |
| gemini15flash | +1.41pp | +0.28pp | -1.72pp | +0.93pp | +1.61pp |
| gpt4omini | +1.75pp | +1.01pp | +0.22pp | +1.27pp | +1.54pp |
| gpt4ominift | +1.46pp | +1.37pp | +1.75pp | +0.92pp | +1.44pp |
| gemini3flash | +2.08pp | +1.66pp | +0.79pp | +1.25pp | +2.93pp |
| llama4maverick | +1.55pp | +0.01pp | -2.68pp | +1.19pp | +1.53pp |

---

*Generated by `hard_vs_standard.py`*
