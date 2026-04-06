"""
lib/masks.py
============
Centralised mask definitions for all STS synergy analysis scripts.

Five masks:
  all           : every pair (5625)
  hard          : edge-case pairs ∪ uncertain pairs (decimal/integer GT sign flip)
  standard      : all − hard
  light_hard    : pairs touching the specified rows/cols − hard
  light_standard: all − hard − light_hard

Usage:
    from lib.masks import build_all_masks, LIGHT_HARD_ROWS, LIGHT_HARD_COLS
    masks = build_all_masks(gt, dec_gt, edge_mask)
    hard_pairs = masks['hard']
"""

from pathlib import Path
import numpy as np
import pandas as pd

# Cards whose rows/columns define the light_hard mask
LIGHT_HARD_ROWS = {'Havoc', 'True Grit', 'Sentinel', 'Berserk', 'Exhume'}
LIGHT_HARD_COLS = {'Havoc', 'True Grit', 'Sentinel', 'Double Tap', 'Fiend Fire'}

# Decimal values that qualify for the uncertain check
_HALF_VALS  = {0.5, -0.5}
_SOLID_VALS = {1.0, 1.5, 2.0, -1.0, -1.5, -2.0}


def get_uncertain_pairs(dec_gt: pd.DataFrame, int_gt: pd.DataFrame) -> set:
    """
    Pairs where decimal GT and integer GT have strictly opposite signs.
    Covers half_flipped (dec=±0.5) and solid_flipped (dec=±1/1.5/2).
    """
    uncertain = set()
    cards = dec_gt.index.tolist()
    for r in cards:
        for c in cards:
            if r not in int_gt.index or c not in int_gt.columns:
                continue
            dv = dec_gt.loc[r, c]
            iv = int_gt.loc[r, c]
            if pd.isna(dv):
                continue
            ds, is_ = np.sign(dv), np.sign(iv)
            if ds == 0 or is_ == 0 or is_ == ds:
                continue
            if dv in _HALF_VALS or dv in _SOLID_VALS:
                uncertain.add((r, c))
    return uncertain


def get_edge_pairs(edge_mask: pd.DataFrame) -> set:
    """All pairs where edge_mask == 1."""
    cards = edge_mask.index.tolist()
    return {(r, c) for r in cards for c in cards if edge_mask.loc[r, c] == 1.0}


def build_all_masks(
    int_gt: pd.DataFrame,
    dec_gt: pd.DataFrame,
    edge_mask: pd.DataFrame,
) -> dict:
    """
    Build all five pair-set masks. All DataFrames must be pre-aligned to the
    same common card index.

    Returns a dict with keys:
        'all', 'hard', 'standard', 'light_hard', 'light_standard'
    and metadata keys:
        '_edge_pairs', '_uncertain_pairs'
    """
    cards = int_gt.index.tolist()
    all_pairs = {(r, c) for r in cards for c in cards}

    edge_pairs = get_edge_pairs(edge_mask)
    uncertain  = get_uncertain_pairs(dec_gt, int_gt)
    hard       = edge_pairs | uncertain

    light_hard = (
        {(r, c) for r in cards for c in cards
         if (r in LIGHT_HARD_ROWS or c in LIGHT_HARD_COLS)}
        - hard
    )
    light_standard = all_pairs - hard - light_hard

    return {
        'all':            all_pairs,
        'hard':           hard,
        'standard':       all_pairs - hard,
        'light_hard':     light_hard,
        'light_standard': light_standard,
        '_edge_pairs':    edge_pairs,
        '_uncertain':     uncertain,
    }


def load_and_align(gt, dec_gt_path: Path, edge_mask_path: Path):
    """
    Load decimal GT and edge mask CSVs, align everything to the common card
    index shared with `gt` (the integer GT DataFrame from lib.loader).

    Returns (gt_aligned, dec_aligned, edge_aligned, common_index).
    """
    dec_raw  = pd.read_csv(dec_gt_path,  index_col=0)
    edge_raw = pd.read_csv(edge_mask_path, index_col=0)

    common = gt.index.intersection(dec_raw.index).intersection(edge_raw.index)
    gt_a   = gt.loc[common, common]
    dec_a  = dec_raw.loc[common, common]
    edge_a = edge_raw.loc[common, common].fillna(0)

    return gt_a, dec_a, edge_a, common


# Convenience paths (relative to project root)
DECIMAL_GT_PATH = (
    Path(__file__).resolve().parent.parent
    / "data" / "ground_truth_decimals"
    / "StS Synergies - All Cards (1).csv"
)
EDGE_MASK_PATH = (
    Path(__file__).resolve().parent.parent
    / "data" / "Edge_case_mask"
    / "StS Synergies 3 Class - Edge Case Mask.csv"
)
