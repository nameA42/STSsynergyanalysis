"""Interactive Plotly chart generation for the STS Synergy web app.

All functions return a JSON string (fig.to_json()) ready to embed in templates.
"""

import json
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import plotly.utils


def _j(fig) -> str:
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


def _base_layout(**kwargs):
    base = dict(
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Inter, -apple-system, sans-serif", size=12, color="#1e293b"),
        margin=dict(l=20, r=20, t=50, b=20),
        hoverlabel=dict(bgcolor="white", bordercolor="#e2e8f0", font_size=12),
    )
    base.update(kwargs)
    return base


# ── Synergy heatmaps ──────────────────────────────────────────────────────────

def synergy_heatmap(df: pd.DataFrame, title: str) -> str:
    """75x75 prediction heatmap. Cells are clickable (handled in JS)."""
    cards = list(df.index)

    # Build hover text
    hover = [
        [f"<b>{cards[i]} → {cards[j]}</b><br>Value: {int(df.iloc[i, j])}"
         for j in range(len(cards))]
        for i in range(len(cards))
    ]

    colorscale = [
        [0.0,  "#dc2626"],   # -1 red
        [0.5,  "#f1f5f9"],   # 0  near-white
        [1.0,  "#16a34a"],   # +1 green
    ]

    fig = go.Figure(go.Heatmap(
        z=df.values.tolist(),
        x=cards, y=cards,
        colorscale=colorscale,
        zmid=0, zmin=-1, zmax=1,
        text=hover,
        hovertemplate="%{text}<extra></extra>",
        colorbar=dict(
            tickvals=[-1, 0, 1],
            ticktext=["Anti-synergy (-1)", "Neutral (0)", "Synergy (+1)"],
            thickness=14, len=0.6,
        ),
        xgap=0.5, ygap=0.5,
    ))

    fig.update_layout(
        **_base_layout(
            title=dict(text=title, font_size=15),
            height=780,
            xaxis=dict(tickangle=90, tickfont_size=7, side="bottom"),
            yaxis=dict(tickfont_size=7, autorange="reversed"),
            margin=dict(l=130, r=100, t=60, b=140),
        )
    )
    return _j(fig)


def error_heatmap(pred_df: pd.DataFrame, truth_df: pd.DataFrame, title: str) -> str:
    """Error map (pred - truth). Clickable to navigate to browse."""
    err = pred_df.astype(int) - truth_df.astype(int)
    cards = list(err.index)

    hover = [
        [f"<b>{cards[i]} → {cards[j]}</b><br>Error: {int(err.iloc[i, j]):+d}<br>"
         f"GT={int(truth_df.iloc[i, j])}  Pred={int(pred_df.iloc[i, j])}"
         for j in range(len(cards))]
        for i in range(len(cards))
    ]

    colorscale = [
        [0.0,  "#7c3aed"],  # -2
        [0.25, "#dc2626"],  # -1
        [0.5,  "#f8fafc"],  #  0
        [0.75, "#f97316"],  # +1
        [1.0,  "#b45309"],  # +2
    ]

    fig = go.Figure(go.Heatmap(
        z=err.values.tolist(),
        x=cards, y=cards,
        colorscale=colorscale,
        zmid=0, zmin=-2, zmax=2,
        text=hover,
        hovertemplate="%{text}<extra></extra>",
        colorbar=dict(
            tickvals=[-2, -1, 0, 1, 2],
            ticktext=["-2", "-1", "0", "+1", "+2"],
            title=dict(text="Error", side="right"),
            thickness=14, len=0.6,
        ),
        xgap=0.5, ygap=0.5,
    ))

    fig.update_layout(
        **_base_layout(
            title=dict(text=title, font_size=15),
            height=780,
            xaxis=dict(tickangle=90, tickfont_size=7, side="bottom"),
            yaxis=dict(tickfont_size=7, autorange="reversed"),
            margin=dict(l=130, r=100, t=60, b=140),
        )
    )
    return _j(fig)


# ── Confusion matrix ──────────────────────────────────────────────────────────

def confusion_matrix(cm, labels, title: str) -> str:
    label_names = ["Negative (-1)", "Neutral (0)", "Positive (+1)"]
    total = cm.sum()

    # Text: count + percentage
    text = [
        [f"<b>{cm[i, j]:,}</b><br>({cm[i, j] / total * 100:.1f}%)"
         for j in range(3)]
        for i in range(3)
    ]

    fig = go.Figure(go.Heatmap(
        z=cm.tolist(),
        x=label_names,
        y=label_names,
        colorscale="Blues",
        text=text,
        texttemplate="%{text}",
        hovertemplate="Truth: <b>%{y}</b><br>Predicted: <b>%{x}</b><br>Count: %{z:,}<extra></extra>",
        showscale=False,
        xgap=2, ygap=2,
    ))

    fig.update_layout(
        **_base_layout(
            title=dict(text=title, font_size=15),
            height=380,
            xaxis=dict(title="Predicted", side="bottom", tickfont_size=11),
            yaxis=dict(title="Ground Truth", autorange="reversed", tickfont_size=11),
            margin=dict(l=130, r=20, t=60, b=80),
        )
    )
    return _j(fig)


# ── Distribution / breakdown charts ──────────────────────────────────────────

def class_distribution(pred_df: pd.DataFrame, truth_df: pd.DataFrame, title: str) -> str:
    labels = [-1, 0, 1]
    names = ["Negative (−1)", "Neutral (0)", "Positive (+1)"]
    pf = pred_df.values.astype(int).flatten()
    tf = truth_df.values.astype(int).flatten()
    pc = [int(np.sum(pf == l)) for l in labels]
    tc = [int(np.sum(tf == l)) for l in labels]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Ground Truth", x=names, y=tc,
        marker_color="#2563eb", opacity=0.85,
        text=tc, textposition="outside",
        hovertemplate="%{x}<br>Count: %{y:,}<extra>Ground Truth</extra>",
    ))
    fig.add_trace(go.Bar(
        name="Predicted", x=names, y=pc,
        marker_color="#ea580c", opacity=0.85,
        text=pc, textposition="outside",
        hovertemplate="%{x}<br>Count: %{y:,}<extra>Predicted</extra>",
    ))

    fig.update_layout(
        **_base_layout(
            title=dict(text=title, font_size=15),
            barmode="group", height=360,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
            yaxis=dict(title="Count"),
            margin=dict(l=60, r=20, t=60, b=60),
        )
    )
    return _j(fig)


def error_breakdown(eb: dict, title: str) -> str:
    bd = eb["breakdown"]
    rows = sorted(
        [(k, v) for k, v in bd.items() if v["count"] > 0],
        key=lambda x: -x[1]["count"]
    )

    def readable(k):
        return k.replace("true", "GT=").replace("_pred", " → Pred=").replace("+0", "0")

    keys   = [readable(r[0]) for r in rows]
    counts = [r[1]["count"] for r in rows]
    pcts   = [r[1]["pct"] for r in rows]

    color_map = {
        "GT=+1 → Pred=0":  "#f97316",
        "GT=+1 → Pred=-1": "#dc2626",
        "GT=0 → Pred=+1":  "#84cc16",
        "GT=0 → Pred=-1":  "#94a3b8",
        "GT=-1 → Pred=0":  "#a855f7",
        "GT=-1 → Pred=+1": "#7c3aed",
    }
    colors = [color_map.get(k, "#64748b") for k in keys]

    fig = go.Figure(go.Bar(
        x=keys, y=counts,
        marker_color=colors,
        text=[f"{p:.1f}%" for p in pcts],
        textposition="outside",
        hovertemplate="%{x}<br>Count: %{y:,}<br>%{text} of all pairs<extra></extra>",
    ))

    fig.update_layout(
        **_base_layout(
            title=dict(text=title, font_size=15),
            height=380,
            xaxis=dict(tickangle=20, tickfont_size=11),
            yaxis=dict(title="Count"),
            margin=dict(l=60, r=20, t=60, b=110),
        )
    )
    return _j(fig)


# ── Per-card charts ───────────────────────────────────────────────────────────

def per_card_accuracy(pc_df: pd.DataFrame, title: str) -> str:
    """Clickable: clicking a card navigates to Browse for that card."""
    df = pc_df.sort_values("accuracy")
    mean_acc = float(df["accuracy"].mean())

    def _color(a):
        if a < 0.60: return "#dc2626"
        if a < 0.75: return "#f97316"
        if a < 0.90: return "#84cc16"
        return "#16a34a"

    colors = [_color(a) for a in df["accuracy"]]

    fig = go.Figure(go.Bar(
        x=df["accuracy"] * 100,
        y=df.index.tolist(),
        orientation="h",
        marker_color=colors,
        text=[f"{a*100:.1f}%" for a in df["accuracy"]],
        textposition="outside",
        customdata=df.index.tolist(),
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Accuracy: %{x:.1f}%<br>"
            "Errors: %{customdata}<extra></extra>"
        ),
    ))

    # Fix the customdata to be n_errors
    fig.data[0].customdata = [
        [card, int(pc_df.loc[card, "n_errors"])]
        for card in df.index
    ]
    fig.data[0].hovertemplate = (
        "<b>%{y}</b><br>Accuracy: %{x:.1f}%<br>"
        "Errors: %{customdata[1]}<extra></extra>"
    )

    fig.add_vline(
        x=mean_acc * 100,
        line_dash="dash", line_color="#1e293b", line_width=1.5,
        annotation_text=f"Mean {mean_acc*100:.1f}%",
        annotation_position="top right",
        annotation_font_size=11,
    )

    fig.update_layout(
        **_base_layout(
            title=dict(text=title, font_size=15),
            height=920,
            xaxis=dict(range=[0, 112], title="Accuracy (%)", tickfont_size=11),
            yaxis=dict(tickfont_size=9),
            margin=dict(l=150, r=80, t=60, b=60),
        )
    )
    return _j(fig)


# ── Comparison charts ─────────────────────────────────────────────────────────

def metrics_comparison(metrics_dict: dict, title: str) -> str:
    names = list(metrics_dict.keys())
    keys        = ["accuracy", "macro_f1", "weighted_f1", "macro_precision", "macro_recall"]
    key_labels  = ["Accuracy", "Macro F1", "Weighted F1", "Macro Prec.", "Macro Rec."]
    colors      = px.colors.qualitative.Set2[:len(names)]

    fig = go.Figure()
    for i, (ds, m) in enumerate(metrics_dict.items()):
        vals = [m[k] for k in keys]
        fig.add_trace(go.Bar(
            name=ds, x=key_labels, y=vals,
            marker_color=colors[i], opacity=0.88,
            text=[f"{v:.3f}" for v in vals],
            textposition="outside",
            hovertemplate="%{x}: <b>%{y:.4f}</b><extra>" + ds + "</extra>",
        ))

    fig.update_layout(
        **_base_layout(
            title=dict(text=title, font_size=15),
            barmode="group", height=440,
            yaxis=dict(range=[0, 1.15], title="Score"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
            margin=dict(l=60, r=20, t=70, b=60),
        )
    )
    return _j(fig)


def per_card_comparison(pc_dfs: dict, title: str) -> str:
    names = list(pc_dfs.keys())
    avg = pd.DataFrame({n: df["accuracy"] for n, df in pc_dfs.items()}).mean(axis=1)
    cards_sorted = avg.sort_values().index.tolist()
    colors = px.colors.qualitative.Set1[:len(names)]

    fig = go.Figure()
    for i, (ds, pc) in enumerate(pc_dfs.items()):
        vals = [pc.loc[c, "accuracy"] * 100 for c in cards_sorted]
        fig.add_trace(go.Bar(
            name=ds,
            x=vals, y=cards_sorted,
            orientation="h",
            marker_color=colors[i], opacity=0.82,
            hovertemplate=f"<b>%{{y}}</b><br>{ds}: %{{x:.1f}}%<extra></extra>",
        ))

    fig.update_layout(
        **_base_layout(
            title=dict(text=title, font_size=15),
            barmode="group", height=1100,
            xaxis=dict(range=[0, 112], title="Accuracy (%)", tickfont_size=10),
            yaxis=dict(tickfont_size=8),
            legend=dict(orientation="h", yanchor="bottom", y=1.01, x=0),
            margin=dict(l=160, r=20, t=70, b=60),
        )
    )
    return _j(fig)


def agreement_heatmap(datasets_dict: dict, title: str) -> str:
    names = list(datasets_dict.keys())
    mat = [
        [float(np.mean(
            datasets_dict[n1].values.astype(int).flatten() ==
            datasets_dict[n2].values.astype(int).flatten()
        )) for n2 in names]
        for n1 in names
    ]
    text = [[f"{mat[i][j]:.3f}" for j in range(len(names))] for i in range(len(names))]

    fig = go.Figure(go.Heatmap(
        z=mat, x=names, y=names,
        colorscale="YlOrRd", zmin=0, zmax=1,
        text=text, texttemplate="%{text}",
        hovertemplate="%{y} vs %{x}: %{z:.3f}<extra></extra>",
    ))

    fig.update_layout(
        **_base_layout(
            title=dict(text=title, font_size=15),
            height=max(300, len(names) * 100 + 120),
            margin=dict(l=120, r=20, t=60, b=80),
        )
    )
    return _j(fig)


def delta_per_card(pc_df1: pd.DataFrame, pc_df2: pd.DataFrame,
                   name1: str, name2: str, title: str) -> str:
    delta = (pc_df2["accuracy"] - pc_df1["accuracy"]) * 100
    delta_sorted = delta.sort_values()
    colors = ["#16a34a" if v >= 0 else "#dc2626" for v in delta_sorted]

    fig = go.Figure(go.Bar(
        x=delta_sorted,
        y=delta_sorted.index.tolist(),
        orientation="h",
        marker_color=colors,
        hovertemplate="<b>%{y}</b><br>Delta: %{x:+.1f}%<extra></extra>",
    ))

    fig.add_vline(x=0, line_color="#1e293b", line_width=1.2)

    fig.update_layout(
        **_base_layout(
            title=dict(text=f"{title}: {name1} → {name2}", font_size=15),
            height=920,
            xaxis=dict(title=f"Accuracy change (%) {name1} → {name2}", tickfont_size=10),
            yaxis=dict(tickfont_size=9),
            margin=dict(l=160, r=20, t=60, b=60),
        )
    )
    return _j(fig)
