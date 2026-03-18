# STS Synergy Analysis

Interactive analysis suite for evaluating LLM card synergy predictions against human-annotated ground truth, built for the Slay the Spire synergy paper.

## What it does

Compares multiple LLM model predictions across the full 75×75 Iron Clad card synergy matrix (5,550 directed pairs, 3-class: −1 anti-synergy, 0 neutral, +1 synergy).

**Analyze** — per-model accuracy, F1, confusion matrix, synergy/error heatmaps, per-card accuracy broken down by Card A and Card B role

**Browse** — filter all 5,550 pairs by ground truth, per-model correctness (correct / wrong / under / over), and per-model predicted value; sortable columns including a "number of models correct" sort

**Compare** — side-by-side metrics, per-card accuracy, agreement heatmap, and delta charts for any combination of models

**Annotate** — add notes and tags to individual card pairs, exportable as CSV

## Datasets

Results live in `data/` (one subfolder per model run). Register new datasets in `datasets.json` and rebuild.

Current models: GPT-4o, GPT-5.4, GPT-4o-mini, GPT-4o-mini (fine-tuned), Gemini 1.0 Pro, Gemini 1.5 Flash

## Running locally

```bash
pip install -r requirements.txt
python web.py
```

Opens at `http://localhost:5000`.

## Static site (GitHub Pages)

```bash
python build.py
git add docs/
git commit -m "rebuild"
git push
```

Configure Pages to serve from `/docs`. Live at `https://<user>.github.io/<repo>/`.

> Annotations on the static site use browser localStorage. Export JSON to persist them across sessions.

## Adding a new model

1. Drop the results CSV (and optionally log) into `data/<model-name>/`
2. Add an entry to `datasets.json`
3. Run `python build.py` and push
