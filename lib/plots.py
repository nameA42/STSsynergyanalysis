"""Visualization utilities for STS synergy analysis.

All plot functions save a PNG to the given output directory and return the file path.
"""

import matplotlib
matplotlib.use("Agg")  # non-interactive backend -- must be before pyplot import
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import numpy as np
import pandas as pd
from pathlib import Path

sns.set_theme(style="whitegrid", font_scale=0.9)
plt.rcParams.update({"figure.dpi": 100, "savefig.dpi": 150})

_COLORS = {
    "bad":    "#d73027",
    "poor":   "#fc8d59",
    "ok":     "#91cf60",
    "good":   "#1a9850",
    "blue":   "steelblue",
    "coral":  "coral",
    "navy":   "#1f3a6e",
}


# -- internal helpers ----------------------------------------------------------

def _save(fig, path: Path | str) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(p, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return str(p)


def _card_label_params(n_cards: int) -> dict:
    fs = max(4, 7 - max(0, n_cards - 50) // 10)
    return {"fontsize": fs, "rotation_x": 90, "rotation_y": 0}


# -- individual plot functions -------------------------------------------------

def confusion_matrix_plot(cm, labels, title: str, outdir, filename="confusion_matrix.png") -> str:
    label_names = ["Negative (-1)", "Neutral (0)", "Positive (+1)"]
    fig, ax = plt.subplots(figsize=(7, 5))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
                xticklabels=label_names, yticklabels=label_names,
                linewidths=0.5, ax=ax)
    ax.set_xlabel("Predicted", fontsize=11)
    ax.set_ylabel("Ground Truth", fontsize=11)
    ax.set_title(title, fontsize=13, fontweight="bold")
    return _save(fig, Path(outdir) / filename)


def prediction_heatmap(df: pd.DataFrame, title: str, outdir,
                       filename="prediction_heatmap.png") -> str:
    lp = _card_label_params(len(df))
    fig, ax = plt.subplots(figsize=(15, 13))
    sns.heatmap(df, cmap="RdYlGn", center=0, vmin=-1, vmax=1,
                xticklabels=True, yticklabels=True,
                linewidths=0.2, linecolor="lightgray", ax=ax)
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.tick_params(axis="x", rotation=lp["rotation_x"], labelsize=lp["fontsize"])
    ax.tick_params(axis="y", rotation=lp["rotation_y"], labelsize=lp["fontsize"])
    return _save(fig, Path(outdir) / filename)


def error_heatmap(pred_df: pd.DataFrame, truth_df: pd.DataFrame,
                  title: str, outdir, filename="error_heatmap.png") -> str:
    """Show where predictions deviate from ground truth (pred - truth)."""
    err = pred_df.astype(int) - truth_df.astype(int)
    lp = _card_label_params(len(err))
    cmap = sns.diverging_palette(220, 20, as_cmap=True)
    fig, ax = plt.subplots(figsize=(15, 13))
    sns.heatmap(err, cmap=cmap, center=0, vmin=-2, vmax=2,
                xticklabels=True, yticklabels=True,
                linewidths=0.2, linecolor="lightgray", ax=ax,
                cbar_kws={"label": "Error (pred - truth)"})
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.tick_params(axis="x", rotation=lp["rotation_x"], labelsize=lp["fontsize"])
    ax.tick_params(axis="y", rotation=lp["rotation_y"], labelsize=lp["fontsize"])
    return _save(fig, Path(outdir) / filename)


def per_card_accuracy_chart(pc_df: pd.DataFrame, title: str, outdir,
                            filename="per_card_accuracy.png") -> str:
    df = pc_df.sort_values("accuracy")
    mean_acc = df["accuracy"].mean()

    def _color(a):
        if a < 0.60: return _COLORS["bad"]
        if a < 0.75: return _COLORS["poor"]
        if a < 0.90: return _COLORS["ok"]
        return _COLORS["good"]

    colors = [_color(a) for a in df["accuracy"]]
    fig, ax = plt.subplots(figsize=(10, 14))
    bars = ax.barh(df.index, df["accuracy"] * 100, color=colors,
                   edgecolor="white", linewidth=0.5)
    ax.axvline(mean_acc * 100, color=_COLORS["navy"], linestyle="--", alpha=0.85,
               linewidth=1.5)

    for bar, acc in zip(bars, df["accuracy"]):
        ax.text(min(bar.get_width() + 0.6, 103), bar.get_y() + bar.get_height() / 2,
                f"{acc*100:.1f}%", va="center", fontsize=7)

    ax.set_xlim(0, 108)
    ax.set_xlabel("Accuracy (%)", fontsize=11)
    ax.set_title(title, fontsize=13, fontweight="bold")

    legend_handles = [
        mpatches.Patch(facecolor=_COLORS["bad"],  label="< 60%"),
        mpatches.Patch(facecolor=_COLORS["poor"], label="60-75%"),
        mpatches.Patch(facecolor=_COLORS["ok"],   label="75-90%"),
        mpatches.Patch(facecolor=_COLORS["good"], label=">= 90%"),
        plt.Line2D([0], [0], color=_COLORS["navy"], linestyle="--",
                   label=f"Mean {mean_acc*100:.1f}%"),
    ]
    ax.legend(handles=legend_handles, loc="lower right", fontsize=8)
    return _save(fig, Path(outdir) / filename)


def class_distribution(pred_df: pd.DataFrame, truth_df: pd.DataFrame,
                       title: str, outdir, filename="class_distribution.png") -> str:
    labels = [-1, 0, 1]
    names = ["Negative (-1)", "Neutral (0)", "Positive (+1)"]
    pf = pred_df.values.astype(int).flatten()
    tf = truth_df.values.astype(int).flatten()
    pc = [np.sum(pf == l) for l in labels]
    tc = [np.sum(tf == l) for l in labels]

    x, w = np.arange(3), 0.35
    fig, ax = plt.subplots(figsize=(8, 5))
    b1 = ax.bar(x - w/2, tc, w, label="Ground Truth", color=_COLORS["blue"], alpha=0.85)
    b2 = ax.bar(x + w/2, pc, w, label="Predicted",    color=_COLORS["coral"], alpha=0.85)
    for b in list(b1) + list(b2):
        ax.text(b.get_x() + b.get_width()/2, b.get_height() + 3,
                f"{int(b.get_height()):,}", ha="center", va="bottom", fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels(names, fontsize=10)
    ax.set_ylabel("Count", fontsize=11)
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.legend()
    return _save(fig, Path(outdir) / filename)


def metrics_comparison_bar(metrics_dict: dict, title: str, outdir,
                           filename="metrics_comparison.png") -> str:
    datasets = list(metrics_dict.keys())
    keys = ["accuracy", "macro_f1", "weighted_f1", "macro_precision", "macro_recall"]
    key_labels = ["Accuracy", "Macro F1", "Weighted F1", "Macro Prec.", "Macro Rec."]

    x = np.arange(len(keys))
    w = 0.75 / len(datasets)
    colors = plt.cm.Set2(np.linspace(0, 0.9, len(datasets)))

    fig, ax = plt.subplots(figsize=(12, 6))
    for i, (ds, m) in enumerate(metrics_dict.items()):
        vals = [m[k] for k in keys]
        offset = (i - len(datasets) / 2 + 0.5) * w
        bars = ax.bar(x + offset, vals, w, label=ds, color=colors[i], alpha=0.88)
        for bar, v in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.005,
                    f"{v:.3f}", ha="center", va="bottom", fontsize=7, rotation=45)

    ax.set_xticks(x)
    ax.set_xticklabels(key_labels, fontsize=10)
    ax.set_ylim(0, 1.15)
    ax.set_ylabel("Score", fontsize=11)
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.legend(fontsize=9)
    ax.axhline(1.0, color="gray", linestyle="--", alpha=0.3)
    return _save(fig, Path(outdir) / filename)


def per_card_comparison(pc_dfs: dict, title: str, outdir,
                        filename="per_card_comparison.png") -> str:
    """Grouped bar chart comparing per-card accuracy across datasets."""
    datasets = list(pc_dfs.keys())
    all_cards = list(list(pc_dfs.values())[0].index)

    # Sort cards by mean accuracy across datasets
    avg = pd.DataFrame({n: df["accuracy"] for n, df in pc_dfs.items()}).mean(axis=1)
    cards_sorted = avg.sort_values().index.tolist()

    y = np.arange(len(cards_sorted))
    w = 0.75 / len(datasets)
    colors = plt.cm.Set1(np.linspace(0, 0.8, len(datasets)))

    fig, ax = plt.subplots(figsize=(12, 14))
    for i, (ds, pc) in enumerate(pc_dfs.items()):
        vals = [pc.loc[c, "accuracy"] * 100 for c in cards_sorted]
        offset = (i - len(datasets) / 2 + 0.5) * w
        ax.barh(y + offset, vals, w, label=ds, color=colors[i], alpha=0.82)

    ax.set_yticks(y)
    ax.set_yticklabels(cards_sorted, fontsize=7)
    ax.set_xlim(0, 110)
    ax.set_xlabel("Accuracy (%)", fontsize=11)
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.legend(fontsize=9)
    ax.axvline(100, color="gray", linestyle="--", alpha=0.3)
    return _save(fig, Path(outdir) / filename)


def agreement_heatmap(datasets_dict: dict, title: str, outdir,
                      filename="agreement_heatmap.png") -> str:
    names = list(datasets_dict.keys())
    n = len(names)
    mat = np.zeros((n, n))
    for i, n1 in enumerate(names):
        for j, n2 in enumerate(names):
            a1 = datasets_dict[n1].values.astype(int).flatten()
            a2 = datasets_dict[n2].values.astype(int).flatten()
            mat[i, j] = float(np.mean(a1 == a2))

    df = pd.DataFrame(mat, index=names, columns=names)
    fig, ax = plt.subplots(figsize=(max(5, n + 2), max(4, n + 1)))
    sns.heatmap(df, annot=True, fmt=".3f", cmap="YlOrRd", vmin=0, vmax=1,
                linewidths=0.5, ax=ax, annot_kws={"size": 11})
    ax.set_title(title, fontsize=13, fontweight="bold")
    return _save(fig, Path(outdir) / filename)


def error_type_breakdown(breakdown_dict: dict, title: str, outdir,
                         filename="error_breakdown.png") -> str:
    """Bar chart of error types (e.g. true+1_pred0, true0_pred+1, etc.)."""
    keys = list(breakdown_dict["breakdown"].keys())
    counts = [breakdown_dict["breakdown"][k]["count"] for k in keys]
    pcts = [breakdown_dict["breakdown"][k]["pct"] for k in keys]

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(keys, counts, color=_COLORS["coral"], alpha=0.85, edgecolor="white")
    for bar, pct in zip(bars, pcts):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                f"{pct:.1f}%", ha="center", va="bottom", fontsize=8)
    ax.set_xlabel("Error Type (true -> predicted)", fontsize=11)
    ax.set_ylabel("Count", fontsize=11)
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.tick_params(axis="x", rotation=30, labelsize=8)
    return _save(fig, Path(outdir) / filename)


def delta_per_card(pc_df1: pd.DataFrame, pc_df2: pd.DataFrame,
                   name1: str, name2: str, title: str, outdir,
                   filename="delta_per_card.png") -> str:
    """Show accuracy change from dataset1 -> dataset2, sorted by delta."""
    delta = (pc_df2["accuracy"] - pc_df1["accuracy"]) * 100
    delta_sorted = delta.sort_values()

    colors = [_COLORS["good"] if v >= 0 else _COLORS["bad"] for v in delta_sorted]
    fig, ax = plt.subplots(figsize=(10, 14))
    ax.barh(delta_sorted.index, delta_sorted, color=colors,
            edgecolor="white", linewidth=0.5)
    ax.axvline(0, color="black", linewidth=0.8)
    ax.set_xlabel(f"Accuracy change (%) {name1} -> {name2}", fontsize=11)
    ax.set_title(title, fontsize=13, fontweight="bold")

    legend_handles = [
        mpatches.Patch(facecolor=_COLORS["good"], label=f"Improved in {name2}"),
        mpatches.Patch(facecolor=_COLORS["bad"],  label=f"Degraded in {name2}"),
    ]
    ax.legend(handles=legend_handles, fontsize=8)
    return _save(fig, Path(outdir) / filename)
