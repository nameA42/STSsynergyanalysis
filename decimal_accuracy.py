#!/usr/bin/env python3
"""
decimal_accuracy.py
===================
Measures model accuracy on pairs split by their decimal ground-truth rating.

The decimal GT uses a finer scale (-2 to +2 in 0.5 steps) vs the 3-class
integer labels (-1, 0, +1) that models predict. This lets us ask:
  - How well do models classify pairs that are *borderline* (0.5, -0.5)?
  - Do they do better on *strong* synergies (1.5, 2.0) vs weak ones (0.5)?
  - Are ambiguous negatives (-0.5) harder to detect than clear ones (-1.0)?

Masks applied:
  positive_half  : decimal GT in {+0.5, +1.5}  → expected prediction +1
  positive_clear : decimal GT in {+1.0, +2.0}  → expected prediction +1
  negative_half  : decimal GT in {-0.5, -1.5}  → expected prediction -1
  negative_clear : decimal GT in {-1.0, -2.0}  → expected prediction -1
  neutral        : decimal GT == 0             → expected prediction  0
  all_positive   : decimal GT >  0             → expected prediction +1
  all_negative   : decimal GT <  0             → expected prediction -1

Usage:
    python decimal_accuracy.py
    python decimal_accuracy.py --output results/
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    classification_report, confusion_matrix,
)

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from lib.loader import (
    load_dataset, get_ground_truth_name, list_model_datasets, load_config,
)

DECIMAL_GT_PATH = ROOT / "data" / "ground_truth_decimals" / "StS Synergies - All Cards (1).csv"

# ── mask definitions ──────────────────────────────────────────────────────────
#   (label, decimal values that belong, integer label models should predict)
MASKS = [
    ("neutral",        [0.0],                  0),
    ("positive_half",  [0.5],                  1),   # borderline synergy
    ("positive_clear", [1.0, 1.5, 2.0],        1),   # definitive synergy (1.5 = as good as 1.0)
    ("all_positive",   [0.5, 1.0, 1.5, 2.0],   1),
    ("negative_half",  [-0.5],                 -1),   # borderline anti-synergy
    ("negative_clear", [-1.0, -1.5, -2.0],    -1),   # definitive anti-synergy
    ("all_negative",   [-0.5, -1.0, -1.5, -2.0], -1),
]

# ── helpers ───────────────────────────────────────────────────────────────────

def load_decimal_gt(gt_index) -> pd.DataFrame:
    df = pd.read_csv(DECIMAL_GT_PATH, index_col=0)
    # Filter to the 75 cards used in model predictions
    common_rows = df.index.intersection(gt_index)
    common_cols = df.columns.intersection(gt_index)
    return df.loc[common_rows, common_cols]


def mask_pairs(dec_gt: pd.DataFrame, values: list[float]) -> pd.DataFrame:
    """Return boolean mask DataFrame — True where dec_gt value is in `values`."""
    return dec_gt.isin(values)


def flatten_with_mask(
    int_gt: pd.DataFrame, pred_df: pd.DataFrame, mask: pd.DataFrame
) -> tuple[np.ndarray, np.ndarray]:
    """
    Return (y_true, y_pred) for all pairs where mask is True.
    y_true comes from the real integer GT (-1/0/+1), not the decimal GT.
    The decimal GT is used only to select which pairs enter the mask.
    """
    rows, cols = np.where(mask.values)
    y_true = np.array([int_gt.iloc[r, c] for r, c in zip(rows, cols)])
    y_pred = np.array([pred_df.iloc[r, c] for r, c in zip(rows, cols)])
    return y_true, y_pred


def stats_for_mask(y_true: np.ndarray, y_pred: np.ndarray, expected_label: int) -> dict:
    """Compute accuracy + per-class and macro metrics for a mask subset."""
    if len(y_true) == 0:
        return {"n": 0}

    # Binary view: did model predict the expected label?
    correct = (y_pred == expected_label)
    acc     = correct.mean()

    # Full sklearn metrics (handles the actual label distribution)
    labels = sorted(set(y_true.tolist()) | set(y_pred.tolist()))

    prec_macro = precision_score(y_true, y_pred, labels=labels,
                                 average="macro", zero_division=0)
    rec_macro  = recall_score(y_true, y_pred, labels=labels,
                              average="macro", zero_division=0)
    f1_macro   = f1_score(y_true, y_pred, labels=labels,
                          average="macro", zero_division=0)

    # Per-class F1 for the expected label specifically
    f1_target = f1_score(y_true, y_pred, labels=[expected_label],
                         average="macro", zero_division=0)
    prec_target = precision_score(y_true, y_pred, labels=[expected_label],
                                  average="macro", zero_division=0)
    rec_target  = recall_score(y_true, y_pred, labels=[expected_label],
                               average="macro", zero_division=0)

    # Prediction distribution (what did the model actually predict?)
    pred_dist = {int(v): int((y_pred == v).sum()) for v in [-1, 0, 1]}

    return {
        "n":           len(y_true),
        "acc":         acc,
        "prec_macro":  prec_macro,
        "rec_macro":   rec_macro,
        "f1_macro":    f1_macro,
        "prec_target": prec_target,
        "rec_target":  rec_target,
        "f1_target":   f1_target,
        "pred_dist":   pred_dist,
    }


# ── figures ───────────────────────────────────────────────────────────────────

def fig_accuracy_heatmap(all_results: dict, output_dir: Path):
    """Grid: models × masks, cell = accuracy on that mask."""
    models     = list(all_results.keys())
    mask_names = [m[0] for m in MASKS]
    data = np.full((len(models), len(mask_names)), np.nan)

    for i, model in enumerate(models):
        for j, mname in enumerate(mask_names):
            r = all_results[model].get(mname, {})
            if r.get("n", 0) > 0:
                data[i, j] = r["acc"] * 100

    fig, ax = plt.subplots(figsize=(max(9, len(mask_names) * 1.4), max(4, len(models) * 0.7)))
    im = ax.imshow(data, aspect="auto", cmap="RdYlGn", vmin=0, vmax=100)
    plt.colorbar(im, ax=ax, label="Accuracy (%)")
    ax.set_xticks(range(len(mask_names)))
    ax.set_xticklabels(mask_names, rotation=35, ha="right", fontsize=9)
    ax.set_yticks(range(len(models)))
    ax.set_yticklabels(models, fontsize=9)
    for i in range(len(models)):
        for j in range(len(mask_names)):
            if not np.isnan(data[i, j]):
                ax.text(j, i, f"{data[i,j]:.1f}%", ha="center", va="center",
                        fontsize=8, color="black" if 30 < data[i,j] < 80 else "white")
    ax.set_title("Accuracy by Decimal GT Mask × Model", fontsize=12, fontweight="bold")
    fig.tight_layout()
    p = output_dir / "dec_fig1_accuracy_heatmap.png"
    fig.savefig(p, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  dec_fig1_accuracy_heatmap.png")


def fig_f1_by_mask(all_results: dict, output_dir: Path):
    """Grouped bar: F1 (target class) per mask, one bar per model."""
    models     = list(all_results.keys())
    # Only non-neutral masks with a meaningful target
    plot_masks = [m for m in MASKS if m[0] != "neutral"]
    mask_names = [m[0] for m in plot_masks]

    x  = np.arange(len(mask_names))
    w  = 0.8 / max(len(models), 1)
    fig, ax = plt.subplots(figsize=(max(10, len(mask_names) * 1.6), 5))
    colors = plt.cm.tab10.colors

    for i, model in enumerate(models):
        vals = []
        for mname, _, _ in plot_masks:
            r = all_results[model].get(mname, {})
            vals.append(r.get("f1_target", 0) * 100 if r.get("n", 0) > 0 else 0)
        offset = (i - len(models) / 2 + 0.5) * w
        ax.bar(x + offset, vals, w * 0.9, label=model, color=colors[i % 10], alpha=0.85)

    ax.set_xticks(x)
    ax.set_xticklabels(mask_names, rotation=25, ha="right", fontsize=9)
    ax.set_ylabel("F1 Score (target class, %)")
    ax.set_title("F1 Score for Target Class by Decimal GT Mask")
    ax.legend(fontsize=8, ncol=3)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    p = output_dir / "dec_fig2_f1_by_mask.png"
    fig.savefig(p, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  dec_fig2_f1_by_mask.png")


def fig_pred_distribution(all_results: dict, output_dir: Path):
    """For each half-value mask, show what the models actually predicted."""
    half_masks = ["positive_half", "negative_half"]
    fig, axes  = plt.subplots(1, 2, figsize=(12, 5))
    models     = list(all_results.keys())
    colors     = plt.cm.tab10.colors
    labels_map = {-1: "Predict −1", 0: "Predict 0", 1: "Predict +1"}

    for ax, mname in zip(axes, half_masks):
        x   = np.arange(len(models))
        w   = 0.25
        for j, pred_val in enumerate([-1, 0, 1]):
            vals = []
            for model in models:
                r  = all_results[model].get(mname, {})
                pd_dist = r.get("pred_dist", {})
                n  = r.get("n", 1) or 1
                vals.append(pd_dist.get(pred_val, 0) / n * 100)
            offset = (j - 1) * w
            ax.bar(x + offset, vals, w * 0.9, label=labels_map[pred_val],
                   color=colors[j + 3], alpha=0.85)

        ax.set_xticks(x)
        ax.set_xticklabels(models, rotation=25, ha="right", fontsize=8)
        ax.set_ylabel("% of pairs predicted as")
        ax.set_title(f"Prediction distribution — {mname}")
        ax.legend(fontsize=8)
        ax.grid(axis="y", alpha=0.3)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0f}%"))

    fig.suptitle("What do models predict for borderline pairs?", fontsize=12, fontweight="bold")
    fig.tight_layout()
    p = output_dir / "dec_fig3_pred_distribution.png"
    fig.savefig(p, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  dec_fig3_pred_distribution.png")


def fig_half_vs_clear(all_results: dict, output_dir: Path):
    """Compare accuracy: half-value pairs vs clear pairs, positive and negative."""
    models   = list(all_results.keys())
    x        = np.arange(len(models))
    w        = 0.2
    colors   = {"positive_half": "#a6e3a1", "positive_clear": "#40a02b",
                "negative_half": "#f38ba8", "negative_clear": "#d20f39"}
    labels   = {"positive_half": "Pos half (0.5,1.5)",
                "positive_clear": "Pos clear (1.0,2.0)",
                "negative_half":  "Neg half (−0.5,−1.5)",
                "negative_clear": "Neg clear (−1.0,−2.0)"}
    order    = ["positive_half", "positive_clear", "negative_half", "negative_clear"]

    fig, ax = plt.subplots(figsize=(max(9, len(models) * 1.5), 5))
    for i, mname in enumerate(order):
        vals   = []
        for model in models:
            r = all_results[model].get(mname, {})
            vals.append(r.get("acc", 0) * 100 if r.get("n", 0) > 0 else 0)
        offset = (i - 1.5) * w
        ax.bar(x + offset, vals, w * 0.9, label=labels[mname],
               color=colors[mname], alpha=0.9)

    ax.set_xticks(x)
    ax.set_xticklabels(models, rotation=20, ha="right", fontsize=9)
    ax.set_ylabel("Accuracy (%)")
    ax.set_title("Half-value vs Clear-value Accuracy (positive & negative)")
    ax.legend(fontsize=8, ncol=2)
    ax.grid(axis="y", alpha=0.3)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    fig.tight_layout()
    p = output_dir / "dec_fig4_half_vs_clear.png"
    fig.savefig(p, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  dec_fig4_half_vs_clear.png")


# ── report ────────────────────────────────────────────────────────────────────

def write_report(all_results: dict, dec_gt: pd.DataFrame, output_dir: Path):
    lines = []
    lines.append("# Decimal Ground Truth Accuracy Analysis\n")
    lines.append(
        "How well do models predict pairs when the ground truth is expressed on\n"
        "a finer decimal scale (−2 to +2 in 0.5 steps) vs the 3-class labels\n"
        "they were trained to produce (−1, 0, +1).\n"
    )

    # Dataset summary
    vals = dec_gt.stack().dropna()
    lines.append("## Decimal GT Value Distribution\n")
    lines.append("| Value | Count | % |")
    lines.append("|-------|-------|---|")
    for v, c in vals.value_counts().sort_index().items():
        lines.append(f"| {v:+.1f} | {c} | {c/len(vals)*100:.1f}% |")
    lines.append("")

    lines.append("## Mask Definitions\n")
    lines.append("| Mask | Decimal GT values | Expected prediction |")
    lines.append("|------|-------------------|---------------------|")
    for mname, mvals, mlabel in MASKS:
        lines.append(f"| `{mname}` | {mvals} | {mlabel:+d} |")
    lines.append("")

    # Cross-model summary per mask
    for mname, mvals, mlabel in MASKS:
        lines.append(f"## Mask: `{mname}`\n")
        n_example = all_results[list(all_results.keys())[0]].get(mname, {}).get("n", 0)
        lines.append(f"Decimal GT values: {mvals} → expected model output: **{mlabel:+d}**  ")
        lines.append(f"Pairs in mask: **{n_example}**\n")
        lines.append("| Model | n | Accuracy | Prec (target) | Recall (target) | F1 (target) | Macro F1 | Pred −1 | Pred 0 | Pred +1 |")
        lines.append("|-------|---|----------|---------------|-----------------|-------------|----------|---------|--------|---------|")
        for model, results in all_results.items():
            r = results.get(mname, {})
            if r.get("n", 0) == 0:
                lines.append(f"| {model} | 0 | — | — | — | — | — | — | — | — |")
                continue
            pd_dist = r.get("pred_dist", {})
            n = r["n"]
            lines.append(
                f"| {model} | {n} "
                f"| {r['acc']*100:.1f}% "
                f"| {r['prec_target']*100:.1f}% "
                f"| {r['rec_target']*100:.1f}% "
                f"| {r['f1_target']*100:.1f}% "
                f"| {r['f1_macro']*100:.1f}% "
                f"| {pd_dist.get(-1,0)} ({pd_dist.get(-1,0)/n*100:.0f}%) "
                f"| {pd_dist.get(0,0)} ({pd_dist.get(0,0)/n*100:.0f}%) "
                f"| {pd_dist.get(1,0)} ({pd_dist.get(1,0)/n*100:.0f}%) |"
            )
        lines.append("")

    # Highlight: half vs clear comparison
    lines.append("## Half-value vs Clear-value Accuracy Summary\n")
    lines.append("| Model | Pos half acc | Pos clear acc | Neg half acc | Neg clear acc |")
    lines.append("|-------|-------------|--------------|-------------|--------------|")
    for model, results in all_results.items():
        ph = results.get("positive_half", {})
        pc = results.get("positive_clear", {})
        nh = results.get("negative_half", {})
        nc = results.get("negative_clear", {})
        lines.append(
            f"| {model} "
            f"| {ph.get('acc',0)*100:.1f}% (n={ph.get('n',0)}) "
            f"| {pc.get('acc',0)*100:.1f}% (n={pc.get('n',0)}) "
            f"| {nh.get('acc',0)*100:.1f}% (n={nh.get('n',0)}) "
            f"| {nc.get('acc',0)*100:.1f}% (n={nc.get('n',0)}) |"
        )
    lines.append("")
    lines.append("---\n")
    lines.append("*Generated by `decimal_accuracy.py`*\n")

    out_path = output_dir / "decimal_report.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  decimal_report.md")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Decimal GT accuracy analysis")
    parser.add_argument("--output", default="adherence_results", metavar="DIR")
    args   = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("  Decimal GT Accuracy Analysis")
    print("=" * 60)

    # Load data
    gt_name  = get_ground_truth_name()
    gt       = load_dataset(gt_name)
    dec_gt   = load_decimal_gt(gt.index)
    models   = list_model_datasets()

    print(f"\nDecimal GT: {dec_gt.shape[0]}×{dec_gt.shape[1]} pairs")
    print(f"Models: {list(models.keys())}\n")

    # Build masks once (boolean DataFrames aligned to dec_gt)
    mask_dfs = {}
    for mname, mvals, _ in MASKS:
        mask_dfs[mname] = mask_pairs(dec_gt, mvals)
        print(f"  {mname:<20}: {mask_dfs[mname].values.sum():5d} pairs")
    print()

    # Analyse each model
    all_results = {}
    for model_name in models:
        print(f"[{model_name}]")
        pred_df = load_dataset(model_name)
        # Align all three DataFrames to the same card ordering
        common       = dec_gt.index.intersection(pred_df.index).intersection(gt.index)
        dec_aligned  = dec_gt.loc[common, common]
        int_aligned  = gt.loc[common, common]        # real integer GT for accuracy
        pred_aligned = pred_df.loc[common, common]

        model_results = {}
        for mname, mvals, mlabel in MASKS:
            mask = mask_pairs(dec_aligned, mvals)
            y_true, y_pred = flatten_with_mask(int_aligned, pred_aligned, mask)
            r = stats_for_mask(y_true, y_pred, mlabel)
            model_results[mname] = r
            if r["n"] > 0:
                print(f"  {mname:<22} n={r['n']:4d}  acc={r['acc']*100:.1f}%"
                      f"  f1_target={r['f1_target']*100:.1f}%"
                      f"  f1_macro={r['f1_macro']*100:.1f}%")
        all_results[model_name] = model_results
        print()

    print("Saving figures...")
    fig_accuracy_heatmap(all_results, output_dir)
    fig_f1_by_mask(all_results, output_dir)
    fig_pred_distribution(all_results, output_dir)
    fig_half_vs_clear(all_results, output_dir)

    print("\nWriting report...")
    write_report(all_results, dec_gt, output_dir)

    # Console summary: half-value pairs (the interesting ones)
    print("\n" + "=" * 60)
    print("  Key result: half-value pairs (most ambiguous)")
    print("=" * 60)
    print(f"  {'Model':<16} {'pos_half acc':>13} {'neg_half acc':>13}")
    print("  " + "-" * 44)
    for model, results in all_results.items():
        ph = results.get("positive_half", {})
        nh = results.get("negative_half", {})
        print(f"  {model:<16}"
              f"  {ph.get('acc',0)*100:>8.1f}% (n={ph.get('n',0):3d})"
              f"  {nh.get('acc',0)*100:>8.1f}% (n={nh.get('n',0):3d})")
    print("=" * 60)
    print(f"\nAll output in: {output_dir}")


if __name__ == "__main__":
    main()
