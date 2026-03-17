#!/usr/bin/env python
"""
STS Synergy Analyzer -- Full metrics report for a single dataset.

Usage:
    python analyze.py                     # interactive dataset selection
    python analyze.py gpt54               # analyze 'gpt54' directly
    python analyze.py gpt54 --no-plots    # skip plot generation
    python analyze.py --list              # list available datasets
"""

import sys
import io
import argparse
from pathlib import Path

# Force UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).parent))

from lib.loader import (
    load_dataset, load_config, list_model_datasets,
    get_ground_truth_name, dataset_info,
)
from lib import metrics as M
from lib import plots as P

try:
    from rich.console import Console
    from rich.table import Table
    from rich import box
    console = Console()
    RICH = True
except ImportError:
    RICH = False


# -- printing helpers ----------------------------------------------------------

def _sep(char="-", width=56):
    return char * width

def _header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}")

def _section(text):
    print(f"\n  {text}")
    print(f"  {_sep()}")


def print_overall(name: str, m: dict):
    _header(f"STS SYNERGY ANALYSIS  .  {name.upper()}")

    _section("OVERALL METRICS")
    rows = [
        ("Accuracy",         f"{m['accuracy']*100:.2f}%"),
        ("Macro F1",         f"{m['macro_f1']:.4f}"),
        ("Weighted F1",      f"{m['weighted_f1']:.4f}"),
        ("Macro Precision",  f"{m['macro_precision']:.4f}"),
        ("Macro Recall",     f"{m['macro_recall']:.4f}"),
        ("Correct / Total",  f"{m['n_correct']:,} / {m['n_total']:,}"),
        ("Errors",           f"{m['n_errors']:,}  ({m['n_errors']/m['n_total']*100:.1f}%)"),
    ]
    for label, value in rows:
        print(f"  {label:<25} {value}")

    _section("PER-CLASS METRICS")
    hdr = f"  {'Class':<15} {'Precision':>11} {'Recall':>9} {'F1':>9} {'Support':>9}"
    print(hdr)
    print(f"  {'-'*15} {'-'*11} {'-'*9} {'-'*9} {'-'*9}")
    for lbl in [-1, 0, 1]:
        pc = m["per_class"][lbl]
        name_str = M.LABEL_NAMES[lbl]
        print(f"  {name_str:<15} {pc['precision']:>11.4f} {pc['recall']:>9.4f} "
              f"{pc['f1']:>9.4f} {pc['support']:>9,}")

    _section("CONFUSION MATRIX  (rows = truth, cols = predicted)")
    cm = m["confusion_matrix"]
    col_labels = ["Neg (-1)", "Neut (0)", "Pos (+1)"]
    print(f"  {'truth \\ pred':<13}", end="")
    for cl in col_labels:
        print(f" {cl:>10}", end="")
    print()
    print(f"  {'-'*13}", end="")
    for _ in col_labels:
        print(f" {'-'*10}", end="")
    print()
    for i, lbl in enumerate([-1, 0, 1]):
        label_str = M.LABEL_NAMES[lbl][:13]
        print(f"  {label_str:<13}", end="")
        for j in range(3):
            cell = f"{cm[i,j]:,}"
            marker = " *" if i == j else "  "
            print(f" {cell:>8}{marker}", end="")
        print()


def print_per_card_summary(pc_df, n=10):
    _section(f"PROBLEM CARDS  (worst {n} by accuracy)")
    worst = pc_df.sort_values("accuracy").head(n)
    hdr = f"  {'#':<4} {'Card':<25} {'Acc':>7} {'Errors':>7} {'FP+syn':>7} {'FN+syn':>7}"
    print(hdr)
    print(f"  {'-'*4} {'-'*25} {'-'*7} {'-'*7} {'-'*7} {'-'*7}")
    for rank, (card, row) in enumerate(worst.iterrows(), 1):
        print(f"  {rank:<4} {card:<25} {row['accuracy']*100:>6.1f}% "
              f"{row['n_errors']:>7} {row['false_pos_synergy']:>7} {row['false_neg_synergy']:>7}")

    _section(f"TOP CARDS  (best {n} by accuracy)")
    best = pc_df.sort_values("accuracy").tail(n).iloc[::-1]
    print(hdr)
    print(f"  {'-'*4} {'-'*25} {'-'*7} {'-'*7} {'-'*7} {'-'*7}")
    for rank, (card, row) in enumerate(best.iterrows(), 1):
        print(f"  {rank:<4} {card:<25} {row['accuracy']*100:>6.1f}% "
              f"{row['n_errors']:>7} {row['false_pos_synergy']:>7} {row['false_neg_synergy']:>7}")


def print_error_breakdown(eb: dict):
    _section("ERROR BREAKDOWN  (how predictions went wrong)")
    bd = eb["breakdown"]
    rows_sorted = sorted(bd.items(), key=lambda x: -x[1]["count"])
    print(f"  {'Error type (truth->pred)':<30} {'Count':>7}  {'% of all pairs':>14}")
    print(f"  {'-'*30} {'-'*7}  {'-'*14}")
    for key, info in rows_sorted:
        if info["count"] > 0:
            readable = key.replace("true", "truth=").replace("_pred", " -> pred=")
            print(f"  {readable:<30} {info['count']:>7,}  {info['pct']:>13.2f}%")


# -- dataset selection menu ----------------------------------------------------

def select_dataset() -> str | None:
    models = list_model_datasets()
    if not models:
        print("No model datasets found in datasets.json.")
        return None

    print("\nAvailable datasets:")
    items = list(models.items())
    for i, (name, info) in enumerate(items, 1):
        print(f"  [{i}] {name:<20}  {info.get('description', '')}")
    print()

    while True:
        raw = input("Select dataset (number or name, q to quit): ").strip()
        if raw.lower() in ("q", "quit", ""):
            return None
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(items):
                return items[idx][0]
        elif raw in models:
            return raw
        print("  Invalid selection, try again.")


# -- main logic ----------------------------------------------------------------

def run(name: str, make_plots: bool = True):
    gt_name = get_ground_truth_name()
    print(f"\nLoading '{name}' vs ground truth...")
    truth = load_dataset(gt_name)
    pred  = load_dataset(name)

    print("Computing metrics...")
    m  = M.overall(pred, truth)
    pc = M.per_card(pred, truth)
    eb = M.error_breakdown(pred, truth)

    print_overall(name, m)
    print_per_card_summary(pc)
    print_error_breakdown(eb)

    if make_plots:
        outdir = Path("outputs") / name
        outdir.mkdir(parents=True, exist_ok=True)
        print(f"\n  Generating plots -> outputs/{name}/")

        P.confusion_matrix_plot(m["confusion_matrix"], [-1, 0, 1],
                                f"Confusion Matrix - {name}", outdir)
        print("    OK  confusion_matrix.png")

        P.prediction_heatmap(pred, f"Predictions - {name}", outdir)
        print("    OK  prediction_heatmap.png")

        P.error_heatmap(pred, truth, f"Errors - {name}", outdir)
        print("    OK  error_heatmap.png")

        P.per_card_accuracy_chart(pc, f"Per-Card Accuracy - {name}", outdir)
        print("    OK  per_card_accuracy.png")

        P.class_distribution(pred, truth, f"Class Distribution - {name}", outdir)
        print("    OK  class_distribution.png")

        P.error_type_breakdown(eb, f"Error Breakdown - {name}", outdir)
        print("    OK  error_breakdown.png")

        print(f"\n  All plots saved to outputs/{name}/")

    print()


def main():
    parser = argparse.ArgumentParser(
        description="Full analysis report for one synergy prediction dataset."
    )
    parser.add_argument("dataset", nargs="?", help="Dataset name (from datasets.json)")
    parser.add_argument("--no-plots", action="store_true", help="Skip plot generation")
    parser.add_argument("--list",     action="store_true", help="List available datasets")
    args = parser.parse_args()

    if args.list:
        models = list_model_datasets()
        print("\nAvailable datasets:")
        for name, info in models.items():
            print(f"  {name:<20}  {info.get('description', '')}")
        print()
        return

    name = args.dataset or select_dataset()
    if not name:
        return

    run(name, make_plots=not args.no_plots)


if __name__ == "__main__":
    main()
