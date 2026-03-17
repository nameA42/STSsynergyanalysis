"""Data loading utilities for the STS synergy analysis suite."""

import json
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def load_config() -> dict:
    p = BASE_DIR / "datasets.json"
    if not p.exists():
        raise FileNotFoundError(
            "datasets.json not found. Create it in the project root.\n"
            "See the example in the README or copy datasets.json.example."
        )
    with open(p) as f:
        return json.load(f)


def get_card_names() -> list[str]:
    """Return ordered list of card names from the ground truth file."""
    config = load_config()
    gt = _gt_entry(config)
    df = pd.read_csv(BASE_DIR / gt["file"], index_col=0)
    return list(df.columns)


def _gt_entry(config: dict) -> dict:
    for entry in config.values():
        if entry.get("type") == "ground_truth":
            return entry
    raise ValueError("No 'ground_truth' type entry found in datasets.json")


def get_ground_truth_name() -> str:
    config = load_config()
    for name, entry in config.items():
        if entry.get("type") == "ground_truth":
            return name
    raise ValueError("No 'ground_truth' type entry found in datasets.json")


def load_dataset(name: str) -> pd.DataFrame:
    """Load a dataset by its short name. Returns a cardxcard DataFrame of int values."""
    config = load_config()
    if name not in config:
        raise ValueError(f"Unknown dataset '{name}'. Available: {list(config.keys())}")

    entry = config[name]
    path = BASE_DIR / entry["file"]
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    df = pd.read_csv(path, index_col=0)

    if entry["type"] != "ground_truth":
        # Model result CSVs use numeric indices -- remap to card names
        cards = get_card_names()
        df.index = cards
        df.columns = cards

    n_missing = df.isna().sum().sum()
    if n_missing:
        print(f"  [loader] {name}: filling {n_missing} NaN cell(s) with 0")
        df = df.fillna(0)
    return df.astype(int)


def list_model_datasets() -> dict:
    """Return {name: config_entry} for all non-ground-truth datasets."""
    config = load_config()
    return {k: v for k, v in config.items() if v.get("type") != "ground_truth"}


def load_all_model_datasets() -> dict[str, pd.DataFrame]:
    """Load every model dataset. Returns {name: DataFrame}."""
    return {name: load_dataset(name) for name in list_model_datasets()}


def dataset_info(name: str) -> str:
    config = load_config()
    entry = config.get(name, {})
    parts = [name]
    if "description" in entry:
        parts.append(entry["description"])
    if "date" in entry:
        parts.append(entry["date"])
    return " | ".join(parts)
