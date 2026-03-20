#!/usr/bin/env python
"""
STS Synergy Annotator -- Add notes and labels to card pair predictions.

Annotations are saved to annotations/annotations.csv -- easy to open in Excel/Sheets.

Usage:
    python annotate.py                         # interactive menu
    python annotate.py --view                  # print all annotations
    python annotate.py --view --tag important  # filter by tag
    python annotate.py --view --card Bash      # filter by card name
    python annotate.py --export                # re-export CSV (refreshes pred columns)
"""

import sys
import argparse
import csv
from datetime import datetime
from pathlib import Path

# Force UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

from lib.loader import (
    load_dataset, load_all_model_datasets, get_ground_truth_name,
    get_card_names, list_model_datasets,
)

ANNOTATIONS_FILE = Path(__file__).parent / "annotations" / "annotations.csv"

# Column order in the CSV -- prediction columns are added dynamically
# model="" means general (not tied to any specific model)
_FIXED_COLS = ["pair_id", "model", "card_a", "card_b", "ground_truth"]
_META_COLS  = ["note", "tags", "timestamp"]

# Default tags drawn from the paper's error taxonomy (Section VIII) and
# challenge categories (Section V). Always shown as suggestions even when
# no annotations exist yet.
DEFAULT_TAGS = [
    # Error types (§VIII)
    "description_error",
    "timing_error",
    "timing_interruption",
    "timing_immediacy",
    "game_state_error",
    "rule_error",
    "skip_error",
    "similarity_error",
    # Challenge categories (§V)
    "mixed_effects",
    "conflicting_synergy",
    "design_subversion",
    "resource_management",
    "scaling",
    "external_factors",
    # General
    "false_positive",
    "false_negative",
    "interesting",
    "paper_example",
]


# -- CSV I/O ------------------------------------------------------------------

def _load_annotations() -> pd.DataFrame:
    if not ANNOTATIONS_FILE.exists():
        return pd.DataFrame(columns=_FIXED_COLS + _META_COLS)
    df = pd.read_csv(ANNOTATIONS_FILE, dtype=str)
    # Ensure required columns exist (backwards-compat: old rows have no model column)
    for col in _FIXED_COLS + _META_COLS:
        if col not in df.columns:
            df[col] = ""
    return df


def _ann_key(pair_id: str, model: str) -> tuple:
    return (pair_id, model.strip())


def get_annotations_for_pair(pair_id: str) -> dict:
    """Return {model_key: row_dict} for all annotations on this pair.
    model_key is "" for general annotations, or the model name."""
    df = _load_annotations()
    if df.empty:
        return {}
    rows = df[df["pair_id"] == pair_id]
    result = {}
    for _, row in rows.iterrows():
        key = row.get("model", "").strip()
        result[key] = row.to_dict()
    return result


def get_all_tags() -> list:
    """Return sorted list of all unique tags (defaults + any used in annotations)."""
    tags = set(DEFAULT_TAGS)
    df = _load_annotations()
    if not df.empty:
        for raw in df["tags"].dropna():
            for t in str(raw).split(","):
                t = t.strip()
                if t:
                    tags.add(t)
    return sorted(tags)


def _save_annotations(df: pd.DataFrame):
    ANNOTATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(ANNOTATIONS_FILE, index=False)


def _build_pred_columns(preds: dict) -> dict:
    """Return {pred_<name>: value} for all model datasets."""
    return {f"pred_{n}": str(v) for n, v in preds.items()}


def add_annotation(card_a: str, card_b: str,
                   gt: int, preds: dict[str, int],
                   note: str, tags: str,
                   model: str = "") -> bool:
    """
    Add or update an annotation for a card pair.
    model="" means general (not tied to any model).
    Composite key is (pair_id, model).
    Returns True if added/updated, False if nothing to save.
    """
    if not note and not tags:
        return False

    df = _load_annotations()
    pair_id   = f"{card_a}|{card_b}"
    model     = model.strip()
    pred_cols = _build_pred_columns(preds)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    row = {
        "pair_id":      pair_id,
        "model":        model,
        "card_a":       card_a,
        "card_b":       card_b,
        "ground_truth": str(gt),
        **pred_cols,
        "note":         note,
        "tags":         tags,
        "timestamp":    timestamp,
    }

    # Add any new pred columns to existing DataFrame
    for col in pred_cols:
        if col not in df.columns:
            df[col] = ""
    if "model" not in df.columns:
        df["model"] = ""

    # Update if (pair_id, model) exists, otherwise append
    mask = (df["pair_id"] == pair_id) & (df["model"] == model)
    if mask.any():
        if not note:
            row["note"] = df.loc[mask, "note"].iloc[0]
        for col, val in row.items():
            df.loc[mask, col] = val
    else:
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)

    _save_annotations(df)
    return True


def delete_annotation(pair_id: str, model: str = "") -> bool:
    df = _load_annotations()
    model = model.strip()
    if "model" not in df.columns:
        df["model"] = ""
    before = len(df)
    df = df[~((df["pair_id"] == pair_id) & (df["model"] == model))]
    if len(df) == before:
        return False
    _save_annotations(df)
    return True


# -- display helpers ----------------------------------------------------------

def _sym(v) -> str:
    m = {1: "+1", 0: " 0", -1: "-1", "1": "+1", "0": " 0", "-1": "-1"}
    return m.get(str(v).strip(), str(v))


def print_annotation(row: pd.Series, pred_cols: list[str]):
    print(f"\n  +{'-'*58}+")
    print(f"  |  {row['card_a']}  ->  {row['card_b']}")
    print(f"  |  Ground Truth:  {_sym(row['ground_truth'])}")
    for col in pred_cols:
        name = col.replace("pred_", "")
        val = row.get(col, "?")
        print(f"  |  {name:<15}  {_sym(val)}")
    print(f"  |")
    note = row.get("note", "")
    tags = row.get("tags", "")
    ts   = row.get("timestamp", "")
    if note:
        print(f"  |  Note:   {note}")
    if tags:
        print(f"  |  Tags:   {tags}")
    if ts:
        print(f"  |  Added:  {ts}")
    print(f"  +{'-'*58}+")


def print_all_annotations(df: pd.DataFrame, filter_tag: str = "",
                          filter_card: str = ""):
    pred_cols = [c for c in df.columns if c.startswith("pred_")]

    if filter_tag:
        df = df[df["tags"].str.contains(filter_tag, case=False, na=False)]
    if filter_card:
        mask = (df["card_a"].str.contains(filter_card, case=False, na=False) |
                df["card_b"].str.contains(filter_card, case=False, na=False))
        df = df[mask]

    if df.empty:
        print("  No annotations match the filter.")
        return

    print(f"\n  {len(df)} annotation(s):")
    for _, row in df.iterrows():
        print_annotation(row, pred_cols)


def print_summary_table(df: pd.DataFrame):
    """Compact table view of all annotations."""
    if df.empty:
        print("  No annotations yet.")
        return
    pred_cols = [c for c in df.columns if c.startswith("pred_")]

    # Header
    header = f"  {'#':<4} {'Pair':<35} {'GT':>4}"
    for col in pred_cols:
        n = col.replace("pred_", "")[:6]
        header += f" {n:>7}"
    header += f"  {'Tags':<20}  Note"
    print(header)
    print(f"  {'-'*4} {'-'*35} {'-'*4}" + " -----"*len(pred_cols) + f"  {'-'*20}  {'-'*30}")

    for i, (_, row) in enumerate(df.iterrows(), 1):
        pair = f"{row['card_a']} -> {row['card_b']}"
        line = f"  {i:<4} {pair:<35} {_sym(row['ground_truth']):>4}"
        for col in pred_cols:
            line += f" {_sym(row.get(col, '?')):>7}"
        tags = str(row.get("tags", ""))[:20]
        note = str(row.get("note", ""))[:40]
        line += f"  {tags:<20}  {note}"
        print(line)


# -- interactive annotation session -------------------------------------------

def fuzzy_match(query: str, items: list[str]) -> list[str]:
    q = query.lower()
    exact = [x for x in items if x.lower() == q]
    if exact:
        return exact
    return [x for x in items if q in x.lower()]


def pick_card(prompt: str, cards: list[str]) -> str | None:
    raw = input(f"  {prompt}: ").strip()
    if not raw:
        return None
    matches = fuzzy_match(raw, cards)
    if not matches:
        print(f"  No card matching '{raw}'.")
        return None
    if len(matches) == 1:
        return matches[0]
    print("  Matches:")
    for i, m in enumerate(matches, 1):
        print(f"    [{i}] {m}")
    sel = input("  Pick: ").strip()
    if sel.isdigit() and 1 <= int(sel) <= len(matches):
        return matches[int(sel) - 1]
    return None


def interactive_add(truth_df, datasets, cards):
    print("\n  -- Add Annotation --")
    card_a = pick_card("Card A (partial name OK)", cards)
    if not card_a:
        return
    card_b = pick_card("Card B", cards)
    if not card_b:
        return

    gt = int(truth_df.loc[card_a, card_b])
    preds = {n: int(df.loc[card_a, card_b]) for n, df in datasets.items()}

    # Show current values
    print(f"\n  Pair: {card_a} -> {card_b}")
    print(f"  Ground Truth: {_sym(gt)}")
    for name, val in preds.items():
        correct = "OK" if val == gt else "X"
        print(f"  {name:<15} {_sym(val)}  [{correct}]")

    note = input("\n  Note (free text): ").strip()
    tags = input("  Tags (comma-separated, e.g. false_negative,important): ").strip()

    if add_annotation(card_a, card_b, gt, preds, note, tags):
        print(f"  OK Saved annotation for {card_a} -> {card_b}")
    else:
        print("  (Nothing to save -- note and tags are both blank.)")


def interactive_view(df):
    print("\n  -- View / Filter Annotations --")
    print(f"  Total annotations: {len(df)}")
    if df.empty:
        return

    print("  Filter by tag (blank = all):  ", end="")
    tag = input().strip()
    print("  Filter by card (blank = all): ", end="")
    card = input().strip()
    print()
    print_all_annotations(df, filter_tag=tag, filter_card=card)


def interactive_delete(df):
    if df.empty:
        print("  No annotations to delete.")
        return
    print_summary_table(df)
    raw = input("\n  Enter # to delete (or blank to cancel): ").strip()
    if not raw.isdigit():
        return
    idx = int(raw) - 1
    if 0 <= idx < len(df):
        pair_id = df.iloc[idx]["pair_id"]
        confirm = input(f"  Delete annotation for '{pair_id}'? [y/N]: ").strip().lower()
        if confirm == "y":
            if delete_annotation(pair_id):
                print(f"  OK Deleted.")
    else:
        print("  Invalid number.")


def interactive(truth_df, datasets):
    cards = list(truth_df.index)

    menu = """
  +---------------------------------------------+
  |  STS SYNERGY ANNOTATOR                      |
  |                                             |
  |  [1]  Add annotation                        |
  |  [2]  View / filter annotations             |
  |  [3]  Summary table                         |
  |  [4]  Delete annotation                     |
  |  [5]  Open annotations file in explorer     |
  |  [q]  Quit                                  |
  +---------------------------------------------+"""

    while True:
        df = _load_annotations()
        print(menu)
        print(f"  ({len(df)} annotations saved)")
        choice = input("  > ").strip().lower()

        if choice in ("q", "quit"):
            break
        elif choice == "1":
            interactive_add(truth_df, datasets, cards)
        elif choice == "2":
            interactive_view(df)
        elif choice == "3":
            print()
            print_summary_table(df)
        elif choice == "4":
            interactive_delete(df)
        elif choice == "5":
            path = ANNOTATIONS_FILE.resolve()
            if path.exists():
                import os, subprocess
                try:
                    subprocess.Popen(["explorer", "/select,", str(path)])
                except Exception:
                    print(f"  File: {path}")
            else:
                print(f"  No annotations file yet. It will be at: {path}")
        else:
            print("  Unknown option.")


# -- main ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Add and manage notes on STS synergy card pair predictions."
    )
    parser.add_argument("--view",   action="store_true", help="Print all annotations")
    parser.add_argument("--tag",    default="", help="Filter by tag (with --view)")
    parser.add_argument("--card",   default="", help="Filter by card name (with --view)")
    parser.add_argument("--export", action="store_true",
                        help="Re-export annotations CSV with current prediction columns")
    args = parser.parse_args()

    gt_name  = get_ground_truth_name()
    truth    = load_dataset(gt_name)
    datasets = load_all_model_datasets()
    df       = _load_annotations()

    if args.view:
        print_all_annotations(df, filter_tag=args.tag, filter_card=args.card)
        return

    if args.export:
        # Refresh prediction columns from current datasets
        if df.empty:
            print("  No annotations to export.")
            return
        cards = list(truth.index)
        for _, row in df.iterrows():
            ca, cb = row["card_a"], row["card_b"]
            if ca in cards and cb in cards:
                for ds_name, ds_df in datasets.items():
                    col = f"pred_{ds_name}"
                    if col not in df.columns:
                        df[col] = ""
                    df.loc[df["pair_id"] == row["pair_id"], col] = str(
                        int(ds_df.loc[ca, cb])
                    )
        _save_annotations(df)
        print(f"  OK Exported {len(df)} annotations to {ANNOTATIONS_FILE}")
        return

    interactive(truth, datasets)


if __name__ == "__main__":
    main()
