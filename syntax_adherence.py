#!/usr/bin/env python3
"""
syntax_adherence.py
===================
Measures how closely model responses adhere to the expected chain-of-thought
format (paper §VI-C) and whether deviations correlate with prediction errors.

Expected response sections:
  1. Card Description  — word-for-word recitation of card stats/effects
  2. Order of Events   — sequence of what happens when cards are played
  3. Synergy Analysis  — core analysis of the interaction
  4. Conclusion        — summary and classification
  5. Final Score       — the numeric verdict (-1, 0, or 1)

The adherence score is a continuous 0–1 metric (% of sections present),
NOT binary. Order adherence (are sections in the right sequence?) is computed
separately and reported alongside.

Usage:
    python syntax_adherence.py --model gpt4o
    python syntax_adherence.py --all
    python syntax_adherence.py --model gpt4o gpt54 --output results/
"""

import argparse
import sys
import re
import textwrap
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats as scipy_stats

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from lib import logs as log_parser
from lib.loader import load_dataset, list_model_datasets, get_ground_truth_name

# ── Expected format sections ─────────────────────────────────────────────────
# Drawn from paper §VI-C and the actual response structure in the log files.
# Each entry: (section_name, [regex_patterns_any_of])
# Patterns are searched line-by-line (lowercased). Final Score also checks for
# a bare numeric line.
SECTIONS = [
    ("Card Description", [
        r"card\s+descriptions?",
        r"\*\*card\s*[ab\d]\*\*",        # **Card A** or **Card 1**
        r"^-\s*(type|cost)\s*:",          # - Type: ... / - Cost: ...
        r"card [12ab] \([^\)]+\) -",      # Card 1 (Attack Type) - Cost ...
    ]),
    ("Order of Events", [
        r"order of events",
        r"order of play",
        r"sequence of events",
        r"playing card [ab\d12] (first|next|second)",
        r"^\*\*playing",
    ]),
    ("Synergy Analysis", [
        r"synergy analysis",
        r"analyzing the combo",
        r"combo analysis",
        r"^###\s+anal",
        r"^-\s*the (combo|synergy) (is|creates|provides|results)",
    ]),
    ("Conclusion", [
        r"conclusion",
        r"in summary",
        r"to summarize",
        r"^###\s+conclusion",
    ]),
    ("Final Score", [
        r"final\s+score",
        r"^score[:\s]*[-]?[01]\s*$",
    ]),
]

SECTION_NAMES = [s[0] for s in SECTIONS]
_BARE_SCORE_RE = re.compile(r"^-?[01]\s*$")


# ── Adherence measurement ─────────────────────────────────────────────────────

def measure_adherence(response: str) -> dict:
    """
    Measure how closely a response follows the expected format.

    Returns dict:
      section_present  : {section_name: bool}
      adherence_score  : float 0-1  (fraction of sections found)
      order_score      : float 0-1  (found sections in correct relative order)
      combined_score   : float 0-1  (0.7 * adherence + 0.3 * order)
    """
    lines = response.splitlines()
    presence: dict[str, bool] = {}
    first_line: dict[str, float] = {}   # line index of first match

    for sec_name, patterns in SECTIONS:
        found_at = None
        for i, line in enumerate(lines):
            ll = line.strip().lower()
            for pat in patterns:
                if re.search(pat, ll):
                    found_at = i
                    break
            if found_at is not None:
                break

        # Special case: Final Score — also accept a bare "-1", "0", or "1" line
        if found_at is None and sec_name == "Final Score":
            for i, line in enumerate(lines):
                if _BARE_SCORE_RE.match(line.strip()):
                    found_at = i
                    break

        presence[sec_name] = found_at is not None
        first_line[sec_name] = float(found_at) if found_at is not None else float("inf")

    adherence_score = sum(presence.values()) / len(SECTIONS)

    # Order score: among the sections that ARE present, are they in the right order?
    found_pairs = sorted(
        [(pos, name) for name, pos in first_line.items() if pos < float("inf")]
    )
    found_names = [name for _, name in found_pairs]

    if len(found_names) <= 1:
        order_score = 1.0
    else:
        n = len(found_names)
        correct_pairs = sum(
            1 for i in range(n) for j in range(i + 1, n)
            if SECTION_NAMES.index(found_names[i]) < SECTION_NAMES.index(found_names[j])
        )
        total_pairs = n * (n - 1) // 2
        order_score = correct_pairs / total_pairs if total_pairs > 0 else 1.0

    return {
        "section_present": presence,
        "adherence_score": adherence_score,
        "order_score":     order_score,
        "combined_score":  0.7 * adherence_score + 0.3 * order_score,
    }


# ── Data loading ──────────────────────────────────────────────────────────────

def find_log_path(ds_name: str) -> Path | None:
    from lib.loader import load_config, BASE_DIR
    config = load_config()
    entry = config.get(ds_name)
    if not entry or entry.get("type") == "ground_truth":
        return None
    csv_path = BASE_DIR / entry["file"]
    logs = list(csv_path.parent.glob("*.log"))
    return logs[0] if logs else None


def analyze_model(model_name: str) -> pd.DataFrame | None:
    """
    Parse log + predictions for one model.
    Returns DataFrame with per-pair adherence + correctness columns.
    """
    log_path = find_log_path(model_name)
    if log_path is None:
        print(f"  ✗ No log file found for '{model_name}'")
        return None

    gt_df   = load_dataset(get_ground_truth_name())
    pred_df = load_dataset(model_name)

    print(f"  Log  : {log_path.name}")
    responses = log_parser.parse_log(log_path)
    print(f"  Pairs: {len(responses)} responses parsed")

    rows = []
    for pair_id, text in responses.items():
        if "|" not in pair_id:
            continue
        ca, cb = pair_id.split("|", 1)
        try:
            gt_val   = int(gt_df.loc[ca, cb])
            pred_val = int(pred_df.loc[ca, cb])
        except (KeyError, ValueError):
            continue

        adh = measure_adherence(text)
        row = {
            "pair_id":         pair_id,
            "card_a":          ca,
            "card_b":          cb,
            "ground_truth":    gt_val,
            "prediction":      pred_val,
            "correct":         int(gt_val == pred_val),
            "adherence_score": adh["adherence_score"],
            "order_score":     adh["order_score"],
            "combined_score":  adh["combined_score"],
            "response_len":    len(text),
        }
        for sec in SECTION_NAMES:
            col = f"has_{sec.lower().replace(' ', '_')}"
            row[col] = int(adh["section_present"][sec])
        rows.append(row)

    if not rows:
        print("  ✗ No valid pairs found")
        return None

    return pd.DataFrame(rows)


# ── Statistics ────────────────────────────────────────────────────────────────

def _safe_pbr(x, y):
    """Point-biserial r; returns (nan, nan) if x is constant."""
    if x.std() == 0 or y.std() == 0:
        return float("nan"), float("nan")
    return scipy_stats.pointbiserialr(y, x)


def compute_stats(df: pd.DataFrame, model_name: str) -> dict:
    correct  = df["correct"]
    adh      = df["adherence_score"]
    combined = df["combined_score"]

    n          = len(df)
    n_correct  = int(correct.sum())
    n_wrong    = n - n_correct
    accuracy   = n_correct / n

    r_adh,  p_adh  = _safe_pbr(adh,               correct)
    r_comb, p_comb = _safe_pbr(combined,           correct)
    r_len,  p_len  = _safe_pbr(df["response_len"], correct)

    # Mean adherence per outcome group
    adh_correct = adh[correct == 1].mean()
    adh_wrong   = adh[correct == 0].mean()

    # Section presence rates per group
    sec_cols = [f"has_{s.lower().replace(' ', '_')}" for s in SECTION_NAMES]
    rates_c  = df[correct == 1][sec_cols].mean().to_dict()
    rates_w  = df[correct == 0][sec_cols].mean().to_dict()

    # Adherence variance for correct vs wrong
    var_correct = adh[correct == 1].var()
    var_wrong   = adh[correct == 0].var()

    return dict(
        model        = model_name,
        n_total      = n,
        n_correct    = n_correct,
        n_wrong      = n_wrong,
        accuracy     = accuracy,
        mean_adh     = adh.mean(),
        std_adh      = adh.std(),
        var_adh      = adh.var(),
        adh_correct  = adh_correct,
        adh_wrong    = adh_wrong,
        var_correct  = var_correct,
        var_wrong    = var_wrong,
        adh_delta    = adh_correct - adh_wrong,
        r_adh        = r_adh,
        p_adh        = p_adh,
        r_combined   = r_comb,
        p_combined   = p_comb,
        r_len        = r_len,
        p_len        = p_len,
        rates_correct = rates_c,
        rates_wrong   = rates_w,
        sec_cols      = sec_cols,
    )


# ── Figures ───────────────────────────────────────────────────────────────────

CORRECT_COLOR   = "#16a34a"
INCORRECT_COLOR = "#dc2626"
NEUTRAL_COLOR   = "#3b82f6"


def _sig_label(p: float) -> str:
    if np.isnan(p):   return "N/A"
    if p < 0.001:     return "***"
    if p < 0.01:      return "**"
    if p < 0.05:      return "*"
    return "ns"


def make_figures(results: list[tuple[str, pd.DataFrame, dict]], output_dir: Path):
    n = len(results)
    w = max(n, 1)

    # ── Fig 1: Violin — adherence distribution by outcome ────────────────────
    fig, axes = plt.subplots(1, w, figsize=(5 * w, 5), squeeze=False)
    fig.suptitle("Adherence Score Distribution: Correct vs Incorrect",
                 fontsize=13, fontweight="bold")

    for ax, (name, df, st) in zip(axes[0], results):
        groups = [
            df[df.correct == 1]["adherence_score"].values,
            df[df.correct == 0]["adherence_score"].values,
        ]
        parts = ax.violinplot(groups, positions=[1, 2], showmedians=True, showmeans=True)
        for pc in parts["bodies"]:
            pc.set_alpha(0.6)
        parts["bodies"][0].set_facecolor(CORRECT_COLOR)
        parts["bodies"][1].set_facecolor(INCORRECT_COLOR)
        ax.set_xticks([1, 2])
        ax.set_xticklabels([
            f"Correct\n(n={st['n_correct']:,})",
            f"Incorrect\n(n={st['n_wrong']:,})",
        ])
        ax.set_ylim(-0.05, 1.15)
        ax.set_ylabel("Adherence Score")
        ax.set_title(name)
        # Annotate means
        ax.hlines(st["adh_correct"], 0.75, 1.25,
                  colors=CORRECT_COLOR, linestyles="--", linewidth=1.5, label=f"μ={st['adh_correct']:.2f}")
        ax.hlines(st["adh_wrong"],   1.75, 2.25,
                  colors=INCORRECT_COLOR, linestyles="--", linewidth=1.5, label=f"μ={st['adh_wrong']:.2f}")
        ax.text(0.04, 0.97,
                f"r={st['r_adh']:.3f}  p={st['p_adh']:.3g} {_sig_label(st['p_adh'])}\n"
                f"Δμ={st['adh_delta']:+.3f}",
                transform=ax.transAxes, fontsize=8, va="top",
                bbox=dict(boxstyle="round", fc="white", alpha=0.7))
        ax.legend(fontsize=7, loc="lower right")

    plt.tight_layout()
    fig.savefig(output_dir / "fig1_adherence_violin.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  fig1_adherence_violin.png")

    # ── Fig 2: Section presence rates ────────────────────────────────────────
    fig, axes = plt.subplots(1, w, figsize=(6 * w, 5), squeeze=False)
    fig.suptitle("Section Presence Rate by Outcome",
                 fontsize=13, fontweight="bold")

    x = np.arange(len(SECTION_NAMES))
    bar_w = 0.35
    short = [s.replace(" ", "\n") for s in SECTION_NAMES]

    for ax, (name, df, st) in zip(axes[0], results):
        rc = [st["rates_correct"].get(c, 0) for c in st["sec_cols"]]
        rw = [st["rates_wrong"].get(c, 0)   for c in st["sec_cols"]]
        ax.bar(x - bar_w / 2, rc, bar_w, label="Correct",   color=CORRECT_COLOR,   alpha=0.85)
        ax.bar(x + bar_w / 2, rw, bar_w, label="Incorrect", color=INCORRECT_COLOR, alpha=0.85)
        ax.set_xticks(x)
        ax.set_xticklabels(short, fontsize=8)
        ax.set_ylim(0, 1.18)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
        ax.set_ylabel("Presence Rate")
        ax.set_title(name)
        ax.legend(fontsize=8)
        # Delta annotations
        for xi, (c, wv) in enumerate(zip(rc, rw)):
            delta = c - wv
            ax.text(xi, max(c, wv) + 0.03, f"{delta:+.0%}",
                    ha="center", va="bottom", fontsize=7,
                    color=CORRECT_COLOR if delta >= 0 else INCORRECT_COLOR)

    plt.tight_layout()
    fig.savefig(output_dir / "fig2_section_presence.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  fig2_section_presence.png")

    # ── Fig 3: Scatter — adherence vs correct (jittered) ─────────────────────
    fig, axes = plt.subplots(1, w, figsize=(5 * w, 4), squeeze=False)
    fig.suptitle("Adherence Score vs Correctness (jittered)",
                 fontsize=13, fontweight="bold")

    for ax, (name, df, st) in zip(axes[0], results):
        jitter = np.random.uniform(-0.06, 0.06, size=len(df))
        colors = df["correct"].map({1: CORRECT_COLOR, 0: INCORRECT_COLOR})
        ax.scatter(df["adherence_score"], df["correct"] + jitter,
                   c=colors, alpha=0.12, s=8, linewidths=0)
        # OLS line — skip if adherence is constant
        x_vals = df["adherence_score"].values
        y_vals = df["correct"].values.astype(float)
        r_val  = st["r_adh"]
        if np.isnan(r_val):
            label = "r=N/A (constant)"
        else:
            slope, intercept, *_ = scipy_stats.linregress(x_vals, y_vals)
            xs = np.linspace(x_vals.min(), x_vals.max(), 200)
            ax.plot(xs, slope * xs + intercept, color="navy", linewidth=2)
            label = f"r={r_val:.3f} {_sig_label(st['p_adh'])}"
        ax.set_xlabel("Adherence Score")
        ax.set_yticks([0, 1])
        ax.set_yticklabels(["Incorrect", "Correct"])
        ax.set_title(f"{name}\n{label}")
        ax.set_title(name)
        ax.text(0.04, 0.04, label, transform=ax.transAxes, fontsize=8,
                va="bottom", bbox=dict(boxstyle="round", fc="white", alpha=0.7))

    plt.tight_layout()
    fig.savefig(output_dir / "fig3_scatter.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  fig3_scatter.png")

    # ── Fig 4: Summary bar — mean adherence correct vs wrong ─────────────────
    fig, ax = plt.subplots(figsize=(max(6, 2.5 * w), 4))
    names  = [r[0] for r in results]
    adh_c  = [r[2]["adh_correct"] for r in results]
    adh_w  = [r[2]["adh_wrong"]   for r in results]
    xi     = np.arange(len(names))

    b_c = ax.bar(xi - bar_w / 2, adh_c, bar_w, label="Correct",   color=CORRECT_COLOR,   alpha=0.85)
    b_w = ax.bar(xi + bar_w / 2, adh_w, bar_w, label="Incorrect", color=INCORRECT_COLOR, alpha=0.85)

    for bar in (*b_c, *b_w):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.005,
                f"{bar.get_height():.3f}", ha="center", va="bottom", fontsize=8)
    # Correlation annotations above bars
    for i, (_, _, st) in enumerate(results):
        ax.text(i, max(adh_c[i], adh_w[i]) + 0.05,
                f"r={st['r_adh']:.3f}\n{_sig_label(st['p_adh'])}",
                ha="center", va="bottom", fontsize=8, color="navy")

    ax.set_xticks(xi)
    ax.set_xticklabels(names, rotation=20, ha="right")
    ax.set_ylabel("Mean Adherence Score")
    ax.set_ylim(0, 1.15)
    ax.set_title("Mean Format Adherence: Correct vs Incorrect Predictions")
    ax.legend()

    plt.tight_layout()
    fig.savefig(output_dir / "fig4_mean_adherence_bar.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  fig4_mean_adherence_bar.png")

    # ── Fig 5: Response length distribution ──────────────────────────────────
    fig, axes = plt.subplots(1, w, figsize=(5 * w, 4), squeeze=False)
    fig.suptitle("Response Length vs Correctness",
                 fontsize=13, fontweight="bold")

    for ax, (name, df, st) in zip(axes[0], results):
        groups = [
            df[df.correct == 1]["response_len"].values,
            df[df.correct == 0]["response_len"].values,
        ]
        bp = ax.boxplot(groups, tick_labels=[
            f"Correct\n(μ={groups[0].mean():.0f})",
            f"Incorrect\n(μ={groups[1].mean():.0f})",
        ], patch_artist=True,
            boxprops=dict(facecolor="#e0f2fe"),
            medianprops=dict(color="navy", linewidth=2),
            flierprops=dict(marker=".", alpha=0.2, markersize=3))
        ax.set_title(name)
        ax.set_ylabel("Response length (chars)")
        ax.text(0.04, 0.97,
                f"r={st['r_len']:.3f}  p={st['p_len']:.3g} {_sig_label(st['p_len'])}",
                transform=ax.transAxes, fontsize=8, va="top",
                bbox=dict(boxstyle="round", fc="white", alpha=0.7))

    plt.tight_layout()
    fig.savefig(output_dir / "fig5_response_length.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  fig5_response_length.png")

    # ── Fig 6: Variance in adherence score ───────────────────────────────────
    fig, ax = plt.subplots(figsize=(max(6, 2.5 * w), 4))
    vars_c = [r[2]["var_correct"] for r in results]
    vars_w = [r[2]["var_wrong"]   for r in results]

    b_c = ax.bar(xi - bar_w / 2, vars_c, bar_w, label="Correct",   color=CORRECT_COLOR,   alpha=0.85)
    b_w = ax.bar(xi + bar_w / 2, vars_w, bar_w, label="Incorrect", color=INCORRECT_COLOR, alpha=0.85)
    for bar in (*b_c, *b_w):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.0005,
                f"{bar.get_height():.4f}", ha="center", va="bottom", fontsize=8)

    ax.set_xticks(xi)
    ax.set_xticklabels(names, rotation=20, ha="right")
    ax.set_ylabel("Adherence Score Variance")
    ax.set_title("Adherence Score Variance: Correct vs Incorrect Predictions")
    ax.legend()

    plt.tight_layout()
    fig.savefig(output_dir / "fig6_adherence_variance.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  fig6_adherence_variance.png")

    # ── Fig 7: Correlation summary across models ──────────────────────────────
    if len(results) > 1:
        fig, ax = plt.subplots(figsize=(max(5, 2 * w), 4))
        rs = [r[2]["r_adh"] for r in results]
        colors = [CORRECT_COLOR if r > 0 else INCORRECT_COLOR for r in rs]
        bars = ax.bar(xi, rs, color=colors, alpha=0.85, edgecolor="white")
        ax.axhline(0, color="black", linewidth=0.8)
        ax.set_xticks(xi)
        ax.set_xticklabels(names, rotation=20, ha="right")
        ax.set_ylabel("Point-biserial r")
        ax.set_title("Correlation: Format Adherence ↔ Prediction Correctness")
        for i, (bar, st) in enumerate(zip(bars, [r[2] for r in results])):
            y = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2,
                    y + (0.003 if y >= 0 else -0.008),
                    f"{y:.3f}\n{_sig_label(st['p_adh'])}",
                    ha="center", va="bottom" if y >= 0 else "top", fontsize=8)

        plt.tight_layout()
        fig.savefig(output_dir / "fig7_correlation_summary.png", dpi=150, bbox_inches="tight")
        plt.close(fig)
        print("  fig7_correlation_summary.png")


# ── Report ────────────────────────────────────────────────────────────────────

def write_report(results: list[tuple[str, pd.DataFrame, dict]], output_dir: Path):
    lines = [
        "# Format Adherence Analysis",
        "",
        "How closely do model responses follow the expected chain-of-thought format",
        "(paper §VI-C), and does adherence correlate with prediction correctness?",
        "",
        "## Expected Sections",
        "",
    ]
    for i, (sec, _) in enumerate(SECTIONS, 1):
        lines.append(f"  {i}. **{sec}**")

    lines += [
        "",
        "> **Adherence score**: fraction of expected sections found (0–1, continuous).",
        "> **Order score**: are found sections in the right relative order? (0–1).",
        "> **Correlation**: point-biserial r between adherence and binary correctness.",
        "",
        "---",
        "",
    ]

    for name, df, st in results:
        sig = _sig_label(st["p_adh"])
        lines += [
            f"## {name}",
            "",
            f"| | Value |",
            f"|--|--|",
            f"| Pairs analyzed | {st['n_total']:,} |",
            f"| Accuracy | {st['accuracy']:.1%} ({st['n_correct']:,} correct / {st['n_wrong']:,} wrong) |",
            f"| Mean adherence (all) | {st['mean_adh']:.3f} ± {st['std_adh']:.3f} |",
            f"| Variance in adherence (all) | {st['var_adh']:.4f} |",
            f"| Mean adherence — correct | {st['adh_correct']:.3f} (var={st['var_correct']:.4f}) |",
            f"| Mean adherence — incorrect | {st['adh_wrong']:.3f} (var={st['var_wrong']:.4f}) |",
            f"| Adherence delta (correct − incorrect) | {st['adh_delta']:+.3f} |",
            "",
            "### Correlation with Correctness",
            "",
            "| Metric | r | p-value | Significance |",
            "|--------|---|---------|--------------|",
            f"| Adherence score | {st['r_adh']:.4f} | {st['p_adh']:.4g} | {sig} |",
            f"| Combined score  | {st['r_combined']:.4f} | {st['p_combined']:.4g} | {_sig_label(st['p_combined'])} |",
            f"| Response length | {st['r_len']:.4f} | {st['p_len']:.4g} | {_sig_label(st['p_len'])} |",
            "",
            "### Section Presence Rates",
            "",
            "| Section | Correct | Incorrect | Δ |",
            "|---------|---------|-----------|---|",
        ]
        for sec in SECTION_NAMES:
            col = f"has_{sec.lower().replace(' ', '_')}"
            rc  = st["rates_correct"].get(col, 0)
            rw  = st["rates_wrong"].get(col, 0)
            delta = rc - rw
            arrow = "↑" if delta > 0.01 else ("↓" if delta < -0.01 else "—")
            lines.append(f"| {sec} | {rc:.1%} | {rw:.1%} | {delta:+.1%} {arrow} |")

        lines += ["", "---", ""]

    path = output_dir / "report.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  report.md")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description="Measure format adherence vs prediction correctness"
    )
    grp = ap.add_mutually_exclusive_group(required=True)
    grp.add_argument("--model", nargs="+", metavar="NAME",
                     help="Model name(s) from datasets.json (e.g. gpt4o gpt54)")
    grp.add_argument("--all",   action="store_true",
                     help="Run on all models that have log files")
    ap.add_argument("--output", default="adherence_results",
                    help="Output directory (default: adherence_results/)")
    ap.add_argument("--seed", type=int, default=42,
                    help="Random seed for scatter jitter (default: 42)")
    args = ap.parse_args()

    np.random.seed(args.seed)

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    available = list_model_datasets()

    if args.all:
        model_names = list(available.keys())
    else:
        bad = [m for m in args.model if m not in available]
        if bad:
            print(f"Unknown model(s): {bad}")
            print(f"Available: {list(available.keys())}")
            sys.exit(1)
        model_names = args.model

    print(f"\n{'='*60}")
    print(f"  Syntax Adherence Analysis")
    print(f"  Models : {', '.join(model_names)}")
    print(f"  Output : {out}/")
    print(f"{'='*60}\n")

    results: list[tuple[str, pd.DataFrame, dict]] = []

    for name in model_names:
        print(f"[{name}]")
        df = analyze_model(name)
        if df is None:
            print()
            continue
        st = compute_stats(df, name)
        results.append((name, df, st))
        df.to_csv(out / f"{name}_adherence.csv", index=False)
        print(f"  Saved {name}_adherence.csv")
        print()

    if not results:
        print("No results — check that log files exist next to CSV files.")
        sys.exit(1)

    print("Saving figures...")
    make_figures(results, out)

    print("\nWriting report...")
    write_report(results, out)

    # Console summary table
    print(f"\n{'='*75}")
    print(f"  Summary")
    print(f"{'='*75}")
    hdr = f"{'Model':<16} {'Acc':>6} {'Adh(all)':>9} {'Adh(ok)':>8} {'Adh(err)':>9} {'dAdh':>6} {'r':>7} {'sig':>4}"
    print(hdr)
    print("-" * 75)
    for name, _, st in results:
        print(
            f"{name:<16} {st['accuracy']:>6.1%} {st['mean_adh']:>9.3f} "
            f"{st['adh_correct']:>8.3f} {st['adh_wrong']:>9.3f} "
            f"{st['adh_delta']:>+6.3f} {st['r_adh']:>7.3f} {_sig_label(st['p_adh']):>4}"
        )
    print("=" * 75)
    print(f"\nAll output in: {out}/")


if __name__ == "__main__":
    main()
