"""Metrics computation for STS synergy analysis."""

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score, precision_recall_fscore_support, confusion_matrix
)

LABELS = [-1, 0, 1]
LABEL_NAMES = {-1: "Negative (-1)", 0: "Neutral (0)", 1: "Positive (+1)"}


# -- helpers ------------------------------------------------------------------

def _flatten(df: pd.DataFrame, exclude_diag: bool = True) -> np.ndarray:
    arr = df.values.astype(int)
    if exclude_diag:
        mask = ~np.eye(len(arr), dtype=bool)
        return arr[mask]
    return arr.flatten()


# -- main metrics -------------------------------------------------------------

def overall(pred_df: pd.DataFrame, truth_df: pd.DataFrame,
            exclude_diag: bool = True) -> dict:
    """Full classification metrics for a single dataset vs ground truth."""
    yp = _flatten(pred_df, exclude_diag)
    yt = _flatten(truth_df, exclude_diag)

    prec, rec, f1, sup = precision_recall_fscore_support(
        yt, yp, labels=LABELS, zero_division=0
    )
    cm = confusion_matrix(yt, yp, labels=LABELS)

    return {
        "accuracy":        float(accuracy_score(yt, yp)),
        "macro_f1":        float(np.mean(f1)),
        "weighted_f1":     float(np.average(f1, weights=sup)),
        "macro_precision": float(np.mean(prec)),
        "macro_recall":    float(np.mean(rec)),
        "per_class": {
            lbl: {
                "precision": float(prec[i]),
                "recall":    float(rec[i]),
                "f1":        float(f1[i]),
                "support":   int(sup[i]),
            }
            for i, lbl in enumerate(LABELS)
        },
        "confusion_matrix": cm,
        "n_total":   len(yp),
        "n_correct": int(np.sum(yp == yt)),
        "n_errors":  int(np.sum(yp != yt)),
    }


def per_card(pred_df: pd.DataFrame, truth_df: pd.DataFrame,
             exclude_diag: bool = True) -> pd.DataFrame:
    """Per-card metrics (row-wise). Returns a DataFrame indexed by card name."""
    cards = list(pred_df.index)
    rows = []
    for i, card in enumerate(cards):
        yp = pred_df.iloc[i].values.astype(int)
        yt = truth_df.iloc[i].values.astype(int)
        if exclude_diag:
            mask = np.ones(len(yp), dtype=bool)
            mask[i] = False
            yp, yt = yp[mask], yt[mask]

        _, _, f1, _ = precision_recall_fscore_support(
            yt, yp, labels=LABELS, zero_division=0
        )
        rows.append({
            "card":             card,
            "accuracy":         float(accuracy_score(yt, yp)),
            "macro_f1":         float(np.mean(f1)),
            "n_errors":         int(np.sum(yp != yt)),
            "false_pos_synergy": int(np.sum((yp == 1) & (yt != 1))),
            "false_neg_synergy": int(np.sum((yp != 1) & (yt == 1))),
            "false_pos_anti":   int(np.sum((yp == -1) & (yt != -1))),
            "false_neg_anti":   int(np.sum((yp != -1) & (yt == -1))),
            "n_total":          len(yp),
        })
    return pd.DataFrame(rows).set_index("card")


def per_card_as_b(pred_df: pd.DataFrame, truth_df: pd.DataFrame,
                  exclude_diag: bool = True) -> pd.DataFrame:
    """Per-card metrics when the card appears as Card B (column). Transposes and reuses per_card."""
    return per_card(pred_df.T, truth_df.T, exclude_diag)


def pair_table(pred_df: pd.DataFrame, truth_df: pd.DataFrame,
               extra: dict | None = None,
               exclude_diag: bool = True) -> pd.DataFrame:
    """
    Flat table of all card pairs with their predicted and ground-truth values.

    extra: optional {dataset_name: DataFrame} for multi-dataset comparison columns.
    """
    cards = list(pred_df.index)
    rows = []
    for i, ca in enumerate(cards):
        for j, cb in enumerate(cards):
            if exclude_diag and i == j:
                continue
            pv = int(pred_df.iloc[i, j])
            tv = int(truth_df.iloc[i, j])
            row = {
                "pair_id":      f"{ca}|{cb}",
                "card_a":       ca,
                "card_b":       cb,
                "ground_truth": tv,
                "predicted":    pv,
                "correct":      pv == tv,
                "error":        pv - tv,
            }
            if extra:
                for name, df in extra.items():
                    row[f"pred_{name}"] = int(df.iloc[i, j])
            rows.append(row)
    return pd.DataFrame(rows)


def compute_agreement(pred1_df: pd.DataFrame, pred2_df: pd.DataFrame,
                      truth_df: pd.DataFrame | None = None,
                      exclude_diag: bool = True) -> dict:
    """Agreement statistics between two prediction sets."""
    a1 = _flatten(pred1_df, exclude_diag)
    a2 = _flatten(pred2_df, exclude_diag)

    result = {"agreement_rate": float(np.mean(a1 == a2))}

    if truth_df is not None:
        at = _flatten(truth_df, exclude_diag)
        result.update({
            "both_correct":       float(np.mean((a1 == at) & (a2 == at))),
            "both_wrong":         float(np.mean((a1 != at) & (a2 != at))),
            "only_first_correct": float(np.mean((a1 == at) & (a2 != at))),
            "only_second_correct":float(np.mean((a1 != at) & (a2 == at))),
        })

    return result


def per_card_combined(pred_df: pd.DataFrame, truth_df: pd.DataFrame,
                      exclude_diag: bool = True) -> pd.DataFrame:
    cards = list(pred_df.index)
    rows = []
    for i, card in enumerate(cards):
        yp_a = pred_df.iloc[i].values.astype(int)
        yt_a = truth_df.iloc[i].values.astype(int)
        yp_b = pred_df.iloc[:, i].values.astype(int)
        yt_b = truth_df.iloc[:, i].values.astype(int)
        if exclude_diag:
            mask = np.ones(len(cards), dtype=bool)
            mask[i] = False
            yp_a, yt_a = yp_a[mask], yt_a[mask]
            yp_b, yt_b = yp_b[mask], yt_b[mask]
        yp = np.concatenate([yp_a, yp_b])
        yt = np.concatenate([yt_a, yt_b])
        _, _, f1, _ = precision_recall_fscore_support(yt, yp, labels=LABELS, zero_division=0)
        rows.append({
            "card": card,
            "accuracy": float(accuracy_score(yt, yp)),
            "macro_f1": float(np.mean(f1)),
            "n_errors": int(np.sum(yp != yt)),
            "n_total": len(yp),
        })
    return pd.DataFrame(rows).set_index("card")


def card_profile(card: str, role: str, pred_dfs: dict,
                 truth_df: pd.DataFrame) -> list:
    """
    role: 'a' = card is Card A (row), 'b' = card is Card B (column).
    Returns list of dicts sorted by gt value then other_card name:
      [{other_card, gt, model1_pred, model2_pred, ...}, ...]
    pred_dfs: {model_name: DataFrame}
    """
    cards = list(truth_df.index)
    rows = []
    for other in cards:
        if other == card:
            continue
        if role == 'a':
            gt = int(truth_df.loc[card, other])
            preds = {n: int(df.loc[card, other]) for n, df in pred_dfs.items()}
        else:
            gt = int(truth_df.loc[other, card])
            preds = {n: int(df.loc[other, card]) for n, df in pred_dfs.items()}
        row = {"other_card": other, "gt": gt}
        row.update(preds)
        rows.append(row)
    # Sort by gt descending then other_card
    rows.sort(key=lambda r: (-r["gt"], r["other_card"]))
    return rows


def error_breakdown(pred_df: pd.DataFrame, truth_df: pd.DataFrame,
                    exclude_diag: bool = True) -> dict:
    """Detailed breakdown of error types."""
    yp = _flatten(pred_df, exclude_diag)
    yt = _flatten(truth_df, exclude_diag)

    errors = yp != yt
    total = len(yp)

    breakdown = {}
    for true_lbl in LABELS:
        for pred_lbl in LABELS:
            if true_lbl == pred_lbl:
                continue
            key = f"true{true_lbl:+d}_pred{pred_lbl:+d}"
            count = int(np.sum((yt == true_lbl) & (yp == pred_lbl)))
            breakdown[key] = {"count": count, "pct": count / total * 100}

    return {
        "total_errors": int(np.sum(errors)),
        "error_rate":   float(np.mean(errors)),
        "breakdown":    breakdown,
    }
