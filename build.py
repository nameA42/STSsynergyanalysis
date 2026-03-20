"""
build.py — Static site builder for STS Synergy analysis.

Outputs:
  docs/data/config.json
  docs/data/pairs.json
  docs/data/metrics.json
  docs/data/per_card.json
  docs/data/annotations.json
  docs/static/  (copy of static/)
  docs/*.html   (copy of docs_src/)
  docs/.nojekyll
"""

import io
import json
import math
import shutil
import sys
from pathlib import Path

# Force UTF-8 output on Windows so non-ASCII print() calls don't crash
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import numpy as np
import pandas as pd

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DOCS_DIR = BASE_DIR / "docs"
DOCS_DATA = DOCS_DIR / "data"
DOCS_SRC  = BASE_DIR / "docs_src"

sys.path.insert(0, str(BASE_DIR))
from lib import loader, metrics as mlib
from lib.logs import find_log_for_csv, parse_log


def nan_safe(obj):
    """Recursively replace NaN/Inf with None for JSON serialisation."""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, dict):
        return {k: nan_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [nan_safe(v) for v in obj]
    # numpy scalar types
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        v = float(obj)
        return None if (math.isnan(v) or math.isinf(v)) else v
    return obj


def main():
    print("=" * 60)
    print("STS Synergy — Static Site Build")
    print("=" * 60)

    # ── Setup dirs ────────────────────────────────────────────────
    DOCS_DIR.mkdir(exist_ok=True)
    DOCS_DATA.mkdir(exist_ok=True)
    print(f"Output directory: {DOCS_DIR}")

    # ── Load data ─────────────────────────────────────────────────
    print("\n[1/6] Loading datasets...")
    config = loader.load_config()
    truth_df = loader.load_dataset(loader.get_ground_truth_name())
    model_dfs = loader.load_all_model_datasets()
    model_info = loader.list_model_datasets()
    cards = loader.get_card_names()
    print(f"  Ground truth: {truth_df.shape}")
    print(f"  Models: {list(model_dfs.keys())}")
    print(f"  Cards: {len(cards)}")

    # ── config.json ───────────────────────────────────────────────
    print("\n[2/6] Writing config.json...")
    # Load card descriptions from Card Names CSV
    import csv as _csv
    card_names_csv = BASE_DIR / "data" / "ground_truth" / "StS Synergies - Card Names.csv"
    card_descriptions = {}
    if card_names_csv.exists():
        with open(card_names_csv, encoding="utf-8", newline="") as f:
            for row in _csv.DictReader(f):
                name = (row.get("Name") or row.get("C") or "").strip()
                desc = row.get("Description", "").strip()
                if name and desc:
                    card_descriptions[name] = desc

    config_out = {
        "models": {
            name: {
                "description": info.get("description", ""),
                "model":       info.get("model", name),
                "date":        info.get("date", ""),
            }
            for name, info in model_info.items()
        },
        "cards": cards,
        "card_descriptions": card_descriptions,
    }
    # model_order added after metrics are computed (see below)
    (DOCS_DATA / "config.json").write_text(
        json.dumps(config_out, indent=2), encoding="utf-8"
    )
    print(f"  {len(config_out['models'])} models, {len(cards)} cards")

    # ── pairs.json ────────────────────────────────────────────────
    print("\n[3/6] Building pairs.json (5625 pairs)...")
    model_names = list(model_dfs.keys())

    pairs_out = []
    for i, ca in enumerate(cards):
        for j, cb in enumerate(cards):
            if i == j:
                continue
            pair = {
                "pair_id": f"{ca}|{cb}",
                "card_a":  ca,
                "card_b":  cb,
                "gt":      int(truth_df.iloc[i, j]),
            }
            for ds_name, df in model_dfs.items():
                pair[ds_name] = int(df.iloc[i, j])
            pairs_out.append(pair)

    (DOCS_DATA / "pairs.json").write_text(
        json.dumps(pairs_out), encoding="utf-8"
    )
    print(f"  {len(pairs_out)} pairs written")

    # ── metrics.json ──────────────────────────────────────────────
    print("\n[4/6] Computing metrics.json...")
    metrics_out = {}
    for ds_name, df in model_dfs.items():
        m = mlib.overall(df, truth_df)
        # confusion_matrix is a numpy array — convert to list
        cm = m.pop("confusion_matrix")
        m["confusion_matrix"] = cm.tolist()
        # per_class keys are ints — make them strings for JSON
        m["per_class"] = {str(k): v for k, v in m["per_class"].items()}
        metrics_out[ds_name] = nan_safe(m)
        print(f"  {ds_name}: acc={m['accuracy']:.4f}  macro_f1={m['macro_f1']:.4f}")

    (DOCS_DATA / "metrics.json").write_text(
        json.dumps(metrics_out, indent=2), encoding="utf-8"
    )

    # Add model_order to config.json (sorted by accuracy descending)
    accuracies = {n: metrics_out[n]["accuracy"] for n in model_names}
    model_order = sorted(model_names, key=lambda n: accuracies[n], reverse=True)
    config_out["model_order"] = model_order
    from annotate import DEFAULT_TAGS
    config_out["default_tags"] = DEFAULT_TAGS
    (DOCS_DATA / "config.json").write_text(
        json.dumps(config_out, indent=2), encoding="utf-8"
    )
    print(f"  model_order: {model_order}")

    # ── per_card.json ─────────────────────────────────────────────
    print("\n[5/6] Computing per_card.json...")
    per_card_out = {
        "as_a": {},
        "as_b": {},
        "combined": {},
    }
    for ds_name, df in model_dfs.items():
        pc_a_df   = mlib.per_card(df, truth_df)
        pc_b_df   = mlib.per_card_as_b(df, truth_df)
        pc_comb_df = mlib.per_card_combined(df, truth_df)
        per_card_out["as_a"][ds_name] = {
            card: nan_safe(row.to_dict())
            for card, row in pc_a_df.iterrows()
        }
        per_card_out["as_b"][ds_name] = {
            card: nan_safe(row.to_dict())
            for card, row in pc_b_df.iterrows()
        }
        per_card_out["combined"][ds_name] = {
            card: nan_safe(row.to_dict())
            for card, row in pc_comb_df.iterrows()
        }
    (DOCS_DATA / "per_card.json").write_text(
        json.dumps(per_card_out, indent=2), encoding="utf-8"
    )
    print(f"  {len(cards)} cards × {len(model_dfs)} models (as_a, as_b, combined)")

    # ── responses.json ────────────────────────────────────────────
    print("\n[6/7] Parsing model log files for reasoning...")
    responses_out = {}   # pair_id → {model_name: response_text}
    for ds_name, info in model_info.items():
        csv_path = BASE_DIR / info.get("file", "")
        log_path = find_log_for_csv(csv_path)
        if log_path is None:
            print(f"  {ds_name}: no log file found")
            continue
        parsed = parse_log(log_path)
        print(f"  {ds_name}: {len(parsed)} responses parsed")
        for pair_id, text in parsed.items():
            if pair_id not in responses_out:
                responses_out[pair_id] = {}
            responses_out[pair_id][ds_name] = text

    (DOCS_DATA / "responses.json").write_text(
        json.dumps(responses_out, ensure_ascii=False), encoding="utf-8"
    )
    print(f"  Total pairs with at least one response: {len(responses_out)}")

    # ── annotations.json ──────────────────────────────────────────
    print("\n[7/7] Loading annotations...")
    ann_json_path = BASE_DIR / "annotations" / "annotations.json"
    ann_csv_path  = BASE_DIR / "annotations" / "annotations.csv"

    if ann_json_path.exists():
        annotations = json.loads(ann_json_path.read_text(encoding="utf-8"))
        print(f"  Loaded {len(annotations)} annotations from annotations.json")
    elif ann_csv_path.exists():
        print(f"  Migrating from annotations.csv...")
        ann_df = pd.read_csv(ann_csv_path, dtype=str)
        annotations = ann_df.to_dict(orient="records")
        # Write migrated JSON for future use
        ann_json_path.parent.mkdir(exist_ok=True)
        ann_json_path.write_text(
            json.dumps(annotations, indent=2), encoding="utf-8"
        )
        print(f"  Migrated {len(annotations)} annotations -> annotations.json")
    else:
        annotations = []
        print("  No annotations found; writing empty array")

    (DOCS_DATA / "annotations.json").write_text(
        json.dumps(annotations, indent=2), encoding="utf-8"
    )

    # ── Copy static/ → docs/static/ ──────────────────────────────
    print("\nCopying static/ -> docs/static/...")
    static_src = BASE_DIR / "static"
    static_dst = DOCS_DIR / "static"
    if static_dst.exists():
        shutil.rmtree(static_dst)
    shutil.copytree(static_src, static_dst)
    print(f"  Copied {sum(1 for _ in static_dst.rglob('*') if _.is_file())} files")

    # ── Copy docs_src/ → docs/ ────────────────────────────────────
    print("\nCopying docs_src/ -> docs/...")
    if not DOCS_SRC.exists():
        print(f"  WARNING: {DOCS_SRC} does not exist - skipping HTML copy")
    else:
        html_count = 0
        for src_file in DOCS_SRC.glob("*.html"):
            dst_file = DOCS_DIR / src_file.name
            shutil.copy2(src_file, dst_file)
            html_count += 1
            print(f"  Copied {src_file.name}")
        print(f"  {html_count} HTML files copied")

    # ── Write .nojekyll ───────────────────────────────────────────
    (DOCS_DIR / ".nojekyll").write_text("", encoding="utf-8")
    print("\nWrote docs/.nojekyll")

    # ── Summary ───────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("Build complete!")
    all_files = list(DOCS_DIR.rglob("*"))
    file_count = sum(1 for f in all_files if f.is_file())
    print(f"  Total files in docs/: {file_count}")
    print(f"  data/config.json    : {(DOCS_DATA/'config.json').stat().st_size:,} bytes")
    print(f"  data/pairs.json     : {(DOCS_DATA/'pairs.json').stat().st_size:,} bytes")
    print(f"  data/metrics.json   : {(DOCS_DATA/'metrics.json').stat().st_size:,} bytes")
    print(f"  data/per_card.json  : {(DOCS_DATA/'per_card.json').stat().st_size:,} bytes")
    print(f"  data/annotations.json: {(DOCS_DATA/'annotations.json').stat().st_size:,} bytes")
    print(f"  data/responses.json  : {(DOCS_DATA/'responses.json').stat().st_size:,} bytes")
    print("=" * 60)


if __name__ == "__main__":
    main()
