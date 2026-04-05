#!/usr/bin/env python3
"""
uncertain_cards.py
==================
Finds pairs where the decimal GT and integer GT disagree in direction
(i.e. raters flipped the sign during consensus), then measures model
accuracy on those conflicted pairs.

Two masks:
  half_flipped   : decimal ±0.5 → integer GT is the opposite sign
                   (dec +0.5 → int -1, or dec -0.5 → int +1)
  solid_flipped  : decimal ±1.0/±1.5/±2.0 → integer GT is the opposite sign

For each mask the script:
  1. Lists every pair by card name + decimal/integer GT values
  2. Shows model accuracy / F1 on those pairs
  3. Writes adherence_results/uncertain_cards_report.md

Usage:
    python uncertain_cards.py
    python uncertain_cards.py --output results/
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from lib.loader import load_dataset, get_ground_truth_name, list_model_datasets

DECIMAL_GT_PATH = (
    ROOT / "data" / "ground_truth_decimals" / "StS Synergies - All Cards (1).csv"
)


# ── data loading ──────────────────────────────────────────────────────────────

def load_decimal_gt(common_index) -> pd.DataFrame:
    df = pd.read_csv(DECIMAL_GT_PATH, index_col=0)
    shared = df.index.intersection(common_index)
    return df.loc[shared, shared]


# ── mask logic ────────────────────────────────────────────────────────────────

def find_flipped_pairs(dec_gt: pd.DataFrame, int_gt: pd.DataFrame) -> dict:
    """
    Return two dicts of {(row_card, col_card): (dec_val, int_val)} for:
      half_flipped  : dec in {+0.5, -0.5}, int sign != dec sign
      solid_flipped : dec in {+1, +1.5, +2, -1, -1.5, -2}, int sign != dec sign

    'Opposite sign' means dec_val and int_val have opposite non-zero signs.
    dec=0 is excluded (neutral has no direction to flip from).
    """
    half_vals  = {0.5, -0.5}
    solid_vals = {1.0, 1.5, 2.0, -1.0, -1.5, -2.0}

    half_flipped  = {}
    solid_flipped = {}

    cards = dec_gt.index.tolist()
    for r_card in cards:
        for c_card in cards:
            if r_card not in int_gt.index or c_card not in int_gt.columns:
                continue
            dec_val = dec_gt.loc[r_card, c_card]
            int_val = int_gt.loc[r_card, c_card]

            if pd.isna(dec_val):
                continue

            # Opposite sign: one is positive, the other is negative
            dec_sign = np.sign(dec_val)
            int_sign = np.sign(int_val)
            # "Flipped" means strictly opposite sign (e.g. +0.5 -> -1, not +0.5 -> 0)
            if dec_sign == 0 or int_sign == 0 or int_sign == dec_sign:
                continue  # neutral dec, neutral int, or same direction -> not flipped

            key = (r_card, c_card)
            if dec_val in half_vals:
                half_flipped[key] = (dec_val, int_val)
            elif dec_val in solid_vals:
                solid_flipped[key] = (dec_val, int_val)

    return {"half_flipped": half_flipped, "solid_flipped": solid_flipped}


# ── stats ─────────────────────────────────────────────────────────────────────

def stats_for_pairs(
    pairs: dict,
    int_gt: pd.DataFrame,
    pred_df: pd.DataFrame,
    expected_label_fn,
) -> dict:
    """
    pairs : {(row_card, col_card): (dec_val, int_val)}
    expected_label_fn : callable(int_val) → the label we 'expect' model to predict.
                        We use the INTEGER gt sign as the ground truth for accuracy.
    """
    if not pairs:
        return {"n": 0}

    y_true, y_pred, expected = [], [], []
    for (r, c), (dec_val, int_val) in pairs.items():
        if r not in pred_df.index or c not in pred_df.columns:
            continue
        y_true.append(int_val)
        y_pred.append(pred_df.loc[r, c])
        expected.append(expected_label_fn(int_val))

    y_true = np.array(y_true)
    y_pred = np.array(y_pred)

    n = len(y_true)
    if n == 0:
        return {"n": 0}

    labels = sorted(set(y_true.tolist()) | set(y_pred.tolist()))
    acc = accuracy_score(y_true, y_pred)
    f1_macro = f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)
    pred_dist = {int(v): int((y_pred == v).sum()) for v in [-1, 0, 1]}

    return {
        "n": n,
        "acc": acc,
        "f1_macro": f1_macro,
        "pred_dist": pred_dist,
        "y_true": y_true,
        "y_pred": y_pred,
    }


# ── report ────────────────────────────────────────────────────────────────────

def pair_table(pairs: dict) -> list[str]:
    """Render a markdown table listing all flipped pairs."""
    lines = []
    lines.append("| Card A | Card B | Dec GT | Int GT | Direction |")
    lines.append("|--------|--------|--------|--------|-----------|")
    for (r, c), (dec_val, int_val) in sorted(pairs.items()):
        direction = f"{'pos' if dec_val > 0 else 'neg'} → {'pos' if int_val > 0 else 'neg'}"
        lines.append(f"| {r} | {c} | {dec_val:+.1f} | {int_val:+d} | {direction} |")
    return lines


def model_stats_table(mask_results: dict) -> list[str]:
    lines = []
    lines.append("| Model | n | Accuracy | Macro F1 | Pred −1 | Pred 0 | Pred +1 |")
    lines.append("|-------|---|----------|----------|---------|--------|---------|")
    for model, r in mask_results.items():
        if r.get("n", 0) == 0:
            lines.append(f"| {model} | 0 | — | — | — | — | — |")
            continue
        n  = r["n"]
        pd = r["pred_dist"]
        lines.append(
            f"| {model} | {n} "
            f"| {r['acc']*100:.1f}% "
            f"| {r['f1_macro']*100:.1f}% "
            f"| {pd.get(-1,0)} ({pd.get(-1,0)/n*100:.0f}%) "
            f"| {pd.get(0,0)} ({pd.get(0,0)/n*100:.0f}%) "
            f"| {pd.get(1,0)} ({pd.get(1,0)/n*100:.0f}%) |"
        )
    return lines


def write_report(
    masks: dict,
    all_model_results: dict,
    output_dir: Path,
):
    lines = []
    lines.append("# Uncertain Cards Report\n")
    lines.append(
        "Pairs where the decimal GT and integer GT disagree in *direction* —\n"
        "i.e. the rater consensus flipped the sign during aggregation.\n"
        "These pairs represent genuine annotation uncertainty and are used as\n"
        "a diagnostic lens on model behaviour under ambiguity.\n"
    )
    lines.append(
        "> **Accuracy** and **F1** are computed against the integer GT (the final\n"
        "> consensus label), since that is what models were trained to predict.\n"
        "> The decimal GT determines *which* pairs enter each mask.\n"
    )
    lines.append("")

    for mask_name, pairs in masks.items():
        n_pairs = len(pairs)
        if mask_name == "half_flipped":
            heading  = "## Mask: `half_flipped`"
            desc     = (
                "Decimal GT = ±0.5 (borderline), but the integer consensus GT\n"
                "went to the **opposite sign** (e.g. decimal +0.5 → integer −1).\n"
                "These are pairs where raters leaned one way individually but the\n"
                "final vote reversed direction."
            )
        else:
            heading  = "## Mask: `solid_flipped`"
            desc     = (
                "Decimal GT = ±1.0/±1.5/±2.0 (clear/strong), but the integer\n"
                "consensus GT went to the **opposite sign**.\n"
                "These are the most surprising mismatches: pairs that scored\n"
                "clearly in one direction on the decimal scale but were labelled\n"
                "the other way in the final integer GT."
            )

        lines.append(heading)
        lines.append("")
        lines.append(desc)
        lines.append(f"\n**Total pairs: {n_pairs}**\n")

        if n_pairs == 0:
            lines.append("*No pairs matched this mask.*\n")
        else:
            lines.append("### Pair List\n")
            lines.extend(pair_table(pairs))
            lines.append("")

            lines.append("### Model Accuracy on These Pairs\n")
            mask_results = {m: r[mask_name] for m, r in all_model_results.items()}
            lines.extend(model_stats_table(mask_results))
            lines.append("")

            lines.append("### Notes\n")
            if n_pairs < 20:
                lines.append(
                    f"> ⚠ Small sample (n={n_pairs}). Treat accuracy figures as illustrative,\n"
                    "> not statistically reliable. Individual pair results shown above are\n"
                    "> more informative than aggregate metrics here.\n"
                )
            else:
                lines.append(
                    f"> n={n_pairs}. Results are more reliable than the half-flipped mask\n"
                    "> but still a small slice of the full dataset.\n"
                )

        lines.append("---\n")

    lines.append("*Generated by `uncertain_cards.py`*\n")

    out = output_dir / "uncertain_cards_report.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"  uncertain_cards_report.md -> {out}")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Uncertain cards analysis")
    parser.add_argument("--output", default="adherence_results", metavar="DIR")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("  Uncertain Cards Analysis")
    print("=" * 60)

    gt_name  = get_ground_truth_name()
    gt       = load_dataset(gt_name)
    dec_gt   = load_decimal_gt(gt.index)
    models   = list_model_datasets()

    # Align both GTs to common cards
    common      = dec_gt.index.intersection(gt.index)
    dec_aligned = dec_gt.loc[common, common]
    int_aligned = gt.loc[common, common]

    print(f"\nCommon cards: {len(common)}")
    print(f"Models: {list(models.keys())}\n")

    # Find flipped pairs
    masks = find_flipped_pairs(dec_aligned, int_aligned)

    for mask_name, pairs in masks.items():
        print(f"  {mask_name}: {len(pairs)} pairs")
        for (r, c), (dec_val, int_val) in sorted(pairs.items()):
            print(f"    [{dec_val:+.1f} -> {int_val:+d}]  {r}  x  {c}")
    print()

    # Per-model stats for each mask
    all_model_results = {}
    for model_name in models:
        pred_df = load_dataset(model_name)
        pred_aligned = pred_df.loc[common, common]

        model_r = {}
        for mask_name, pairs in masks.items():
            r = stats_for_pairs(
                pairs,
                int_aligned,
                pred_aligned,
                expected_label_fn=lambda v: int(np.sign(v)),
            )
            model_r[mask_name] = r
        all_model_results[model_name] = model_r

    # Print summary
    for mask_name in masks:
        print(f"\n[{mask_name}]")
        print(f"  {'Model':<16} {'Acc':>8} {'MacroF1':>10}")
        print("  " + "-" * 38)
        for model, mr in all_model_results.items():
            r = mr[mask_name]
            if r["n"] == 0:
                print(f"  {model:<16}  {'—':>8}  {'—':>10}")
            else:
                print(f"  {model:<16}  {r['acc']*100:>7.1f}%  {r['f1_macro']*100:>9.1f}%")

    print("\nWriting report...")
    write_report(masks, all_model_results, output_dir)
    print(f"\nDone. Output in: {output_dir}")


if __name__ == "__main__":
    main()
