# Format Adherence Analysis

How closely do model responses follow the expected chain-of-thought format
(paper §VI-C), and does adherence correlate with prediction correctness?

## Expected Sections

  1. **Card Description**
  2. **Order of Events**
  3. **Synergy Analysis**
  4. **Conclusion**
  5. **Final Score**

> **Adherence score**: fraction of expected sections found (0–1, continuous).
> **Order score**: are found sections in the right relative order? (0–1).
> **Correlation**: point-biserial r between adherence and binary correctness.

---

## gpt4o

| | Value |
|--|--|
| Pairs analyzed | 5,625 |
| Accuracy | 80.5% (4,529 correct / 1,096 wrong) |
| Mean adherence (all) | 1.000 ± 0.000 |
| Variance in adherence (all) | 0.0000 |
| Mean adherence — correct | 1.000 (var=0.0000) |
| Mean adherence — incorrect | 1.000 (var=0.0000) |
| Adherence delta (correct − incorrect) | +0.000 |

### Correlation with Correctness

| Metric | r | p-value | Significance |
|--------|---|---------|--------------|
| Adherence score | nan | nan | N/A |
| Combined score  | nan | nan | N/A |
| Response length | -0.1786 | 1.543e-41 | *** |

### Section Presence Rates

| Section | Correct | Incorrect | Δ |
|---------|---------|-----------|---|
| Card Description | 100.0% | 100.0% | +0.0% — |
| Order of Events | 100.0% | 100.0% | +0.0% — |
| Synergy Analysis | 100.0% | 100.0% | +0.0% — |
| Conclusion | 100.0% | 100.0% | +0.0% — |
| Final Score | 100.0% | 100.0% | +0.0% — |

---

## gpt54

| | Value |
|--|--|
| Pairs analyzed | 5,625 |
| Accuracy | 80.1% (4,507 correct / 1,118 wrong) |
| Mean adherence (all) | 0.313 ± 0.124 |
| Variance in adherence (all) | 0.0154 |
| Mean adherence — correct | 0.306 (var=0.0147) |
| Mean adherence — incorrect | 0.341 (var=0.0169) |
| Adherence delta (correct − incorrect) | -0.035 |

### Correlation with Correctness

| Metric | r | p-value | Significance |
|--------|---|---------|--------------|
| Adherence score | -0.1134 | 1.437e-17 | *** |
| Combined score  | -0.1211 | 7.678e-20 | *** |
| Response length | -0.3101 | 1.266e-125 | *** |

### Section Presence Rates

| Section | Correct | Incorrect | Δ |
|---------|---------|-----------|---|
| Card Description | 38.1% | 46.0% | -7.9% ↓ |
| Order of Events | 6.7% | 17.3% | -10.5% ↓ |
| Synergy Analysis | 6.7% | 5.7% | +1.0% — |
| Conclusion | 1.3% | 1.5% | -0.2% — |
| Final Score | 100.0% | 100.0% | +0.0% — |

---

## gemini10pro

| | Value |
|--|--|
| Pairs analyzed | 5,625 |
| Accuracy | 42.9% (2,415 correct / 3,210 wrong) |
| Mean adherence (all) | 0.992 ± 0.047 |
| Variance in adherence (all) | 0.0022 |
| Mean adherence — correct | 0.992 (var=0.0018) |
| Mean adherence — incorrect | 0.992 (var=0.0025) |
| Adherence delta (correct − incorrect) | +0.001 |

### Correlation with Correctness

| Metric | r | p-value | Significance |
|--------|---|---------|--------------|
| Adherence score | 0.0091 | 0.4971 | ns |
| Combined score  | 0.0078 | 0.5587 | ns |
| Response length | -0.2236 | 1.079e-64 | *** |

### Section Presence Rates

| Section | Correct | Incorrect | Δ |
|---------|---------|-----------|---|
| Card Description | 99.1% | 99.2% | -0.1% — |
| Order of Events | 99.1% | 99.3% | -0.2% — |
| Synergy Analysis | 98.1% | 98.0% | +0.1% — |
| Conclusion | 99.9% | 99.5% | +0.4% — |
| Final Score | 99.9% | 99.7% | +0.2% — |

---

## gemini15flash

| | Value |
|--|--|
| Pairs analyzed | 4,810 |
| Accuracy | 75.5% (3,632 correct / 1,178 wrong) |
| Mean adherence (all) | 1.000 ± 0.012 |
| Variance in adherence (all) | 0.0001 |
| Mean adherence — correct | 1.000 (var=0.0002) |
| Mean adherence — incorrect | 1.000 (var=0.0000) |
| Adherence delta (correct − incorrect) | -0.000 |

### Correlation with Correctness

| Metric | r | p-value | Significance |
|--------|---|---------|--------------|
| Adherence score | -0.0082 | 0.5691 | ns |
| Combined score  | -0.0081 | 0.573 | ns |
| Response length | -0.3031 | 9.87e-103 | *** |

### Section Presence Rates

| Section | Correct | Incorrect | Δ |
|---------|---------|-----------|---|
| Card Description | 100.0% | 100.0% | -0.0% — |
| Order of Events | 100.0% | 100.0% | -0.0% — |
| Synergy Analysis | 100.0% | 100.0% | -0.0% — |
| Conclusion | 100.0% | 100.0% | -0.0% — |
| Final Score | 100.0% | 100.0% | +0.0% — |

---

## gpt4omini

| | Value |
|--|--|
| Pairs analyzed | 5,625 |
| Accuracy | 68.1% (3,832 correct / 1,793 wrong) |
| Mean adherence (all) | 1.000 ± 0.008 |
| Variance in adherence (all) | 0.0001 |
| Mean adherence — correct | 1.000 (var=0.0000) |
| Mean adherence — incorrect | 1.000 (var=0.0002) |
| Adherence delta (correct − incorrect) | +0.000 |

### Correlation with Correctness

| Metric | r | p-value | Significance |
|--------|---|---------|--------------|
| Adherence score | 0.0195 | 0.1438 | ns |
| Combined score  | 0.0195 | 0.1438 | ns |
| Response length | -0.1883 | 4.448e-46 | *** |

### Section Presence Rates

| Section | Correct | Incorrect | Δ |
|---------|---------|-----------|---|
| Card Description | 100.0% | 100.0% | +0.0% — |
| Order of Events | 100.0% | 100.0% | +0.0% — |
| Synergy Analysis | 100.0% | 99.9% | +0.1% — |
| Conclusion | 100.0% | 99.9% | +0.1% — |
| Final Score | 100.0% | 99.9% | +0.1% — |

---

## gpt4ominift

| | Value |
|--|--|
| Pairs analyzed | 5,625 |
| Accuracy | 79.4% (4,465 correct / 1,160 wrong) |
| Mean adherence (all) | 1.000 ± 0.004 |
| Variance in adherence (all) | 0.0000 |
| Mean adherence — correct | 1.000 (var=0.0000) |
| Mean adherence — incorrect | 1.000 (var=0.0000) |
| Adherence delta (correct − incorrect) | -0.000 |

### Correlation with Correctness

| Metric | r | p-value | Significance |
|--------|---|---------|--------------|
| Adherence score | -0.0096 | 0.471 | ns |
| Combined score  | -0.0105 | 0.4301 | ns |
| Response length | -0.1931 | 2.115e-48 | *** |

### Section Presence Rates

| Section | Correct | Incorrect | Δ |
|---------|---------|-----------|---|
| Card Description | 100.0% | 100.0% | +0.0% — |
| Order of Events | 100.0% | 100.0% | +0.0% — |
| Synergy Analysis | 100.0% | 100.0% | -0.0% — |
| Conclusion | 100.0% | 100.0% | +0.0% — |
| Final Score | 100.0% | 100.0% | +0.0% — |

---

## gemini3flash

| | Value |
|--|--|
| Pairs analyzed | 5,625 |
| Accuracy | 82.3% (4,628 correct / 997 wrong) |
| Mean adherence (all) | 0.998 ± 0.027 |
| Variance in adherence (all) | 0.0007 |
| Mean adherence — correct | 0.999 (var=0.0004) |
| Mean adherence — incorrect | 0.994 (var=0.0022) |
| Adherence delta (correct − incorrect) | +0.005 |

### Correlation with Correctness

| Metric | r | p-value | Significance |
|--------|---|---------|--------------|
| Adherence score | 0.0690 | 2.213e-07 | *** |
| Combined score  | 0.0800 | 1.902e-09 | *** |
| Response length | -0.2367 | 1.719e-72 | *** |

### Section Presence Rates

| Section | Correct | Incorrect | Δ |
|---------|---------|-----------|---|
| Card Description | 99.9% | 99.1% | +0.8% — |
| Order of Events | 99.7% | 99.1% | +0.6% — |
| Synergy Analysis | 99.9% | 99.6% | +0.3% — |
| Conclusion | 99.9% | 99.1% | +0.8% — |
| Final Score | 100.0% | 100.0% | +0.0% — |

---

---

## Response Length Analysis

Across all models, incorrect predictions have significantly longer responses.
This is a confound: models write more when pairs are harder (true synergies/anti-synergies),
and harder pairs remain hard to classify regardless of response length.


### Cross-Model Summary

| Model | Acc | Mean (correct) | Mean (incorrect) | Diff | r | d | p (MWU) | sig |
|-------|-----|----------------|-----------------|------|---|---|---------|-----|
| gpt4o | 80.5% | 1329 (σ=174) | 1409 (σ=177) | -80 | -0.1786 | -0.458 | 1.15e-40 | *** |
| gpt54 | 80.1% | 804 (σ=222) | 992 (σ=266) | -189 | -0.3101 | -0.817 | 1.7e-106 | *** |
| gemini10pro | 42.9% | 1346 (σ=293) | 1486 (σ=309) | -140 | -0.2236 | -0.463 | 1.69e-72 | *** |
| gemini15flash | 75.5% | 1127 (σ=215) | 1290 (σ=236) | -163 | -0.3031 | -0.739 | 1.41e-97 | *** |
| gpt4omini | 68.1% | 1375 (σ=184) | 1452 (σ=189) | -76 | -0.1883 | -0.411 | 1.19e-45 | *** |
| gpt4ominift | 79.4% | 714 (σ=107) | 768 (σ=124) | -54 | -0.1931 | -0.486 | 1.16e-42 | *** |
| gemini3flash | 82.3% | 1651 (σ=286) | 1836 (σ=310) | -185 | -0.2367 | -0.638 | 1.71e-69 | *** |

### gpt4o — detail

**Length by outcome**

| | Mean | Median | Std |
|--|------|--------|-----|
| Correct   | 1329 | 1318 | 174 |
| Incorrect | 1409 | 1397 | 177 |

- r(length, correct) = **-0.1786**, p=1.54e-41 ***
- Cohen's d = **-0.458** (correct vs incorrect)
- r² = 0.0319 (3.19% variance explained)

**Accuracy by length quartile** (Q1=shortest, Q4=longest)

| Quartile | n | Mean length | Accuracy |
|----------|---|-------------|---------|
| Q1 | 1412 | 1132 | 89.8% |
| Q2 | 1405 | 1277 | 82.7% |
| Q3 | 1404 | 1391 | 79.1% |
| Q4 | 1404 | 1579 | 70.4% |

**Confound check: mean length and accuracy by GT class**

| GT class | n | Mean length | Accuracy |
|----------|---|-------------|---------|
| Anti-syn (-1) | 125 | 1387 | 31.2% |
| Neutral (0) | 4553 | 1339 | 83.8% |
| Synergy (+1) | 947 | 1363 | 71.1% |

### gpt54 — detail

**Length by outcome**

| | Mean | Median | Std |
|--|------|--------|-----|
| Correct   | 804 | 767 | 222 |
| Incorrect | 992 | 958 | 266 |

- r(length, correct) = **-0.3101**, p=1.27e-125 ***
- Cohen's d = **-0.817** (correct vs incorrect)
- r² = 0.0961 (9.61% variance explained)

**Accuracy by length quartile** (Q1=shortest, Q4=longest)

| Quartile | n | Mean length | Accuracy |
|----------|---|-------------|---------|
| Q1 | 1409 | 573 | 92.8% |
| Q2 | 1409 | 731 | 86.3% |
| Q3 | 1402 | 886 | 78.4% |
| Q4 | 1405 | 1176 | 62.9% |

**Confound check: mean length and accuracy by GT class**

| GT class | n | Mean length | Accuracy |
|----------|---|-------------|---------|
| Anti-syn (-1) | 125 | 985 | 34.4% |
| Neutral (0) | 4553 | 825 | 84.1% |
| Synergy (+1) | 947 | 900 | 66.9% |

### gemini10pro — detail

**Length by outcome**

| | Mean | Median | Std |
|--|------|--------|-----|
| Correct   | 1346 | 1307 | 293 |
| Incorrect | 1486 | 1444 | 309 |

- r(length, correct) = **-0.2236**, p=1.08e-64 ***
- Cohen's d = **-0.463** (correct vs incorrect)
- r² = 0.0500 (5.00% variance explained)

**Accuracy by length quartile** (Q1=shortest, Q4=longest)

| Quartile | n | Mean length | Accuracy |
|----------|---|-------------|---------|
| Q1 | 1413 | 1080 | 61.1% |
| Q2 | 1403 | 1300 | 43.4% |
| Q3 | 1405 | 1486 | 38.0% |
| Q4 | 1404 | 1838 | 29.1% |

**Confound check: mean length and accuracy by GT class**

| GT class | n | Mean length | Accuracy |
|----------|---|-------------|---------|
| Anti-syn (-1) | 125 | 1507 | 27.2% |
| Neutral (0) | 4553 | 1422 | 35.6% |
| Synergy (+1) | 947 | 1432 | 80.1% |

### gemini15flash — detail

**Length by outcome**

| | Mean | Median | Std |
|--|------|--------|-----|
| Correct   | 1127 | 1103 | 215 |
| Incorrect | 1290 | 1280 | 236 |

- r(length, correct) = **-0.3031**, p=9.87e-103 ***
- Cohen's d = **-0.739** (correct vs incorrect)
- r² = 0.0918 (9.18% variance explained)

**Accuracy by length quartile** (Q1=shortest, Q4=longest)

| Quartile | n | Mean length | Accuracy |
|----------|---|-------------|---------|
| Q1 | 1209 | 905 | 89.7% |
| Q2 | 1197 | 1071 | 82.2% |
| Q3 | 1202 | 1213 | 76.0% |
| Q4 | 1202 | 1480 | 54.2% |

**Confound check: mean length and accuracy by GT class**

| GT class | n | Mean length | Accuracy |
|----------|---|-------------|---------|
| Anti-syn (-1) | 109 | 1284 | 29.4% |
| Neutral (0) | 3892 | 1150 | 80.4% |
| Synergy (+1) | 809 | 1232 | 58.0% |

### gpt4omini — detail

**Length by outcome**

| | Mean | Median | Std |
|--|------|--------|-----|
| Correct   | 1375 | 1368 | 184 |
| Incorrect | 1452 | 1448 | 189 |

- r(length, correct) = **-0.1883**, p=4.45e-46 ***
- Cohen's d = **-0.411** (correct vs incorrect)
- r² = 0.0355 (3.55% variance explained)

**Accuracy by length quartile** (Q1=shortest, Q4=longest)

| Quartile | n | Mean length | Accuracy |
|----------|---|-------------|---------|
| Q1 | 1412 | 1166 | 78.8% |
| Q2 | 1401 | 1332 | 71.6% |
| Q3 | 1418 | 1457 | 66.1% |
| Q4 | 1394 | 1646 | 55.9% |

**Confound check: mean length and accuracy by GT class**

| GT class | n | Mean length | Accuracy |
|----------|---|-------------|---------|
| Anti-syn (-1) | 125 | 1491 | 22.4% |
| Neutral (0) | 4553 | 1401 | 69.1% |
| Synergy (+1) | 947 | 1378 | 69.3% |

### gpt4ominift — detail

**Length by outcome**

| | Mean | Median | Std |
|--|------|--------|-----|
| Correct   | 714 | 703 | 107 |
| Incorrect | 768 | 757 | 124 |

- r(length, correct) = **-0.1931**, p=2.11e-48 ***
- Cohen's d = **-0.486** (correct vs incorrect)
- r² = 0.0373 (3.73% variance explained)

**Accuracy by length quartile** (Q1=shortest, Q4=longest)

| Quartile | n | Mean length | Accuracy |
|----------|---|-------------|---------|
| Q1 | 1411 | 593 | 87.2% |
| Q2 | 1409 | 680 | 83.8% |
| Q3 | 1399 | 750 | 78.0% |
| Q4 | 1406 | 876 | 68.4% |

**Confound check: mean length and accuracy by GT class**

| GT class | n | Mean length | Accuracy |
|----------|---|-------------|---------|
| Anti-syn (-1) | 125 | 770 | 16.0% |
| Neutral (0) | 4553 | 720 | 86.8% |
| Synergy (+1) | 947 | 743 | 52.2% |

### gemini3flash — detail

**Length by outcome**

| | Mean | Median | Std |
|--|------|--------|-----|
| Correct   | 1651 | 1602 | 286 |
| Incorrect | 1836 | 1783 | 310 |

- r(length, correct) = **-0.2367**, p=1.72e-72 ***
- Cohen's d = **-0.638** (correct vs incorrect)
- r² = 0.0560 (5.60% variance explained)

**Accuracy by length quartile** (Q1=shortest, Q4=longest)

| Quartile | n | Mean length | Accuracy |
|----------|---|-------------|---------|
| Q1 | 1408 | 1353 | 93.5% |
| Q2 | 1406 | 1553 | 86.3% |
| Q3 | 1405 | 1733 | 80.1% |
| Q4 | 1406 | 2097 | 69.3% |

**Confound check: mean length and accuracy by GT class**

| GT class | n | Mean length | Accuracy |
|----------|---|-------------|---------|
| Anti-syn (-1) | 125 | 1832 | 48.0% |
| Neutral (0) | 4553 | 1677 | 84.5% |
| Synergy (+1) | 947 | 1698 | 76.0% |

---

*Length analysis generated by `length_analysis.py`*
