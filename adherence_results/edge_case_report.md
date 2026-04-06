# Edge Case Analysis Report

Model accuracy on 77 hand-curated edge-case pairs, sub-divided by their
integer ground truth label. Edge cases are pairs where the correct
classification is non-obvious, requires deep game knowledge, or involves
conditional/context-dependent interactions.

> Accuracy = fraction of pairs where model predicted the correct integer GT label.  
> F1 (target) = F1 for the expected class specifically.  
> Macro F1 = unweighted average across all classes present in the sub-mask.


## Edge Positive (n=30) — edge cases where GT = +1

These are pairs the mask flagged as edge cases that *are* genuine synergies.
Models must correctly identify the positive interaction despite the non-obvious
or conditional nature of the combo.

### Pair List

| Card A | Card B | Int GT |
|--------|--------|--------|
| Armaments | Blood for Blood | +1 |
| Armaments | Reaper | +1 |
| Bash | Havoc | +1 |
| Battle Trance | Second Wind | +1 |
| Berserk | Body Slam | +1 |
| Berserk | True Grit | +1 |
| Brutality | Second Wind | +1 |
| Burning Pact | Second Wind | +1 |
| Burning Pact | Sentinel | +1 |
| Corruption | Power Through | +1 |
| Corruption | Second Wind | +1 |
| Dark Embrace | Warcry | +1 |
| Dual Wield | Second Wind | +1 |
| Evolve | Havoc | +1 |
| Evolve | Second Wind | +1 |
| Fire Breathing | Dark Embrace | +1 |
| Fire Breathing | Evolve | +1 |
| Headbutt | Fire Breathing | +1 |
| Offering | Corruption | +1 |
| Pommel Strike | Second Wind | +1 |
| Power Through | Brutality | +1 |
| Rampage | Havoc | +1 |
| Seeing Red | True Grit | +1 |
| Sentinel | Corruption | +1 |
| Shockwave | Blood for Blood | +1 |
| Shockwave | Reaper | +1 |
| Shrug it Off | Second Wind | +1 |
| True Grit | Sentinel | +1 |
| True Grit | Sever Soul | +1 |
| Warcry | Fire Breathing | +1 |

### Model Performance

| Model | n | Accuracy | Prec | Recall | F1 (target) | Macro F1 | Pred -1 | Pred 0 | Pred +1 |
|-------|---|----------|------|--------|-------------|----------|---------|--------|---------|
| gpt4o | 30 | 60.0% | 100.0% | 60.0% | 75.0% | 37.5% | 0 (0%) | 12 (40%) | 18 (60%) |
| gpt54 | 30 | 53.3% | 100.0% | 53.3% | 69.6% | 23.2% | 3 (10%) | 11 (37%) | 16 (53%) |
| gemini10pro | 30 | 66.7% | 100.0% | 66.7% | 80.0% | 20.0% | 2 (7%) | 6 (20%) | 20 (67%) |
| gemini15flash | 30 | 33.3% | 100.0% | 33.3% | 50.0% | 16.7% | 1 (3%) | 19 (63%) | 10 (33%) |
| gpt4omini | 30 | 50.0% | 100.0% | 50.0% | 66.7% | 22.2% | 3 (10%) | 12 (40%) | 15 (50%) |
| gpt4ominift | 30 | 36.7% | 100.0% | 36.7% | 53.7% | 17.9% | 2 (7%) | 17 (57%) | 11 (37%) |
| gemini3flash | 30 | 76.7% | 100.0% | 76.7% | 86.8% | 28.9% | 1 (3%) | 6 (20%) | 23 (77%) |
| llama4maverick | 30 | 73.3% | 100.0% | 73.3% | 84.6% | 28.2% | 1 (3%) | 7 (23%) | 22 (73%) |

---

## Edge Neutral (n=43) — edge cases where GT = 0

Pairs flagged as edge cases that are ultimately neutral.
The risk here is false positives — models that over-pattern-match on
card interactions may incorrectly predict synergy where there is none.

### Pair List

| Card A | Card B | Int GT |
|--------|--------|--------|
| Anger | Dropkick | +0 |
| Barricade | Berserk | +0 |
| Barricade | Corruption | +0 |
| Barricade | Sever Soul | +0 |
| Bash | Double Tap | +0 |
| Berserk | Barricade | +0 |
| Bludgeon | Feed | +0 |
| Brutality | Power Through | +0 |
| Carnage | Exhume | +0 |
| Corruption | Feed | +0 |
| Corruption | Fiend Fire | +0 |
| Corruption | Flex | +0 |
| Corruption | Offering | +0 |
| Corruption | Rage | +0 |
| Demon Form | Double Tap | +0 |
| Double Tap | Fiend Fire | +0 |
| Evolve | Sever Soul | +0 |
| Exhume | Exhume | +0 |
| Fiend Fire | Pommel Strike | +0 |
| Fiend Fire | Shrug it Off | +0 |
| Fire Breathing | Fiend Fire | +0 |
| Fire Breathing | Sever Soul | +0 |
| Ghostly Armor | Exhume | +0 |
| Immolate | Havoc | +0 |
| Inflame | Double Tap | +0 |
| Juggernaut | Berserk | +0 |
| Juggernaut | Corruption | +0 |
| Juggernaut | Sever Soul | +0 |
| Limit Break | Double Tap | +0 |
| Offering | Clash | +0 |
| Rage | Double Tap | +0 |
| Rampage | Warcry | +0 |
| Reckless Charge | Havoc | +0 |
| Reckless Charge | True Grit | +0 |
| Seeing Red | Warcry | +0 |
| Sentinel | Dual Wield | +0 |
| Sentinel | Feel No Pain | +0 |
| Sentinel | Warcry | +0 |
| Shockwave | Double Tap | +0 |
| Spot Weakness | Double Tap | +0 |
| Uppercut | Double Tap | +0 |
| Warcry | Dropkick | +0 |
| Wild Strike | Havoc | +0 |

### Model Performance

| Model | n | Accuracy | Prec | Recall | F1 (target) | Macro F1 | Pred -1 | Pred 0 | Pred +1 |
|-------|---|----------|------|--------|-------------|----------|---------|--------|---------|
| gpt4o | 43 | 58.1% | 100.0% | 58.1% | 73.5% | 24.5% | 4 (9%) | 25 (58%) | 14 (33%) |
| gpt54 | 43 | 62.8% | 100.0% | 62.8% | 77.1% | 25.7% | 8 (19%) | 27 (63%) | 8 (19%) |
| gemini10pro | 43 | 20.9% | 100.0% | 20.9% | 34.6% | 11.5% | 6 (14%) | 9 (21%) | 28 (65%) |
| gemini15flash | 43 | 62.8% | 100.0% | 62.8% | 77.1% | 25.7% | 3 (7%) | 27 (63%) | 13 (30%) |
| gpt4omini | 43 | 44.2% | 100.0% | 44.2% | 61.3% | 20.4% | 5 (12%) | 19 (44%) | 19 (44%) |
| gpt4ominift | 43 | 72.1% | 100.0% | 72.1% | 83.8% | 27.9% | 5 (12%) | 31 (72%) | 7 (16%) |
| gemini3flash | 43 | 48.8% | 100.0% | 48.8% | 65.6% | 21.9% | 13 (30%) | 21 (49%) | 9 (21%) |
| llama4maverick | 43 | 48.8% | 100.0% | 48.8% | 65.6% | 21.9% | 2 (5%) | 21 (49%) | 20 (47%) |

---

## Edge Negative (n=4) — edge cases where GT = -1

Pairs flagged as edge cases that are anti-synergies.
Small sample (n=4). Treat results as illustrative only.

### Pair List

| Card A | Card B | Int GT |
|--------|--------|--------|
| Battle Trance | Warcry | -1 |
| Offering | Sever Soul | -1 |
| Offering | True Grit | -1 |
| True Grit | Armaments | -1 |

### Model Performance

| Model | n | Accuracy | Prec | Recall | F1 (target) | Macro F1 | Pred -1 | Pred 0 | Pred +1 |
|-------|---|----------|------|--------|-------------|----------|---------|--------|---------|
| gpt4o | 4 | 75.0% | 100.0% | 75.0% | 85.7% | 42.9% | 3 (75%) | 1 (25%) | 0 (0%) |
| gpt54 | 4 | 50.0% | 100.0% | 50.0% | 66.7% | 22.2% | 2 (50%) | 1 (25%) | 1 (25%) |
| gemini10pro | 4 | 25.0% | 100.0% | 25.0% | 40.0% | 20.0% | 1 (25%) | 0 (0%) | 3 (75%) |
| gemini15flash | 4 | 50.0% | 100.0% | 50.0% | 66.7% | 33.3% | 2 (50%) | 2 (50%) | 0 (0%) |
| gpt4omini | 4 | 25.0% | 100.0% | 25.0% | 40.0% | 20.0% | 1 (25%) | 0 (0%) | 3 (75%) |
| gpt4ominift | 4 | 25.0% | 100.0% | 25.0% | 40.0% | 13.3% | 1 (25%) | 2 (50%) | 1 (25%) |
| gemini3flash | 4 | 50.0% | 100.0% | 50.0% | 66.7% | 22.2% | 2 (50%) | 1 (25%) | 1 (25%) |
| llama4maverick | 4 | 75.0% | 100.0% | 75.0% | 85.7% | 42.9% | 3 (75%) | 0 (0%) | 1 (25%) |

> **Warning — small sample (n=4).** Aggregate metrics are unreliable; the pair list above is more informative.

---

## Summary

| Model | Pos acc (n=30) | Neu acc (n=43) | Neg acc (n=4) |
|-------|-----------------|-----------------|-----------------|
| gpt4o | 60.0% | 58.1% | 75.0% |
| gpt54 | 53.3% | 62.8% | 50.0% |
| gemini10pro | 66.7% | 20.9% | 25.0% |
| gemini15flash | 33.3% | 62.8% | 50.0% |
| gpt4omini | 50.0% | 44.2% | 25.0% |
| gpt4ominift | 36.7% | 72.1% | 25.0% |
| gemini3flash | 76.7% | 48.8% | 50.0% |
| llama4maverick | 73.3% | 48.8% | 75.0% |

---

*Generated by `edge_case_analysis.py`*
