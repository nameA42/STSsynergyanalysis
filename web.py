"""
STS Synergy Web App — run with:  python web.py
Then open http://localhost:5000 in your browser.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from flask import Flask, render_template, request, redirect, url_for, jsonify

from lib.loader import load_dataset, list_model_datasets, get_ground_truth_name, load_config
from lib import metrics as M
from lib import plotly_charts as PC
from annotate import add_annotation, _load_annotations, delete_annotation

app = Flask(__name__)
app.secret_key = "sts-synergy-2026"


# ── Template helpers ──────────────────────────────────────────────────────────

@app.template_global()
def args_drop(*keys):
    """Return current request args as dict, dropping the named keys."""
    return {k: v for k, v in request.args.items() if k not in keys}


@app.template_global()
def args_with(**overrides):
    """Return current request args merged with overrides."""
    d = dict(request.args)
    d.update({k: str(v) for k, v in overrides.items()})
    return d

# ── in-memory dataset cache (datasets don't change while app is running) ──────
_cache: dict = {}

def _get(name: str):
    if name not in _cache:
        _cache[name] = load_dataset(name)
    return _cache[name]

def _truth():
    return _get(get_ground_truth_name())

def _all_models() -> dict:
    return list_model_datasets()

def _default_ds() -> str:
    return next(iter(_all_models()))


# ── helpers ───────────────────────────────────────────────────────────────────

def _parse_class(label: str):
    """Parse a displayed class label back to int. Handles '-1','0','1'."""
    for v in (-1, 0, 1):
        if str(v) == label.strip():
            return v
    return None


# ── routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return redirect(url_for("analyze"))


# ── ANALYZE ───────────────────────────────────────────────────────────────────

@app.route("/analyze")
@app.route("/analyze/<ds_name>")
def analyze(ds_name=None):
    models = _all_models()
    if not models:
        return render_template("error.html", msg="No model datasets found in datasets.json.")

    if ds_name is None or ds_name not in models:
        ds_name = _default_ds()

    truth = _truth()
    pred  = _get(ds_name)
    m     = M.overall(pred, truth)
    pc_a  = M.per_card(pred, truth)
    pc_b  = M.per_card_as_b(pred, truth)
    eb    = M.error_breakdown(pred, truth)

    charts = {
        "confusion":       PC.confusion_matrix(m["confusion_matrix"], [-1, 0, 1],
                                               "Confusion Matrix"),
        "class_dist":      PC.class_distribution(pred, truth, "Class Distribution"),
        "per_card_a":      PC.per_card_accuracy(pc_a, f"Per-Card Accuracy — as Card A"),
        "per_card_b":      PC.per_card_accuracy(pc_b, f"Per-Card Accuracy — as Card B"),
        "pred_heatmap":    PC.synergy_heatmap(pred, f"Predictions — {ds_name}"),
        "error_heatmap":   PC.error_heatmap(pred, truth, f"Errors — {ds_name}"),
        "error_breakdown": PC.error_breakdown(eb, "Error Breakdown"),
    }

    # Per-card tables (worst 15 / best 10 for each role)
    worst_a = pc_a.sort_values("accuracy").head(15).reset_index()
    best_a  = pc_a.sort_values("accuracy").tail(10).iloc[::-1].reset_index()
    worst_b = pc_b.sort_values("accuracy").head(15).reset_index()
    best_b  = pc_b.sort_values("accuracy").tail(10).iloc[::-1].reset_index()

    return render_template("analyze.html",
        active="analyze",
        models=models,
        ds_name=ds_name,
        ds_info=load_config().get(ds_name, {}),
        metrics=m,
        worst_a=worst_a.to_dict("records"),
        best_a=best_a.to_dict("records"),
        worst_b=worst_b.to_dict("records"),
        best_b=best_b.to_dict("records"),
        charts=charts,
    )


# ── COMPARE ───────────────────────────────────────────────────────────────────

@app.route("/compare", methods=["GET", "POST"])
def compare():
    models = _all_models()
    if request.method == "POST":
        selected = request.form.getlist("datasets")
        if len(selected) >= 2:
            return redirect(url_for("compare_view", datasets=",".join(selected)))
    return render_template("compare.html", active="compare", models=models)


@app.route("/compare/<datasets>")
def compare_view(datasets):
    models = _all_models()
    names  = [n for n in datasets.split(",") if n in models]
    if len(names) < 2:
        return redirect(url_for("compare"))

    truth   = _truth()
    ds_dfs  = {n: _get(n) for n in names}
    met     = {n: M.overall(ds, truth) for n, ds in ds_dfs.items()}
    pc_dfs  = {n: M.per_card(ds, truth) for n, ds in ds_dfs.items()}

    agreement = {}
    if len(names) == 2:
        agreement = M.compute_agreement(ds_dfs[names[0]], ds_dfs[names[1]], truth)

    # Per-card delta table (top 10 improved / degraded)
    delta_table = []
    if len(names) == 2:
        import pandas as pd
        n1, n2 = names
        delta = (pc_dfs[n2]["accuracy"] - pc_dfs[n1]["accuracy"]) * 100
        for card, d in delta.sort_values(ascending=False).items():
            delta_table.append({
                "card": card,
                "acc1": pc_dfs[n1].loc[card, "accuracy"] * 100,
                "acc2": pc_dfs[n2].loc[card, "accuracy"] * 100,
                "delta": d,
            })

    charts = {
        "metrics": PC.metrics_comparison(met, "Metrics Comparison"),
        "per_card": PC.per_card_comparison(pc_dfs, "Per-Card Accuracy"),
        "agreement": PC.agreement_heatmap(ds_dfs, "Prediction Agreement"),
    }
    if len(names) == 2:
        charts["delta"] = PC.delta_per_card(
            pc_dfs[names[0]], pc_dfs[names[1]], names[0], names[1], "Accuracy Delta"
        )

    per_class = {
        lbl: {n: met[n]["per_class"][lbl] for n in names}
        for lbl in [-1, 0, 1]
    }

    return render_template("compare.html",
        active="compare",
        models=models,
        names=names,
        metrics=met,
        per_class=per_class,
        agreement=agreement,
        delta_table=delta_table,
        charts=charts,
        datasets_str=datasets,
    )


# ── BROWSE ────────────────────────────────────────────────────────────────────

@app.route("/browse")
def browse():
    import pandas as pd
    models   = _all_models()

    # Sort models by accuracy descending (highest accuracy = leftmost column)
    model_accuracies = {n: M.overall(_get(n), _truth())["accuracy"] for n in models}
    sorted_model_names = sorted(models.keys(), key=lambda n: model_accuracies[n], reverse=True)

    ds_name  = sorted_model_names[0] if sorted_model_names else ""
    card_a_q = request.args.get("card_a", "").strip()
    card_b_q = request.args.get("card_b", "").strip()
    gt_f     = request.args.get("gt", "")
    pair_sel = request.args.get("pair", "")
    page     = max(1, int(request.args.get("page", 1)))
    per_page = int(request.args.get("per_page", 50))
    sort_col = request.args.get("sort", "")
    sort_dir = request.args.get("order", "asc")

    # Per-model correctness filters: ""=any, "1"=correct, "0"=wrong (any), "-1"=under, "+1"=over
    correctness_filters = {n: request.args.get(f"correct_{n}", "") for n in models}

    # Per-model prediction filters
    pred_filters = {n: request.args.get(f"pred_{n}", "") for n in models}

    truth    = _truth()
    pred_df  = _get(ds_name) if ds_name in models else None
    other_ds = [n for n in sorted_model_names if n != ds_name]
    extra    = {n: _get(n) for n in other_ds}

    pairs_df = M.pair_table(pred_df, truth, extra=extra) if pred_df is not None else pd.DataFrame()

    # Compute correct_<n> for every extra dataset
    if not pairs_df.empty:
        for n in other_ds:
            pairs_df[f"correct_{n}"] = pairs_df[f"pred_{n}"] == pairs_df["ground_truth"]

        # Compute n_correct column (number of models that got the pair correct)
        pairs_df["n_correct"] = pairs_df["correct"].astype(int)
        for n in other_ds:
            pairs_df["n_correct"] += pairs_df[f"correct_{n}"].astype(int)

    # Apply filters
    if not pairs_df.empty:
        if card_a_q:
            pairs_df = pairs_df[pairs_df["card_a"].str.contains(card_a_q, case=False, na=False)]
        if card_b_q:
            pairs_df = pairs_df[pairs_df["card_b"].str.contains(card_b_q, case=False, na=False)]
        if gt_f in ("-1", "0", "1"):
            pairs_df = pairs_df[pairs_df["ground_truth"] == int(gt_f)]

        # Correctness filters (5 states)
        for n, val in correctness_filters.items():
            if val == "":
                continue
            col = "predicted" if n == ds_name else f"pred_{n}"
            if col not in pairs_df.columns:
                continue
            if val == "1":
                pairs_df = pairs_df[pairs_df["ground_truth"] == pairs_df[col]]
            elif val == "0":
                pairs_df = pairs_df[pairs_df["ground_truth"] != pairs_df[col]]
            elif val == "-1":
                pairs_df = pairs_df[pairs_df[col] < pairs_df["ground_truth"]]
            elif val == "+1":
                pairs_df = pairs_df[pairs_df[col] > pairs_df["ground_truth"]]

        # Prediction filters
        for n, val in pred_filters.items():
            if val not in ("-1", "0", "1"):
                continue
            col = "predicted" if n == ds_name else f"pred_{n}"
            if col in pairs_df.columns:
                pairs_df = pairs_df[pairs_df[col] == int(val)]

        # Sorting — valid columns: ground_truth, predicted, pred_<n>, n_correct
        valid_sort = {"ground_truth", "predicted", "n_correct"}
        for n in other_ds:
            valid_sort.add(f"pred_{n}")
        if sort_col in valid_sort and sort_col in pairs_df.columns:
            pairs_df = pairs_df.sort_values(sort_col, ascending=(sort_dir == "asc"))

    total       = len(pairs_df)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page        = min(page, total_pages)
    page_rows   = pairs_df.iloc[(page - 1) * per_page: page * per_page].to_dict("records") \
                  if not pairs_df.empty else []

    # Load annotation flags
    ann_df  = _load_annotations()
    ann_ids = set(ann_df["pair_id"].tolist()) if not ann_df.empty else set()

    # Selected pair detail
    selected = None
    if pair_sel and "|" in pair_sel:
        ca, cb = pair_sel.split("|", 1)
        cards = list(truth.index)
        if ca in cards and cb in cards:
            gt_val = int(truth.loc[ca, cb])
            preds  = {n: int(_get(n).loc[ca, cb]) for n in models}
            ann_row = None
            if not ann_df.empty:
                match = ann_df[ann_df["pair_id"] == pair_sel]
                if not match.empty:
                    ann_row = match.iloc[0].to_dict()
            selected = {
                "card_a": ca, "card_b": cb,
                "pair_id": pair_sel,
                "ground_truth": gt_val,
                "predictions": preds,
                "annotation": ann_row,
            }

    return render_template("browse.html",
        active="browse",
        models=models,
        ds_name=ds_name,
        other_ds=other_ds,
        model_order=sorted_model_names,
        pairs=page_rows,
        ann_ids=ann_ids,
        total=total,
        page=page,
        total_pages=total_pages,
        per_page=per_page,
        filters=dict(card_a=card_a_q, card_b=card_b_q, gt=gt_f),
        correctness_filters=correctness_filters,
        pred_filters=pred_filters,
        sort=dict(col=sort_col, order=sort_dir),
        pair_sel=pair_sel,
        selected=selected,
    )


# ── ANNOTATE ──────────────────────────────────────────────────────────────────

@app.route("/annotate")
def annotate_page():
    models     = _all_models()
    cards      = list(_truth().index)
    tag_filter = request.args.get("tag", "").strip()
    card_filt  = request.args.get("card", "").strip()

    ann_df = _load_annotations()
    if not ann_df.empty:
        if tag_filter:
            ann_df = ann_df[ann_df["tags"].str.contains(tag_filter, case=False, na=False)]
        if card_filt:
            mask = (ann_df["card_a"].str.contains(card_filt, case=False, na=False) |
                    ann_df["card_b"].str.contains(card_filt, case=False, na=False))
            ann_df = ann_df[mask]
    annotations = ann_df.to_dict("records") if not ann_df.empty else []

    return render_template("annotate.html",
        active="annotate",
        models=models,
        cards=cards,
        annotations=annotations,
        tag_filter=tag_filter,
        card_filter=card_filt,
        pred_cols=[c for c in (_load_annotations().columns if not _load_annotations().empty else [])
                   if c.startswith("pred_")],
    )


# ── API ───────────────────────────────────────────────────────────────────────

@app.route("/api/annotate/add", methods=["POST"])
def api_annotate_add():
    data   = request.json or {}
    card_a = data.get("card_a", "").strip()
    card_b = data.get("card_b", "").strip()
    note   = data.get("note", "").strip()
    tags   = data.get("tags", "").strip()

    truth  = _truth()
    models = _all_models()
    cards  = list(truth.index)

    if card_a not in cards or card_b not in cards:
        return jsonify({"success": False, "error": "Invalid card name(s)"}), 400
    if not note and not tags:
        return jsonify({"success": False, "error": "Note and tags cannot both be empty"}), 400

    try:
        gt    = int(truth.loc[card_a, card_b])
        preds = {n: int(_get(n).loc[card_a, card_b]) for n in models}
        add_annotation(card_a, card_b, gt, preds, note, tags)
        return jsonify({"success": True, "pair_id": f"{card_a}|{card_b}"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/annotate/delete", methods=["POST"])
def api_annotate_delete():
    pair_id = (request.json or {}).get("pair_id", "")
    ok = delete_annotation(pair_id)
    return jsonify({"success": ok})


@app.route("/api/pair/<path:pair_id>")
def api_pair(pair_id):
    """Return all dataset predictions for a card pair (used by browse JS)."""
    if "|" not in pair_id:
        return jsonify({"error": "Invalid pair_id"}), 400
    ca, cb = pair_id.split("|", 1)
    truth  = _truth()
    models = _all_models()
    cards  = list(truth.index)
    if ca not in cards or cb not in cards:
        return jsonify({"error": "Card not found"}), 404

    ann_df   = _load_annotations()
    ann_row  = None
    if not ann_df.empty:
        match = ann_df[ann_df["pair_id"] == pair_id]
        if not match.empty:
            ann_row = {k: str(v) for k, v in match.iloc[0].to_dict().items()}

    return jsonify({
        "card_a":       ca,
        "card_b":       cb,
        "ground_truth": int(truth.loc[ca, cb]),
        "predictions":  {n: int(_get(n).loc[ca, cb]) for n in models},
        "annotation":   ann_row,
    })


# ── launch ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Auto-open browser once on startup (not on reloader restart)
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        import threading, webbrowser
        def _open():
            import time; time.sleep(1.2)
            webbrowser.open("http://localhost:5000")
        threading.Thread(target=_open, daemon=True).start()

    port = int(os.environ.get("PORT", 5000))
    is_local = port == 5000
    print("\n  STS Synergy Web App")
    print(f"  Running at http://localhost:{port}")
    if is_local:
        print("  Press Ctrl+C to stop\n")
    app.run(debug=is_local, host="0.0.0.0", port=port, use_reloader=is_local)
