#!/usr/bin/env python
"""
STS Synergy Comparison -- Side-by-side analysis of multiple datasets.

Usage:
    python compare.py                     # interactive selection
    python compare.py gpt4o gpt54         # compare two datasets
    python compare.py --all               # compare every model dataset
    python compare.py gpt4o gpt54 --no-plots
"""

import sys
import argparse
from pathlib import Path

import pandas as pd
import numpy as np

# Force UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).parent))

from lib.loader import (
    load_dataset, list_model_datasets, get_ground_truth_name, load_all_model_datasets
)
from lib import metrics as M
from lib import plots as P


# -- printing helpers ----------------------------------------------------------

def _sep(w=60): return "-" * w

def _header(text):
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}")

def _section(text):
    print(f"\n  {text}")
    print(f"  {_sep()}")


def print_metrics_table(names: list[str], metrics_dict: dict):
    col_w = max(12, max(len(n) for n in names) + 2)
    _section("METRICS SUMMARY")

    keys = ["accuracy", "macro_f1", "weighted_f1", "macro_precision", "macro_recall"]
    labels = ["Accuracy", "Macro F1", "Weighted F1", "Macro Prec.", "Macro Rec."]

    header = f"  {'Metric':<20}" + "".join(f"{n:>{col_w}}" for n in names)
    if len(names) == 2:
        header += f"  {'D (2nd-1st)':>12}"
    print(header)
    print(f"  {'-'*20}" + "-" * col_w * len(names) + ("  " + "-"*12 if len(names)==2 else ""))

    for key, label in zip(keys, labels):
        vals = [metrics_dict[n][key] for n in names]
        if key == "accuracy":
            row = f"  {label:<20}" + "".join(f"{v*100:>{col_w}.2f}%" for v in vals)
        else:
            row = f"  {label:<20}" + "".join(f"{v:>{col_w}.4f}" for v in vals)
        if len(names) == 2:
            delta = vals[1] - vals[0]
            sign = "+" if delta >= 0 else ""
            row += f"  {sign}{delta:>+.4f}"
        print(row)


def print_per_class_f1(names: list[str], metrics_dict: dict):
    col_w = max(12, max(len(n) for n in names) + 2)
    _section("PER-CLASS F1 SCORES")

    header = f"  {'Class':<16}" + "".join(f"{n:>{col_w}}" for n in names)
    if len(names) == 2:
        header += f"  {'D':>8}"
    print(header)
    print(f"  {'-'*16}" + "-" * col_w * len(names))

    for lbl in [-1, 0, 1]:
        vals = [metrics_dict[n]["per_class"][lbl]["f1"] for n in names]
        row = f"  {M.LABEL_NAMES[lbl]:<16}" + "".join(f"{v:>{col_w}.4f}" for v in vals)
        if len(names) == 2:
            delta = vals[1] - vals[0]
            row += f"  {delta:>+8.4f}"
        print(row)


def print_agreement(names: list[str], agreement: dict):
    _section("INTER-DATASET AGREEMENT")
    print(f"  Agreement rate:         {agreement['agreement_rate']*100:.2f}%")
    if "both_correct" in agreement:
        print(f"  Both correct:           {agreement['both_correct']*100:.2f}%")
        print(f"  Both wrong:             {agreement['both_wrong']*100:.2f}%")
        print(f"  Only '{names[0]}' correct:  {agreement['only_first_correct']*100:.2f}%")
        print(f"  Only '{names[1]}' correct:  {agreement['only_second_correct']*100:.2f}%")


def print_per_card_delta(names: list[str], pc_dfs: dict):
    if len(names) != 2:
        return
    n1, n2 = names
    delta = (pc_dfs[n2]["accuracy"] - pc_dfs[n1]["accuracy"]) * 100

    _section(f"MOST IMPROVED CARDS  ({n1} ->{n2})")
    top = delta.sort_values(ascending=False).head(10)
    for card, d in top.items():
        a1 = pc_dfs[n1].loc[card, "accuracy"] * 100
        a2 = pc_dfs[n2].loc[card, "accuracy"] * 100
        bar = "^" if d > 0 else "v"
        print(f"  {card:<25}  {a1:.1f}% ->{a2:.1f}%  ({bar} {abs(d):.1f}%)")

    _section(f"MOST DEGRADED CARDS  ({n1} ->{n2})")
    bottom = delta.sort_values().head(10)
    for card, d in bottom.items():
        a1 = pc_dfs[n1].loc[card, "accuracy"] * 100
        a2 = pc_dfs[n2].loc[card, "accuracy"] * 100
        bar = "v"
        print(f"  {card:<25}  {a1:.1f}% ->{a2:.1f}%  ({bar} {abs(d):.1f}%)")


def print_disagreement_stats(names: list[str], datasets: dict, truth_df):
    """Show pairs where models disagree and who is right."""
    if len(names) != 2:
        return
    n1, n2 = names
    pairs = M.pair_table(datasets[n1], truth_df,
                         extra={n2: datasets[n2]}, exclude_diag=True)

    disagree = pairs[pairs["predicted"] != pairs[f"pred_{n2}"]].copy()
    total = len(pairs)
    n_dis = len(disagree)
    print(f"\n  Pairs where {n1} and {n2} disagree: {n_dis:,} / {total:,} "
          f"({n_dis/total*100:.1f}%)")

    # Who's right when they disagree?
    dis_n1_right = disagree[disagree["predicted"] == disagree["ground_truth"]]
    dis_n2_right = disagree[disagree[f"pred_{n2}"] == disagree["ground_truth"]]
    dis_both_wrong = disagree[
        (disagree["predicted"] != disagree["ground_truth"]) &
        (disagree[f"pred_{n2}"] != disagree["ground_truth"])
    ]
    print(f"  Of those, {n1} is right:   {len(dis_n1_right):,}")
    print(f"  Of those, {n2} is right:   {len(dis_n2_right):,}")
    print(f"  Both wrong:               {len(dis_both_wrong):,}")


# -- dataset selection menu ----------------------------------------------------

def select_datasets() -> list[str]:
    models = list_model_datasets()
    if len(models) < 2:
        print("Need at least 2 model datasets in datasets.json.")
        return []

    print("\nAvailable datasets:")
    items = list(models.items())
    for i, (name, info) in enumerate(items, 1):
        print(f"  [{i}] {name:<20}  {info.get('description', '')}")
    print("\nEnter numbers or names to compare (e.g.  1 2  or  gpt4o gpt54):")

    raw = input("> ").strip().split()
    selected = []
    for token in raw:
        if token.isdigit():
            idx = int(token) - 1
            if 0 <= idx < len(items):
                selected.append(items[idx][0])
        elif token in models:
            selected.append(token)

    if len(selected) < 2:
        print("  Need at least 2 valid datasets.")
        return []
    return selected


# -- main logic ----------------------------------------------------------------

def run(names: list[str], make_plots: bool = True):
    gt_name = get_ground_truth_name()
    print(f"\nLoading {len(names)} datasets...")
    truth = load_dataset(gt_name)
    datasets = {n: load_dataset(n) for n in names}

    print("Computing metrics...")
    metrics_dict = {n: M.overall(ds, truth) for n, ds in datasets.items()}
    pc_dfs       = {n: M.per_card(ds, truth) for n, ds in datasets.items()}

    agreement = {}
    if len(names) == 2:
        agreement = M.compute_agreement(datasets[names[0]], datasets[names[1]], truth)

    label = "_vs_".join(names)
    _header(f"COMPARISON  .  {label.upper().replace('_VS_', ' vs ')}")

    print_metrics_table(names, metrics_dict)
    print_per_class_f1(names, metrics_dict)
    if agreement:
        print_agreement(names, agreement)
    print_per_card_delta(names, pc_dfs)
    print_disagreement_stats(names, datasets, truth)

    if make_plots:
        outdir = Path("outputs") / f"compare_{label}"
        outdir.mkdir(parents=True, exist_ok=True)
        print(f"\n  Generating plots ->outputs/compare_{label}/")

        P.metrics_comparison_bar(metrics_dict, f"Metrics Comparison", outdir)
        print("    OK  metrics_comparison.png")

        P.per_card_comparison(pc_dfs, "Per-Card Accuracy Comparison", outdir)
        print("    OK  per_card_comparison.png")

        P.agreement_heatmap(datasets, "Prediction Agreement Matrix", outdir)
        print("    OK  agreement_heatmap.png")

        for n in names:
            P.error_heatmap(datasets[n], truth, f"Errors - {n}", outdir,
                            filename=f"errors_{n}.png")
            print(f"    OK  errors_{n}.png")

        if len(names) == 2:
            P.delta_per_card(pc_dfs[names[0]], pc_dfs[names[1]],
                             names[0], names[1],
                             f"Accuracy Delta: {names[0]} ->{names[1]}", outdir)
            print("    OK  delta_per_card.png")

        print(f"\n  All plots saved to outputs/compare_{label}/")

    print()


def main():
    parser = argparse.ArgumentParser(
        description="Compare multiple synergy prediction datasets side-by-side."
    )
    parser.add_argument("datasets", nargs="*", help="Dataset names to compare")
    parser.add_argument("--all",      action="store_true", help="Compare all model datasets")
    parser.add_argument("--no-plots", action="store_true", help="Skip plot generation")
    args = parser.parse_args()

    if args.all:
        names = list(list_model_datasets().keys())
    elif len(args.datasets) >= 2:
        names = args.datasets
    else:
        names = select_datasets()

    if len(names) < 2:
        print("Nothing to compare.")
        return

    run(names, make_plots=not args.no_plots)


if __name__ == "__main__":
    main()
