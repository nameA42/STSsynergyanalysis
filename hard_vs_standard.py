#!/usr/bin/env python3
"""
hard_vs_standard.py
===================
Runs the 5-mask comparison across all models and writes a report.

Five masks (from lib/masks.py):
  all            : every pair (n=5625)
  hard           : edge-case pairs + uncertain pairs (decimal/integer GT sign flip)
  standard       : all - hard
  light_hard     : pairs touching specified rows/cols - hard
  light_standard : all - hard - light_hard

Usage:
    python hard_vs_standard.py
    python hard_vs_standard.py --output results/
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from lib.loader import load_dataset, get_ground_truth_name, list_model_datasets
from lib.masks import (
    DECIMAL_GT_PATH, EDGE_MASK_PATH, load_and_align, build_all_masks,
    LIGHT_HARD_ROWS, LIGHT_HARD_COLS,
)

MASK_ORDER = ["all", "hard", "standard", "light_hard", "light_standard"]
MASK_LABELS = {
    "all":            "All",
    "hard":           "Hard",
    "standard":       "Standard",
    "light_hard":     "Light Hard",
    "light_standard": "Light Standard",
}


# ── stats ─────────────────────────────────────────────────────────────────────

def run_mask(pair_set: set, int_gt: pd.DataFrame, pred_df: pd.DataFrame) -> dict:
    yt, yp = [], []
    for r, c in pair_set:
        yt.append(int_gt.loc[r, c])
        yp.append(pred_df.loc[r, c])
    yt = np.array(yt)
    yp = np.array(yp)
    acc  = accuracy_score(yt, yp)
    f1m  = f1_score(yt, yp, labels=[-1, 0, 1], average="macro", zero_division=0)
    f1s  = f1_score(yt, yp, labels=[-1, 0, 1], average=None,    zero_division=0)
    return {"n": len(yt), "acc": acc, "f1_macro": f1m,
            "f1_neg": f1s[0], "f1_neu": f1s[1], "f1_pos": f1s[2]}


# ── report ────────────────────────────────────────────────────────────────────

def mask_table(results: dict, mask_key: str, n: int) -> list[str]:
    """Full stats table for one mask across all models."""
    lines = []
    lines.append(f"| Model | n | Accuracy | Macro F1 | F1(−1) | F1(0) | F1(+1) |")
    lines.append(f"|-------|---|----------|----------|--------|-------|--------|")
    for model, mr in results.items():
        r = mr[mask_key]
        lines.append(
            f"| {model} | {r['n']}"
            f" | {r['acc']*100:.1f}%"
            f" | {r['f1_macro']*100:.1f}%"
            f" | {r['f1_neg']*100:.1f}%"
            f" | {r['f1_neu']*100:.1f}%"
            f" | {r['f1_pos']*100:.1f}% |"
        )
    return lines


def summary_table(results: dict, mask_sizes: dict) -> list[str]:
    """Compact Acc / MacroF1 table for all 5 masks side by side."""
    lines = []
    header = f"| {'Model':<16} |"
    for k in MASK_ORDER:
        label = f"{MASK_LABELS[k]} (n={mask_sizes[k]})"
        header += f" {label:^21} |"
    lines.append(header)

    sep = f"|{'':-<18}|"
    for _ in MASK_ORDER:
        sep += f"{'':-^23}|"
    lines.append(sep)

    subhdr = f"| {'':16} |"
    for _ in MASK_ORDER:
        subhdr += f" {'Acc':>10} {'MacF1':>9} |"
    lines.append(subhdr)
    lines.append(sep)

    for model, mr in results.items():
        row = f"| {model:<16} |"
        for k in MASK_ORDER:
            r = mr[k]
            row += f" {r['acc']*100:>9.1f}% {r['f1_macro']*100:>8.1f}% |"
        lines.append(row)
    return lines


def write_report(results: dict, masks: dict, int_gt: pd.DataFrame, output_dir: Path):
    mask_sizes = {k: len(masks[k]) for k in MASK_ORDER}
    edge_pairs = masks["_edge_pairs"]
    uncertain  = masks["_uncertain"]

    lines = []
    lines.append("# Five-Mask Comparison Report\n")
    lines.append(
        "Model accuracy across five pair-set masks of increasing difficulty/specificity.\n\n"
        f"**Hard** = edge-case pairs (hand-curated, n={len(edge_pairs)}) "
        f"+ uncertain pairs (decimal/integer GT sign flip, n={len(uncertain)}, "
        f"overlap={len(edge_pairs & uncertain)})  \n"
        f"**Light Hard** = pairs where row ∈ {{{', '.join(sorted(LIGHT_HARD_ROWS))}}} "
        f"or col ∈ {{{', '.join(sorted(LIGHT_HARD_COLS))}}} — minus hard  \n"
        f"**Standard** = all − hard  \n"
        f"**Light Standard** = all − hard − light hard  \n"
    )
    lines.append("")

    # Summary table
    lines.append("## Summary: Accuracy and Macro F1\n")
    lines.extend(summary_table(results, mask_sizes))
    lines.append("")
    lines.append("---\n")

    # Per-mask detail
    MASK_DESCS = {
        "all": "Every pair in the 75×75 matrix.",
        "hard": (
            "Edge-case pairs (hand-curated as non-obvious) plus uncertain pairs "
            "(where decimal GT and integer GT sign disagree). "
            "The most challenging subset."
        ),
        "standard": "All pairs not in the hard set. Represents typical pair difficulty.",
        "light_hard": (
            f"Pairs involving cards in rows {{{', '.join(sorted(LIGHT_HARD_ROWS))}}} "
            f"or columns {{{', '.join(sorted(LIGHT_HARD_COLS))}}}, "
            "after removing the hard set. A mid-tier difficulty band."
        ),
        "light_standard": (
            "All pairs after removing both hard and light hard. "
            "The cleanest, least ambiguous subset."
        ),
    }

    for k in MASK_ORDER:
        n = mask_sizes[k]
        lines.append(f"## {MASK_LABELS[k]} (n={n})\n")
        lines.append(MASK_DESCS[k])
        lines.append("")
        lines.extend(mask_table(results, k, n))
        lines.append("")
        lines.append("---\n")

    # Delta tables: each mask vs all
    lines.append("## Deltas vs All\n")
    lines.append(
        "How much each mask deviates from the full-dataset baseline (positive = better than all).\n"
    )
    for k in MASK_ORDER[1:]:  # skip 'all'
        n = mask_sizes[k]
        lines.append(f"### {MASK_LABELS[k]} minus All\n")
        lines.append(f"| Model | dAcc | dMacroF1 | dF1(−1) | dF1(0) | dF1(+1) |")
        lines.append(f"|-------|------|----------|---------|--------|---------|")
        for model, mr in results.items():
            a = mr["all"]
            b = mr[k]
            lines.append(
                f"| {model}"
                f" | {(b['acc']-a['acc'])*100:+.2f}pp"
                f" | {(b['f1_macro']-a['f1_macro'])*100:+.2f}pp"
                f" | {(b['f1_neg']-a['f1_neg'])*100:+.2f}pp"
                f" | {(b['f1_neu']-a['f1_neu'])*100:+.2f}pp"
                f" | {(b['f1_pos']-a['f1_pos'])*100:+.2f}pp |"
            )
        lines.append("")

    lines.append("---\n")
    lines.append("*Generated by `hard_vs_standard.py`*\n")

    out = output_dir / "hard_vs_standard_report.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"  hard_vs_standard_report.md -> {out}")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Five-mask comparison")
    parser.add_argument("--output", default="adherence_results", metavar="DIR")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("  Five-Mask Comparison")
    print("=" * 60)

    gt_name = get_ground_truth_name()
    gt      = load_dataset(gt_name)
    models  = list_model_datasets()

    gt_aligned, dec_aligned, em_aligned, common = load_and_align(
        gt, DECIMAL_GT_PATH, EDGE_MASK_PATH
    )

    masks = build_all_masks(gt_aligned, dec_aligned, em_aligned)

    print(f"\nCommon cards: {len(common)}")
    for k in MASK_ORDER:
        print(f"  {k:<16}: {len(masks[k])} pairs")
    print()

    all_results = {}
    for model_name in models:
        pred = load_dataset(model_name).loc[common, common]
        all_results[model_name] = {
            k: run_mask(masks[k], gt_aligned, pred) for k in MASK_ORDER
        }

    # Console summary
    hdr = f"{'Model':<16} {'ALL':>9} {'HARD':>9} {'STD':>9} {'LGT HRD':>9} {'LGT STD':>9}"
    print(f"{'':16} {'Acc / MacF1':^55}")
    print(hdr)
    print("-" * 62)
    for model, mr in all_results.items():
        row = f"{model:<16}"
        for k in MASK_ORDER:
            r = mr[k]
            row += f"  {r['acc']*100:4.1f}/{r['f1_macro']*100:4.1f}"
        print(row)

    print("\nWriting report...")
    write_report(all_results, masks, gt_aligned, output_dir)
    print(f"\nDone. Output in: {output_dir}")


if __name__ == "__main__":
    main()
