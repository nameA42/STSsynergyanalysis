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
