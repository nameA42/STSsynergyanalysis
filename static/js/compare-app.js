/* compare-app.js — Static version of the Compare page */

(function () {
  'use strict';

  let CONFIG   = null;
  let METRICS  = null;
  let PER_CARD = null;
  let PAIRS    = null;

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
    buildCheckboxes();
    restoreFromUrl();
  }).catch(err => {
    console.error('Failed to load data:', err);
    showToast('Failed to load data files', 'error');
  });

  // ── Checkboxes ─────────────────────────────────────────────────────────────

  function buildCheckboxes() {
    const group = document.getElementById('checkbox-group');
    group.innerHTML = '';
    Object.entries(CONFIG.models).forEach(([name, info]) => {
      const label = document.createElement('label');
      label.className = 'checkbox-label';
      label.innerHTML = `
        <input type="checkbox" value="${escHtml(name)}">
        <span class="checkbox-text">
          <strong>${escHtml(name)}</strong>
          <small class="text-muted">${escHtml(info.description || '')}</small>
        </span>`;
      group.appendChild(label);
    });
  }

  function getChecked() {
    return [...document.querySelectorAll('#checkbox-group input[type=checkbox]:checked')]
      .map(i => i.value);
  }

  // ── URL state ──────────────────────────────────────────────────────────────

  function restoreFromUrl() {
    const params = new URLSearchParams(window.location.search);
    const ds = params.getAll('ds');
    if (ds.length) {
      document.querySelectorAll('#checkbox-group input[type=checkbox]').forEach(cb => {
        cb.checked = ds.includes(cb.value);
      });
      runComparison();
    }
  }

  document.getElementById('compare-btn').addEventListener('click', () => {
    const selected = getChecked();
    if (selected.length < 2) {
      showToast('Select at least 2 datasets to compare', 'error');
      return;
    }
    // Update URL
    const url = new URL(window.location.href);
    url.search = '';
    selected.forEach(s => url.searchParams.append('ds', s));
    window.history.pushState({}, '', url.toString());
    runComparison();
  });

  // ── Run comparison ─────────────────────────────────────────────────────────

  function runComparison() {
    const names = getChecked();
    if (names.length < 2) return;

    document.getElementById('compare-sub').textContent = names.join(' vs ');
    document.getElementById('compare-results').style.display = '';

    renderMetricsTable(names);
    renderPerClassTable(names);
    renderAgreementSection(names);
    renderCompareCharts(names);
    renderDeltaTables(names);
  }

  // ── Metrics summary table ──────────────────────────────────────────────────

  function renderMetricsTable(names) {
    const mkeys = [
      ['accuracy',         'Accuracy',     'pct'],
      ['macro_f1',         'Macro F1',     'f4'],
      ['weighted_f1',      'Weighted F1',  'f4'],
      ['macro_precision',  'Macro Prec.',  'f4'],
      ['macro_recall',     'Macro Rec.',   'f4'],
    ];
    const is2 = names.length === 2;

    // Header
    let thead = `<tr><th>Metric</th>${names.map(n => `<th>${escHtml(n)}</th>`).join('')}`;
    if (is2) thead += `<th>Delta (${escHtml(names[1])} &minus; ${escHtml(names[0])})</th>`;
    thead += '</tr>';
    document.getElementById('metrics-thead').innerHTML = thead;

    // Body
    const rows = mkeys.map(([key, label, fmt]) => {
      const vals = names.map(n => METRICS[n]?.[key] ?? 0);
      const cells = vals.map(v =>
        fmt === 'pct' ? `${(v * 100).toFixed(2)}%` : v.toFixed(4)
      ).map(s => `<td>${s}</td>`).join('');

      let deltaCell = '';
      if (is2) {
        const delta = (METRICS[names[1]]?.[key] ?? 0) - (METRICS[names[0]]?.[key] ?? 0);
        const cls   = delta > 0 ? 'text-green' : (delta < 0 ? 'text-red' : '');
        const dStr  = fmt === 'pct' ? `${(delta*100).toFixed(2) > 0 ? '+' : ''}${(delta*100).toFixed(2)}%`
                                    : `${delta >= 0 ? '+' : ''}${delta.toFixed(4)}`;
        deltaCell = `<td class="${cls}">${dStr}</td>`;
      }
      return `<tr><td><strong>${escHtml(label)}</strong></td>${cells}${deltaCell}</tr>`;
    });
    document.getElementById('metrics-tbody').innerHTML = rows.join('');
  }

  // ── Per-class F1 table ─────────────────────────────────────────────────────

  function renderPerClassTable(names) {
    const classes = [
      { key: '-1', label: 'Negative (-1)', badge: 'badge-neg' },
      { key:  '0', label: 'Neutral (0)',   badge: 'badge-neu' },
      { key:  '1', label: 'Positive (+1)', badge: 'badge-pos' },
    ];
    const is2 = names.length === 2;

    let thead = `<tr><th>Class</th>${names.map(n => `<th>${escHtml(n)}</th>`).join('')}`;
    if (is2) thead += '<th>Delta</th>';
    thead += '</tr>';
    document.getElementById('perclass-thead').innerHTML = thead;

    const rows = classes.map(({ key, label, badge }) => {
      const f1s = names.map(n => METRICS[n]?.per_class?.[key]?.f1 ?? 0);
      const cells = f1s.map(v => `<td>${v.toFixed(4)}</td>`).join('');
      let deltaCell = '';
      if (is2) {
        const d   = f1s[1] - f1s[0];
        const cls = d > 0 ? 'text-green' : (d < 0 ? 'text-red' : '');
        deltaCell = `<td class="${cls}">${d >= 0 ? '+' : ''}${d.toFixed(4)}</td>`;
      }
      return `<tr><td><span class="badge ${badge}">${escHtml(label)}</span></td>${cells}${deltaCell}</tr>`;
    });
    document.getElementById('perclass-tbody').innerHTML = rows.join('');
  }

  // ── Agreement ──────────────────────────────────────────────────────────────

  function renderAgreementSection(names) {
    const section = document.getElementById('agreement-section');
    if (names.length !== 2) { section.style.display = 'none'; return; }
    section.style.display = '';

    const [n1, n2] = names;
    let agree = 0, bothCorrect = 0, bothWrong = 0, only1 = 0, only2 = 0;
    PAIRS.forEach(p => {
      const v1 = p[n1], v2 = p[n2], gt = p.gt;
      if (v1 === v2) agree++;
      const c1 = v1 === gt, c2 = v2 === gt;
      if (c1 && c2) bothCorrect++;
      else if (!c1 && !c2) bothWrong++;
      else if (c1 && !c2) only1++;
      else if (!c1 && c2) only2++;
    });
    const total = PAIRS.length;

    const cards = [
      { val: `${(agree/total*100).toFixed(2)}%`, label: 'Agreement Rate', cls: '' },
      { val: `${(bothCorrect/total*100).toFixed(2)}%`, label: 'Both Correct', cls: 'accent-green' },
      { val: `${(bothWrong/total*100).toFixed(2)}%`,   label: 'Both Wrong',   cls: 'accent-red' },
      { val: `${(only1/total*100).toFixed(2)}%`,  label: `Only ${escHtml(n1)} correct`, cls: '' },
      { val: `${(only2/total*100).toFixed(2)}%`,  label: `Only ${escHtml(n2)} correct`, cls: '' },
    ];
    document.getElementById('agreement-metrics').innerHTML = cards.map(c =>
      `<div class="metric-card">
        <div class="metric-value ${c.cls}">${c.val}</div>
        <div class="metric-label">${c.label}</div>
      </div>`
    ).join('');

    // Browse disagreements link
    document.getElementById('browse-disagreements-btn').href =
      `browse.html?ds=${encodeURIComponent(n1)}&disagree_with=${encodeURIComponent(n2)}`;
  }

  // ── Charts ─────────────────────────────────────────────────────────────────

  function renderCompareCharts(names) {
    const selMetrics  = {};
    const selPerCard  = {};
    names.forEach(n => {
      selMetrics[n] = METRICS[n];
      selPerCard[n] = PER_CARD[n];
    });

    // Metrics comparison bar chart
    {
      const fig = metricsComparison(selMetrics, 'Metrics Comparison');
      Plotly.react('chart-metrics-cmp', fig.data, fig.layout, CHART_CONFIG);
    }

    // Per-card comparison
    {
      const fig = perCardComparison(selPerCard, 'Per-Card Accuracy Comparison');
      Plotly.react('chart-per-card-cmp', fig.data, fig.layout, CHART_CONFIG);
    }

    // Delta per-card (2 only)
    const deltaWrap = document.getElementById('chart-delta-wrap');
    if (names.length === 2) {
      deltaWrap.style.display = '';
      const [n1, n2] = names;
      const fig = deltaPerCard(PER_CARD[n1], PER_CARD[n2], n1, n2, 'Accuracy Delta');
      Plotly.react('chart-delta', fig.data, fig.layout, CHART_CONFIG);
    } else {
      deltaWrap.style.display = 'none';
    }

    // Agreement heatmap
    {
      const fig = agreementHeatmap(names, PAIRS, 'Agreement Heatmap');
      Plotly.react('chart-agreement', fig.data, fig.layout, CHART_CONFIG);
    }
  }

  // ── Delta tables ───────────────────────────────────────────────────────────

  function renderDeltaTables(names) {
    const tables = document.getElementById('delta-tables');
    if (names.length !== 2) { tables.style.display = 'none'; return; }
    tables.style.display = '';

    const [n1, n2] = names;
    const cards = Object.keys(PER_CARD[n1]);
    const deltas = cards.map(c => ({
      card:  c,
      acc1:  (PER_CARD[n1][c]?.accuracy || 0) * 100,
      acc2:  (PER_CARD[n2][c]?.accuracy || 0) * 100,
      delta: ((PER_CARD[n2][c]?.accuracy || 0) - (PER_CARD[n1][c]?.accuracy || 0)) * 100,
    }));

    document.getElementById('improved-label').textContent = `(${n1} → ${n2})`;
    document.getElementById('degraded-label').textContent  = `(${n1} → ${n2})`;
    document.getElementById('improved-h1').textContent = n1;
    document.getElementById('improved-h2').textContent = n2;
    document.getElementById('degraded-h1').textContent = n1;
    document.getElementById('degraded-h2').textContent = n2;

    const improved = [...deltas].sort((a, b) => b.delta - a.delta).slice(0, 10);
    const degraded = [...deltas].sort((a, b) => a.delta - b.delta).slice(0, 10);

    document.getElementById('improved-tbody').innerHTML = improved.map(r =>
      `<tr class="clickable-row" onclick="window.location.href='browse.html?card_a=${encodeURIComponent(r.card)}'">
        <td>${escHtml(r.card)}</td>
        <td>${r.acc1.toFixed(1)}%</td>
        <td>${r.acc2.toFixed(1)}%</td>
        <td class="text-green"><strong>${r.delta >= 0 ? '+' : ''}${r.delta.toFixed(1)}%</strong></td>
      </tr>`
    ).join('');

    document.getElementById('degraded-tbody').innerHTML = degraded.map(r =>
      `<tr class="clickable-row" onclick="window.location.href='browse.html?card_a=${encodeURIComponent(r.card)}'">
        <td>${escHtml(r.card)}</td>
        <td>${r.acc1.toFixed(1)}%</td>
        <td>${r.acc2.toFixed(1)}%</td>
        <td class="text-red"><strong>${r.delta >= 0 ? '+' : ''}${r.delta.toFixed(1)}%</strong></td>
      </tr>`
    ).join('');
  }

  // ── Utilities ──────────────────────────────────────────────────────────────

  function escHtml(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

})();
