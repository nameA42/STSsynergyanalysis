/* analyze-app.js — Static version of the Analyze page */

(function () {
  'use strict';

  let CONFIG = null;
  let METRICS = null;
  let PER_CARD = null;
  let PAIRS = null;
  let currentDs = null;

  // ── Bootstrap ──────────────────────────────────────────────────────────────

  Promise.all([
    fetch('data/config.json').then(r => r.json()),
    fetch('data/metrics.json').then(r => r.json()),
    fetch('data/per_card.json').then(r => r.json()),
    fetch('data/pairs.json').then(r => r.json()),
  ]).then(([cfg, met, pc, pairs]) => {
    CONFIG   = cfg;
    METRICS  = met;
    PER_CARD = pc;
    PAIRS    = pairs;

    buildTabs();

    // Check URL param for ds
    const params = new URLSearchParams(window.location.search);
    const dsParam = params.get('ds');
    const firstDs = Object.keys(CONFIG.models)[0];
    selectDs(dsParam && CONFIG.models[dsParam] ? dsParam : firstDs);
  }).catch(err => {
    console.error('Failed to load data:', err);
    showToast('Failed to load data files', 'error');
  });

  // ── Tabs ───────────────────────────────────────────────────────────────────

  function buildTabs() {
    const container = document.getElementById('ds-tabs');
    container.innerHTML = '';
    Object.keys(CONFIG.models).forEach(name => {
      const a = document.createElement('a');
      a.className = 'ds-tab';
      a.textContent = name;
      a.href = '#';
      a.addEventListener('click', e => { e.preventDefault(); selectDs(name); });
      container.appendChild(a);
    });
  }

  function selectDs(name) {
    currentDs = name;

    // Update active tab
    document.querySelectorAll('.ds-tab').forEach(t => {
      t.classList.toggle('active', t.textContent === name);
    });

    // Update subtitle
    const info = CONFIG.models[name] || {};
    const sub  = [info.description, info.date].filter(Boolean).join(' — ');
    document.getElementById('ds-sub').textContent = sub;

    renderMetrics(name);
    renderPerClassTable(name);
    renderCharts(name);
    renderCardTables(name);
  }

  // ── Metric cards ───────────────────────────────────────────────────────────

  function renderMetrics(ds) {
    const m = METRICS[ds];
    if (!m) return;

    document.getElementById('m-accuracy').textContent    = `${(m.accuracy * 100).toFixed(2)}%`;
    document.getElementById('m-macro-f1').textContent    = m.macro_f1.toFixed(4);
    document.getElementById('m-weighted-f1').textContent = m.weighted_f1.toFixed(4);
    document.getElementById('m-macro-prec').textContent  = m.macro_precision.toFixed(4);
    document.getElementById('m-macro-rec').textContent   = m.macro_recall.toFixed(4);
    document.getElementById('m-errors').textContent      = m.n_errors.toLocaleString();
    document.getElementById('m-errors-label').textContent =
      `Errors / ${m.n_total.toLocaleString()} pairs`;
  }

  // ── Per-class table ────────────────────────────────────────────────────────

  function renderPerClassTable(ds) {
    const m = METRICS[ds];
    if (!m) return;
    const tbody = document.getElementById('per-class-tbody');
    const classes = [
      { key: '-1', label: 'Negative (-1)', badge: 'badge-neg' },
      { key:  '0', label: 'Neutral (0)',   badge: 'badge-neu' },
      { key:  '1', label: 'Positive (+1)', badge: 'badge-pos' },
    ];
    tbody.innerHTML = classes.map(({ key, label, badge }) => {
      const pc = m.per_class[key] || {};
      return `<tr>
        <td><span class="badge ${badge}">${label}</span></td>
        <td>${(pc.precision || 0).toFixed(4)}</td>
        <td>${(pc.recall || 0).toFixed(4)}</td>
        <td><strong>${(pc.f1 || 0).toFixed(4)}</strong></td>
        <td>${(pc.support || 0).toLocaleString()}</td>
      </tr>`;
    }).join('');
  }

  // ── Charts ─────────────────────────────────────────────────────────────────

  function renderCharts(ds) {
    const m      = METRICS[ds];
    const pc     = PER_CARD[ds];
    const cards  = CONFIG.cards;
    const pairs  = PAIRS;

    // Confusion matrix
    if (m && m.confusion_matrix) {
      const fig = confusionMatrix(m.confusion_matrix, `Confusion Matrix — ${ds}`);
      Plotly.react('chart-confusion', fig.data, fig.layout, CHART_CONFIG);

      const confEl = document.getElementById('chart-confusion');
      // Remove old listener by replacing element clone trick — use flag instead
      confEl._dsName = ds;
      if (!confEl._clickBound) {
        confEl._clickBound = true;
        confEl.on('plotly_click', function (data) {
          if (!data.points || !data.points.length) return;
          const pt = data.points[0];
          const parseClass = s =>
            s.includes('-1') ? '-1' : (s.includes('+1') || s.endsWith('1)')) ? '1' : '0';
          const gt   = parseClass(String(pt.y));
          const pred = parseClass(String(pt.x));
          window.location.href = `browse.html?gt=${gt}&pred=${pred}&ds=${encodeURIComponent(confEl._dsName)}`;
        });
      }
    }

    // Class distribution
    {
      const fig = classDistribution(pairs, ds, `Class Distribution — ${ds}`);
      Plotly.react('chart-class-dist', fig.data, fig.layout, CHART_CONFIG);
    }

    // Error breakdown
    {
      const fig = errorBreakdown(pairs, ds, `Error Breakdown — ${ds}`);
      Plotly.react('chart-error-breakdown', fig.data, fig.layout, CHART_CONFIG);
    }

    // Per-card accuracy
    if (pc) {
      const fig = perCardAccuracy(pc, `Per-Card Accuracy — ${ds}`);
      Plotly.react('chart-per-card', fig.data, fig.layout, CHART_CONFIG);

      const pcEl = document.getElementById('chart-per-card');
      pcEl._dsName = ds;
      if (!pcEl._clickBound) {
        pcEl._clickBound = true;
        pcEl.on('plotly_click', function (data) {
          if (!data.points || !data.points.length) return;
          const card = data.points[0].y;
          window.location.href = `browse.html?card_a=${encodeURIComponent(card)}&ds=${encodeURIComponent(pcEl._dsName)}`;
        });
      }
    }

    // Prediction heatmap
    {
      const mat = pairsToMatrix(pairs, cards, ds);
      const fig = synergyHeatmap(mat, cards, `Predictions — ${ds}`);
      Plotly.react('chart-pred-heatmap', fig.data, fig.layout, CHART_CONFIG);

      const hmEl = document.getElementById('chart-pred-heatmap');
      hmEl._dsName = ds;
      if (!hmEl._clickBound) {
        hmEl._clickBound = true;
        hmEl.on('plotly_click', function (data) {
          if (!data.points || !data.points.length) return;
          const pt = data.points[0];
          window.location.href = `browse.html?pair=${encodeURIComponent(pt.y + '|' + pt.x)}&ds=${encodeURIComponent(hmEl._dsName)}`;
        });
      }
    }

    // Error heatmap
    {
      const predMat  = pairsToMatrix(pairs, cards, ds);
      const truthMat = pairsToMatrix(pairs, cards, 'gt');
      const fig = errorHeatmap(predMat, truthMat, cards, `Error Map — ${ds}`);
      Plotly.react('chart-error-heatmap', fig.data, fig.layout, CHART_CONFIG);

      const ehEl = document.getElementById('chart-error-heatmap');
      ehEl._dsName = ds;
      if (!ehEl._clickBound) {
        ehEl._clickBound = true;
        ehEl.on('plotly_click', function (data) {
          if (!data.points || !data.points.length) return;
          const pt = data.points[0];
          window.location.href = `browse.html?pair=${encodeURIComponent(pt.y + '|' + pt.x)}&ds=${encodeURIComponent(ehEl._dsName)}`;
        });
      }
    }
  }

  // ── Card tables ────────────────────────────────────────────────────────────

  function renderCardTables(ds) {
    const pc = PER_CARD[ds];
    if (!pc) return;

    const cards = Object.keys(pc);

    // Sort by accuracy
    const sorted = [...cards].sort((a, b) => pc[a].accuracy - pc[b].accuracy);

    function accBarHtml(acc) {
      let color = '#16a34a';
      if (acc < 0.60) color = '#dc2626';
      else if (acc < 0.75) color = '#f97316';
      else if (acc < 0.90) color = '#84cc16';
      return `<div class="acc-bar-wrap">
        <div class="acc-bar" style="width:${(acc*100).toFixed(1)}%;background:${color}"></div>
        <span>${(acc*100).toFixed(1)}%</span>
      </div>`;
    }

    // Worst 15
    const worstTbody = document.getElementById('worst-cards-tbody');
    worstTbody.innerHTML = sorted.slice(0, 15).map((card, idx) => {
      const r = pc[card];
      return `<tr class="clickable-row" style="cursor:pointer"
                  onclick="window.location.href='browse.html?card_a=${encodeURIComponent(card)}&ds=${encodeURIComponent(ds)}'">
        <td class="text-muted">${idx + 1}</td>
        <td><strong>${escHtml(card)}</strong></td>
        <td>${accBarHtml(r.accuracy)}</td>
        <td>${r.n_errors}</td>
        <td>${r.false_pos_synergy ?? '—'}</td>
        <td>${r.false_neg_synergy ?? '—'}</td>
      </tr>`;
    }).join('');

    // Best 10
    const bestTbody = document.getElementById('best-cards-tbody');
    bestTbody.innerHTML = sorted.slice(-10).reverse().map((card, idx) => {
      const r = pc[card];
      return `<tr class="clickable-row" style="cursor:pointer"
                  onclick="window.location.href='browse.html?card_a=${encodeURIComponent(card)}&ds=${encodeURIComponent(ds)}'">
        <td class="text-muted">${idx + 1}</td>
        <td><strong>${escHtml(card)}</strong></td>
        <td>${accBarHtml(r.accuracy)}</td>
        <td>${r.n_errors}</td>
      </tr>`;
    }).join('');
  }

  // ── Utilities ──────────────────────────────────────────────────────────────

  function escHtml(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

})();
