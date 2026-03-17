#!/usr/bin/env python
"""
STS Synergy Browser -- Explore per-card and per-pair predictions interactively.

Usage:
    python browse.py                           # interactive menu
    python browse.py --card "Bash"             # all synergies for Bash
    python browse.py --pair "Bash" "Anger"     # one pair across all datasets
    python browse.py --errors gpt54            # all errors for a dataset
    python browse.py --disagreements           # pairs where datasets disagree
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
    load_dataset, load_all_model_datasets, get_ground_truth_name,
    get_card_names, list_model_datasets,
)
from lib import metrics as M

# Optional: rich for nicer tables
try:
    from rich.console import Console
    from rich.table import Table
    from rich import box as rbox
    console = Console()
    RICH = True
except ImportError:
    RICH = False
    console = None


# -- display helpers ----------------------------------------------------------

_SYM = {1: "+1 OK syn", 0: " 0  ...", -1: "-1 X anti"}
_SYM_SHORT = {1: "+1", 0: " 0", -1: "-1"}
_CORRECT = {True: "OK", False: "X"}


def _val_str(v: int) -> str:
    return _SYM.get(int(v), str(v))


def _val_short(v: int) -> str:
    return _SYM_SHORT.get(int(v), str(v))


def _print_pair_block(card_a: str, card_b: str,
                      truth_df: pd.DataFrame,
                      datasets: dict[str, pd.DataFrame]):
    """Print a rich comparison block for a single card pair."""
    cards = list(truth_df.index)
    if card_a not in cards or card_b not in cards:
        print(f"  Unknown card(s): '{card_a}', '{card_b}'")
        return

    gt = int(truth_df.loc[card_a, card_b])

    print(f"\n  +{'-'*54}+")
    print(f"  |  {card_a}  ->  {card_b}{' '*(50-len(card_a)-len(card_b))}|")
    print(f"  +{'-'*54}+")
    print(f"  |  Ground Truth:   {_val_str(gt):<37}|")
    for ds_name, df in datasets.items():
        pred = int(df.loc[card_a, card_b])
        correct = "OK" if pred == gt else "X "
        print(f"  |  {ds_name:<15}  {_val_str(pred):<20} [{correct}]{' '*(10-len(ds_name))}|")
    print(f"  +{'-'*54}+")


def _print_card_table(card: str, truth_df: pd.DataFrame,
                      datasets: dict[str, pd.DataFrame]):
    """Print a table of all synergies for a given card (row view)."""
    cards = list(truth_df.index)
    if card not in cards:
        print(f"  Unknown card: '{card}'")
        return

    ds_names = list(datasets.keys())
    print(f"\n  All synergies FROM '{card}' (card A):")
    print()

    col_w = 7
    header  = f"  {'Card B':<25} {'Truth':>{col_w}}"
    header += "".join(f" {n:>{col_w}}" for n in ds_names)
    header += f"  {'Notes'}"
    print(header)
    print(f"  {'-'*25} {'-'*col_w}" + f" {'-'*col_w}" * len(ds_names))

    gt_row = truth_df.loc[card]
    pred_rows = {n: df.loc[card] for n, df in datasets.items()}

    for cb in cards:
        if cb == card:
            continue
        gt_val = int(gt_row[cb])
        preds = {n: int(pred_rows[n][cb]) for n in ds_names}
        all_correct = all(v == gt_val for v in preds.values())
        all_agree   = len(set(preds.values())) == 1

        line = f"  {cb:<25} {_val_short(gt_val):>{col_w}}"
        line += "".join(f" {_val_short(v):>{col_w}}" for v in preds.values())

        flags = []
        if not all_correct:
            flags.append("ERR")
        if not all_agree and len(ds_names) > 1:
            flags.append("DISAGREE")
        line += f"  {'  '.join(flags)}"
        print(line)


# -- filter views -------------------------------------------------------------

def show_errors(ds_name: str, truth_df: pd.DataFrame, datasets: dict):
    if ds_name not in datasets:
        print(f"  Dataset '{ds_name}' not found.")
        return
    pred = datasets[ds_name]
    pairs = M.pair_table(pred, truth_df,
                         extra={n: d for n, d in datasets.items() if n != ds_name})
    errors = pairs[~pairs["correct"]].copy()

    print(f"\n  Errors for '{ds_name}'  ({len(errors):,} of {len(pairs):,} pairs)\n")
    ds_names = list(datasets.keys())
    extra_cols = [f"pred_{n}" for n in ds_names if n != ds_name]

    print(f"  {'Card A':<20} {'Card B':<20} {'Truth':>6} {'Pred':>6}", end="")
    for col in extra_cols:
        n = col.replace("pred_", "")
        print(f" {n:>8}", end="")
    print()
    print(f"  {'-'*20} {'-'*20} {'-'*6} {'-'*6}", end="")
    for _ in extra_cols:
        print(f" {'-'*8}", end="")
    print()

    for _, row in errors.sort_values(["card_a", "card_b"]).iterrows():
        print(f"  {row['card_a']:<20} {row['card_b']:<20} "
              f"{_val_short(row['ground_truth']):>6} {_val_short(row['predicted']):>6}", end="")
        for col in extra_cols:
            print(f" {_val_short(row[col]):>8}", end="")
        print()


def show_disagreements(truth_df: pd.DataFrame, datasets: dict):
    if len(datasets) < 2:
        print("  Need at least 2 datasets to show disagreements.")
        return

    names = list(datasets.keys())
    n1, n2 = names[0], names[1]
    pairs = M.pair_table(datasets[n1], truth_df, extra={n2: datasets[n2]})
    dis = pairs[pairs["predicted"] != pairs[f"pred_{n2}"]].copy()

    print(f"\n  Pairs where '{n1}' and '{n2}' disagree  ({len(dis):,} pairs)\n")
    print(f"  {'Card A':<20} {'Card B':<20} {'Truth':>6} {n1:>10} {n2:>10} {'Winner':>10}")
    print(f"  {'-'*20} {'-'*20} {'-'*6} {'-'*10} {'-'*10} {'-'*12}")

    for _, row in dis.sort_values(["card_a", "card_b"]).iterrows():
        gt = row["ground_truth"]
        p1 = row["predicted"]
        p2 = row[f"pred_{n2}"]
        if p1 == gt:
            winner = n1
        elif p2 == gt:
            winner = n2
        else:
            winner = "neither"
        print(f"  {row['card_a']:<20} {row['card_b']:<20} "
              f"{_val_short(gt):>6} {_val_short(p1):>10} {_val_short(p2):>10} {winner:>12}")


# -- interactive mode ----------------------------------------------------------

def fuzzy_match_card(query: str, cards: list[str]) -> list[str]:
    q = query.lower()
    exact = [c for c in cards if c.lower() == q]
    if exact:
        return exact
    return [c for c in cards if q in c.lower()]


def pick_card(prompt: str, cards: list[str]) -> str | None:
    raw = input(f"  {prompt}: ").strip()
    if not raw:
        return None
    matches = fuzzy_match_card(raw, cards)
    if not matches:
        print(f"  No card matching '{raw}'.")
        return None
    if len(matches) == 1:
        return matches[0]
    print("  Multiple matches:")
    for i, m in enumerate(matches, 1):
        print(f"    [{i}] {m}")
    sel = input("  Pick number: ").strip()
    if sel.isdigit() and 1 <= int(sel) <= len(matches):
        return matches[int(sel) - 1]
    return None


def interactive(truth_df, datasets):
    cards = list(truth_df.index)
    ds_names = list(datasets.keys())

    menu = """
  +---------------------------------------------+
  |  STS SYNERGY BROWSER                        |
  |                                             |
  |  [1]  Browse by card (all synergies)        |
  |  [2]  Browse by pair (side-by-side)         |
  |  [3]  Show all errors for a dataset         |
  |  [4]  Show dataset disagreements            |
  |  [5]  Search card pairs by value            |
  |  [q]  Quit                                  |
  +---------------------------------------------+"""

    while True:
        print(menu)
        choice = input("  > ").strip().lower()

        if choice in ("q", "quit"):
            break

        elif choice == "1":
            card = pick_card("Card name (partial OK)", cards)
            if card:
                _print_card_table(card, truth_df, datasets)

        elif choice == "2":
            card_a = pick_card("Card A name", cards)
            if not card_a:
                continue
            card_b = pick_card("Card B name", cards)
            if not card_b:
                continue
            _print_pair_block(card_a, card_b, truth_df, datasets)
            # offer to annotate
            print()
            ann = input("  Add annotation to this pair? [y/N]: ").strip().lower()
            if ann == "y":
                _quick_annotate(card_a, card_b, truth_df, datasets)

        elif choice == "3":
            print(f"  Datasets: {', '.join(ds_names)}")
            ds = input("  Which dataset? ").strip()
            show_errors(ds, truth_df, datasets)

        elif choice == "4":
            show_disagreements(truth_df, datasets)

        elif choice == "5":
            print("  Filter by ground truth value (-1 / 0 / 1) or press Enter to skip:")
            gt_filter = input("  Ground truth: ").strip()
            print("  Filter by prediction value (-1 / 0 / 1) or press Enter to skip:")
            pred_filter = input("  Predicted (which dataset?): ").strip()
            ds = None
            if pred_filter in ["-1", "0", "1"]:
                print(f"  Available: {', '.join(ds_names)}")
                ds = input("  Dataset name: ").strip()

            n1 = ds_names[0]
            pairs = M.pair_table(datasets[n1], truth_df,
                                 extra={n: datasets[n] for n in ds_names[1:]})
            filtered = pairs
            if gt_filter in ["-1", "0", "1"]:
                filtered = filtered[filtered["ground_truth"] == int(gt_filter)]
            if pred_filter in ["-1", "0", "1"] and ds in datasets:
                col = "predicted" if ds == n1 else f"pred_{ds}"
                filtered = filtered[filtered[col] == int(pred_filter)]
            print(f"\n  {len(filtered):,} pairs match.\n")
            for _, row in filtered.head(50).iterrows():
                print(f"  {row['card_a']:<20} {row['card_b']:<20}  "
                      f"GT={_val_short(row['ground_truth'])}")
            if len(filtered) > 50:
                print(f"  ... and {len(filtered)-50} more.")

        else:
            print("  Unknown option.")


def _quick_annotate(card_a: str, card_b: str,
                    truth_df: pd.DataFrame, datasets: dict):
    """Quick annotation entry from browse mode -- delegates to annotations.csv."""
    from annotate import add_annotation
    gt = int(truth_df.loc[card_a, card_b])
    preds = {n: int(df.loc[card_a, card_b]) for n, df in datasets.items()}
    note = input("  Note: ").strip()
    tags = input("  Tags (comma-separated, or blank): ").strip()
    if note or tags:
        add_annotation(card_a, card_b, gt, preds, note, tags)
        print("  OK Annotation saved.")


# -- main ----------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Browse STS synergy predictions per-card or per-pair."
    )
    parser.add_argument("--card",   nargs=1,   metavar="CARD",      help="Show all synergies for a card")
    parser.add_argument("--pair",   nargs=2,   metavar=("A", "B"),  help="Show one pair across all datasets")
    parser.add_argument("--errors", nargs=1,   metavar="DATASET",   help="Show all errors for a dataset")
    parser.add_argument("--disagreements", action="store_true",     help="Show where datasets disagree")
    args = parser.parse_args()

    gt_name = get_ground_truth_name()
    truth   = load_dataset(gt_name)
    datasets = load_all_model_datasets()

    if args.card:
        _print_card_table(args.card[0], truth, datasets)
    elif args.pair:
        _print_pair_block(args.pair[0], args.pair[1], truth, datasets)
    elif args.errors:
        show_errors(args.errors[0], truth, datasets)
    elif args.disagreements:
        show_disagreements(truth, datasets)
    else:
        interactive(truth, datasets)


if __name__ == "__main__":
    main()
