#!/usr/bin/env python3
"""
edge_case_analysis.py
=====================
Measures model accuracy on hand-curated edge-case pairs, split by their
integer GT label (positive / neutral / negative).

The edge_case mask CSV marks pairs with 1.0 where a pair was considered
an edge case. This script then sub-divides those pairs by their integer
ground truth label and reports accuracy + F1 per model.

Sub-masks:
  edge_positive : edge_case == 1  AND  int_GT == +1
  edge_neutral  : edge_case == 1  AND  int_GT ==  0
  edge_negative : edge_case == 1  AND  int_GT == -1

Usage:
    python edge_case_analysis.py
    python edge_case_analysis.py --output results/
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
from lib.masks import EDGE_MASK_PATH, get_edge_pairs


# ── stats ─────────────────────────────────────────────────────────────────────

def stats_for_pairs(pairs: list, int_gt: pd.DataFrame, pred_df: pd.DataFrame,
                    expected_label: int) -> dict:
    """
    pairs : list of (row_card, col_card)
    expected_label : the int GT label this sub-mask targets (-1 / 0 / +1)
    Accuracy = fraction where model predicted expected_label.
    """
    y_true, y_pred = [], []
    for r, c in pairs:
        if r not in pred_df.index or c not in pred_df.columns:
            continue
        y_true.append(int_gt.loc[r, c])
        y_pred.append(pred_df.loc[r, c])

    if not y_true:
        return {"n": 0}

    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    n = len(y_true)
    labels = sorted(set(y_true.tolist()) | set(y_pred.tolist()))

    acc        = accuracy_score(y_true, y_pred)
    f1_macro   = f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)
    f1_target  = f1_score(y_true, y_pred, labels=[expected_label],
                          average="macro", zero_division=0)
    prec_target = precision_score(y_true, y_pred, labels=[expected_label],
                                  average="macro", zero_division=0)
    rec_target  = recall_score(y_true, y_pred, labels=[expected_label],
                               average="macro", zero_division=0)
    pred_dist  = {int(v): int((y_pred == v).sum()) for v in [-1, 0, 1]}

    return {
        "n": n,
        "acc": acc,
        "f1_macro": f1_macro,
        "f1_target": f1_target,
        "prec_target": prec_target,
        "rec_target": rec_target,
        "pred_dist": pred_dist,
        "y_true": y_true,
        "y_pred": y_pred,
    }


# ── report ────────────────────────────────────────────────────────────────────

def pair_list_table(pairs: list, int_gt: pd.DataFrame) -> list[str]:
    lines = []
    lines.append("| Card A | Card B | Int GT |")
    lines.append("|--------|--------|--------|")
    for r, c in sorted(pairs):
        v = int_gt.loc[r, c]
        lines.append(f"| {r} | {c} | {v:+d} |")
    return lines


def model_table(mask_results: dict, expected_label: int) -> list[str]:
    lines = []
    lines.append("| Model | n | Accuracy | Prec | Recall | F1 (target) | Macro F1 | Pred -1 | Pred 0 | Pred +1 |")
    lines.append("|-------|---|----------|------|--------|-------------|----------|---------|--------|---------|")
    for model, r in mask_results.items():
        if r.get("n", 0) == 0:
            lines.append(f"| {model} | 0 | — | — | — | — | — | — | — | — |")
            continue
        n  = r["n"]
        pd_ = r["pred_dist"]
        lines.append(
            f"| {model} | {n}"
            f" | {r['acc']*100:.1f}%"
            f" | {r['prec_target']*100:.1f}%"
            f" | {r['rec_target']*100:.1f}%"
            f" | {r['f1_target']*100:.1f}%"
            f" | {r['f1_macro']*100:.1f}%"
            f" | {pd_.get(-1,0)} ({pd_.get(-1,0)/n*100:.0f}%)"
            f" | {pd_.get(0,0)} ({pd_.get(0,0)/n*100:.0f}%)"
            f" | {pd_.get(1,0)} ({pd_.get(1,0)/n*100:.0f}%) |"
        )
    return lines


def write_report(
    sub_masks: dict,
    all_model_results: dict,
    int_gt: pd.DataFrame,
    output_dir: Path,
):
    lines = []
    lines.append("# Edge Case Analysis Report\n")
    lines.append(
        "Model accuracy on 77 hand-curated edge-case pairs, sub-divided by their\n"
        "integer ground truth label. Edge cases are pairs where the correct\n"
        "classification is non-obvious, requires deep game knowledge, or involves\n"
        "conditional/context-dependent interactions.\n"
    )
    lines.append(
        "> Accuracy = fraction of pairs where model predicted the correct integer GT label.  \n"
        "> F1 (target) = F1 for the expected class specifically.  \n"
        "> Macro F1 = unweighted average across all classes present in the sub-mask.\n"
    )
    lines.append("")

    meta = {
        "edge_positive": {
            "heading": "## Edge Positive (n={n}) — edge cases where GT = +1",
            "desc": (
                "These are pairs the mask flagged as edge cases that *are* genuine synergies.\n"
                "Models must correctly identify the positive interaction despite the non-obvious\n"
                "or conditional nature of the combo."
            ),
            "expected": +1,
        },
        "edge_neutral": {
            "heading": "## Edge Neutral (n={n}) — edge cases where GT = 0",
            "desc": (
                "Pairs flagged as edge cases that are ultimately neutral.\n"
                "The risk here is false positives — models that over-pattern-match on\n"
                "card interactions may incorrectly predict synergy where there is none."
            ),
            "expected": 0,
        },
        "edge_negative": {
            "heading": "## Edge Negative (n={n}) — edge cases where GT = -1",
            "desc": (
                "Pairs flagged as edge cases that are anti-synergies.\n"
                "Small sample (n=4). Treat results as illustrative only."
            ),
            "expected": -1,
        },
    }

    for mask_name, pairs in sub_masks.items():
        m = meta[mask_name]
        n = len(pairs)
        lines.append(m["heading"].format(n=n))
        lines.append("")
        lines.append(m["desc"])
        lines.append("")

        if n == 0:
            lines.append("*No pairs in this sub-mask.*\n")
            lines.append("---\n")
            continue

        lines.append("### Pair List\n")
        lines.extend(pair_list_table(pairs, int_gt))
        lines.append("")

        lines.append("### Model Performance\n")
        mask_results = {model: r[mask_name] for model, r in all_model_results.items()}
        lines.extend(model_table(mask_results, m["expected"]))
        lines.append("")

        if n < 10:
            lines.append(
                f"> **Warning — small sample (n={n}).** "
                "Aggregate metrics are unreliable; the pair list above is more informative.\n"
            )

        lines.append("---\n")

    # Summary table
    lines.append("## Summary\n")
    lines.append("| Model | Pos acc (n={np}) | Neu acc (n={nn}) | Neg acc (n={nneg}) |".format(
        np=len(sub_masks["edge_positive"]),
        nn=len(sub_masks["edge_neutral"]),
        nneg=len(sub_masks["edge_negative"]),
    ))
    lines.append("|-------|-----------------|-----------------|-----------------|")
    for model, mr in all_model_results.items():
        rp = mr["edge_positive"]
        rn = mr["edge_neutral"]
        rng = mr["edge_negative"]
        def fmt(r):
            return f"{r['acc']*100:.1f}%" if r.get("n", 0) > 0 else "—"
        lines.append(f"| {model} | {fmt(rp)} | {fmt(rn)} | {fmt(rng)} |")
    lines.append("")
    lines.append("---\n")
    lines.append("*Generated by `edge_case_analysis.py`*\n")

    out = output_dir / "edge_case_report.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"  edge_case_report.md -> {out}")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Edge case accuracy analysis")
    parser.add_argument("--output", default="adherence_results", metavar="DIR")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("  Edge Case Analysis")
    print("=" * 60)

    from lib.masks import DECIMAL_GT_PATH, load_and_align
    gt_name = get_ground_truth_name()
    gt = load_dataset(gt_name)
    models = list_model_datasets()

    gt_aligned, _, mask_aligned, common = load_and_align(gt, DECIMAL_GT_PATH, EDGE_MASK_PATH)

    # Build sub-masks using get_edge_pairs
    all_edge = get_edge_pairs(mask_aligned)
    sub_masks = {"edge_positive": [], "edge_neutral": [], "edge_negative": []}
    for r, c in all_edge:
        v = gt_aligned.loc[r, c]
        if v == 1:
            sub_masks["edge_positive"].append((r, c))
        elif v == 0:
            sub_masks["edge_neutral"].append((r, c))
        elif v == -1:
            sub_masks["edge_negative"].append((r, c))

    for k, pairs in sub_masks.items():
        print(f"  {k}: {len(pairs)} pairs")
    print()

    # Per-model stats
    all_model_results = {}
    for model_name in models:
        pred_df = load_dataset(model_name)
        pred_aligned = pred_df.loc[common, common]

        model_r = {}
        for mask_name, pairs in sub_masks.items():
            expected = {"edge_positive": 1, "edge_neutral": 0, "edge_negative": -1}[mask_name]
            r = stats_for_pairs(pairs, gt_aligned, pred_aligned, expected)
            model_r[mask_name] = r
        all_model_results[model_name] = model_r

    # Print console summary
    for mask_name in sub_masks:
        expected = {"edge_positive": 1, "edge_neutral": 0, "edge_negative": -1}[mask_name]
        n = len(sub_masks[mask_name])
        print(f"[{mask_name}]  n={n}")
        print(f"  {'Model':<16} {'Acc':>8} {'F1 target':>11} {'MacroF1':>10}")
        print("  " + "-" * 50)
        for model, mr in all_model_results.items():
            r = mr[mask_name]
            if r.get("n", 0) == 0:
                print(f"  {model:<16}  {'—':>8}  {'—':>11}  {'—':>10}")
            else:
                print(f"  {model:<16}  {r['acc']*100:>7.1f}%  "
                      f"{r['f1_target']*100:>10.1f}%  "
                      f"{r['f1_macro']*100:>9.1f}%")
        print()

    print("Writing report...")
    write_report(sub_masks, all_model_results, gt_aligned, output_dir)
    print(f"\nDone. Output in: {output_dir}")


if __name__ == "__main__":
    main()
