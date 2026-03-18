/* card-app.js — Static version of the Card Profile page */

(function () {
  'use strict';

  let CONFIG  = null;
  let METRICS = null;
  let PAIRS   = null;

  let currentCard    = '';
  let currentRole    = 'a';
  let currentView    = 'fused';
  let enabledModels  = [];

  // ── Bootstrap ──────────────────────────────────────────────────────────────

  Promise.all([
    fetch('data/config.json').then(r => r.json()),
    fetch('data/metrics.json').then(r => r.json()),
    fetch('data/pairs.json').then(r => r.json()),
  ]).then(([cfg, met, pairs]) => {
    CONFIG  = cfg;
    METRICS = met;
    PAIRS   = pairs;

    // Populate card datalist
    const dl = document.getElementById('card-list');
    (CONFIG.cards || []).forEach(c => {
      const opt = document.createElement('option');
      opt.value = c;
      dl.appendChild(opt);
    });

    // Build model toggles
    buildModelToggles();

    // Read URL params
    readUrlParams();

    // Wire events
    wireEvents();

    // Initial render if card set
    if (currentCard) renderProfile();
  }).catch(err => {
    console.error('Failed to load data:', err);
    showToast('Failed to load data files', 'error');
  });

  // ── Model toggles ──────────────────────────────────────────────────────────

  function buildModelToggles() {
    const container = document.getElementById('model-toggles');
    container.innerHTML = '';
    const modelOrder = CONFIG.model_order || Object.keys(CONFIG.models || {});
    enabledModels = [...modelOrder];

    modelOrder.forEach(name => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'btn btn-xs btn-primary';
      btn.dataset.model = name;
      btn.textContent = name;
      btn.addEventListener('click', function () {
        const idx = enabledModels.indexOf(name);
        if (idx >= 0) {
          if (enabledModels.length > 1) {
            enabledModels.splice(idx, 1);
            btn.className = 'btn btn-xs btn-ghost';
          }
        } else {
          enabledModels.push(name);
          btn.className = 'btn btn-xs btn-primary';
        }
        pushUrlParams();
        if (currentCard) renderProfile();
      });
      container.appendChild(btn);
    });
  }

  function syncModelToggleUI() {
    document.querySelectorAll('#model-toggles [data-model]').forEach(btn => {
      const name = btn.dataset.model;
      btn.className = enabledModels.includes(name) ? 'btn btn-xs btn-primary' : 'btn btn-xs btn-ghost';
    });
  }

  // ── URL params ─────────────────────────────────────────────────────────────

  function readUrlParams() {
    const params = new URLSearchParams(window.location.search);
    currentCard  = params.get('card')  || '';
    currentRole  = params.get('role')  || 'a';
    currentView  = params.get('view')  || 'fused';

    const modelOrder = CONFIG.model_order || Object.keys(CONFIG.models || {});
    const modelsParam = params.get('models');
    if (modelsParam) {
      const requested = modelsParam.split(',').filter(n => modelOrder.includes(n));
      enabledModels = requested.length > 0 ? requested : [...modelOrder];
    } else {
      enabledModels = [...modelOrder];
    }

    // Sync UI
    document.getElementById('f-card').value = currentCard;
    syncRoleUI();
    syncViewUI();
    syncModelToggleUI();
  }

  function pushUrlParams() {
    const url = new URL(window.location.href);
    url.search = '';
    if (currentCard)  url.searchParams.set('card',   currentCard);
    if (currentRole !== 'a') url.searchParams.set('role', currentRole);
    if (currentView !== 'fused') url.searchParams.set('view', currentView);
    const modelOrder = CONFIG.model_order || Object.keys(CONFIG.models || {});
    if (enabledModels.length !== modelOrder.length ||
        !enabledModels.every(n => modelOrder.includes(n))) {
      url.searchParams.set('models', enabledModels.join(','));
    }
    window.history.pushState({}, '', url.toString());
  }

  // ── UI sync helpers ────────────────────────────────────────────────────────

  function syncRoleUI() {
    document.getElementById('role-a-btn').className =
      'btn btn-sm ' + (currentRole === 'a' ? 'btn-primary' : 'btn-secondary');
    document.getElementById('role-b-btn').className =
      'btn btn-sm ' + (currentRole === 'b' ? 'btn-primary' : 'btn-secondary');
  }

  function syncViewUI() {
    document.getElementById('view-fused-btn').className =
      'btn btn-sm ' + (currentView === 'fused' ? 'btn-primary' : 'btn-secondary');
    document.getElementById('view-sep-btn').className =
      'btn btn-sm ' + (currentView === 'separate' ? 'btn-primary' : 'btn-secondary');
  }

  // ── Events ─────────────────────────────────────────────────────────────────

  function wireEvents() {
    // Role buttons
    document.getElementById('role-a-btn').addEventListener('click', function () {
      currentRole = 'a';
      syncRoleUI();
      pushUrlParams();
      if (currentCard) renderProfile();
    });
    document.getElementById('role-b-btn').addEventListener('click', function () {
      currentRole = 'b';
      syncRoleUI();
      pushUrlParams();
      if (currentCard) renderProfile();
    });

    // View buttons
    document.getElementById('view-fused-btn').addEventListener('click', function () {
      currentView = 'fused';
      syncViewUI();
      pushUrlParams();
      if (currentCard) renderProfile();
    });
    document.getElementById('view-sep-btn').addEventListener('click', function () {
      currentView = 'separate';
      syncViewUI();
      pushUrlParams();
      if (currentCard) renderProfile();
    });

    // Go button
    document.getElementById('go-btn').addEventListener('click', function () {
      const val = document.getElementById('f-card').value.trim();
      if (val) {
        currentCard = val;
        pushUrlParams();
        renderProfile();
      }
    });

    // Enter key on card input
    document.getElementById('f-card').addEventListener('keydown', function (e) {
      if (e.key === 'Enter') {
        e.preventDefault();
        document.getElementById('go-btn').click();
      }
    });
  }

  // ── Profile computation ────────────────────────────────────────────────────

  function buildProfile(card, role) {
    const cards = CONFIG.cards || [];
    const rows  = [];

    PAIRS.forEach(p => {
      let other, gt, preds;
      if (role === 'a' && p.card_a === card) {
        other = p.card_b;
        gt    = p.gt;
        preds = {};
        const modelOrder = CONFIG.model_order || Object.keys(CONFIG.models || {});
        modelOrder.forEach(n => { preds[n] = p[n]; });
      } else if (role === 'b' && p.card_b === card) {
        other = p.card_a;
        gt    = p.gt;
        preds = {};
        const modelOrder = CONFIG.model_order || Object.keys(CONFIG.models || {});
        modelOrder.forEach(n => { preds[n] = p[n]; });
      } else {
        return;
      }
      const row = { other_card: other, gt };
      Object.assign(row, preds);
      rows.push(row);
    });

    // Sort by gt descending then other_card
    rows.sort((a, b) => {
      if (b.gt !== a.gt) return b.gt - a.gt;
      return a.other_card.localeCompare(b.other_card);
    });
    return rows;
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  function renderProfile() {
    const cards = CONFIG.cards || [];
    if (!currentCard || !cards.includes(currentCard)) {
      document.getElementById('charts-container').innerHTML =
        '<div class="card section-card"><div class="empty-state">Card not found. Please select a valid card.</div></div>';
      return;
    }

    const roleLabel = currentRole === 'a' ? 'Card A' : 'Card B';
    document.getElementById('card-sub').textContent =
      `${currentCard} as ${roleLabel}`;

    const profile = buildProfile(currentCard, currentRole);
    if (!profile.length) {
      document.getElementById('charts-container').innerHTML =
        '<div class="card section-card"><div class="empty-state">No pairs found for this card/role combination.</div></div>';
      return;
    }

    const container = document.getElementById('charts-container');
    container.innerHTML = '';

    if (currentView === 'fused') {
      const title = `${currentCard} as ${roleLabel} — All Models`;
      const barId = 'chart-card-fused';
      const wrap  = document.createElement('div');
      wrap.className = 'card section-card';
      wrap.innerHTML = `<h2 class="section-title">${escHtml(title)}</h2><div id="${barId}"></div>`;
      container.appendChild(wrap);
      const fig = cardProfileFused(profile, enabledModels, currentCard, currentRole, title);
      Plotly.react(barId, fig.data, fig.layout, CHART_CONFIG);

      // Single fused confusion matrix (all models pooled)
      const cmWrap = document.createElement('div');
      cmWrap.className = 'card section-card';
      cmWrap.innerHTML = '<h2 class="section-title">Confusion Matrix — All Models Combined</h2><div id="cm-fused"></div>';
      container.appendChild(cmWrap);
      const cmFig = buildConfusionMatrix(profile, enabledModels);
      Plotly.react('cm-fused', cmFig.data, cmFig.layout, CHART_CONFIG);
    } else {
      enabledModels.forEach(n => {
        const safeN = n.replace(/[^a-zA-Z0-9]/g, '_');
        const barId = `chart-card-sep-${safeN}`;
        const cmId  = `chart-cm-sep-${safeN}`;
        const wrap  = document.createElement('div');
        wrap.className = 'card section-card';
        wrap.innerHTML = `
          <h2 class="section-title">${escHtml(`${currentCard} vs ${n}`)}</h2>
          <div class="sep-chart-row">
            <div class="sep-bar"><div id="${barId}"></div></div>
            <div class="sep-cm"><div class="cm-label">${escHtml(n)}</div><div id="${cmId}"></div></div>
          </div>`;
        container.appendChild(wrap);
        const fig = cardProfileSeparate(profile, n, currentCard, currentRole, `${currentCard} as ${roleLabel} — ${n}`);
        Plotly.react(barId, fig.data, fig.layout, CHART_CONFIG);
        const cmFig = buildConfusionMatrix(profile, n);
        Plotly.react(cmId, cmFig.data, cmFig.layout, CHART_CONFIG);
      });
    }
  }

  // ── Confusion matrix for one model from profile data ───────────────────────

  function buildConfusionMatrix(profile, modelNameOrNames) {
    const labels = [-1, 0, 1];
    const labelNames = ['Negative (-1)', 'Neutral (0)', 'Positive (+1)'];
    const names = Array.isArray(modelNameOrNames) ? modelNameOrNames : [modelNameOrNames];
    // 3x3 count matrix [truth_row][pred_col] — pooled across all given models
    const cm = [[0,0,0],[0,0,0],[0,0,0]];
    names.forEach(n => {
      profile.forEach(r => {
        const ti = labels.indexOf(r.gt);
        const pi = labels.indexOf(r[n] !== undefined ? r[n] : 0);
        if (ti >= 0 && pi >= 0) cm[ti][pi]++;
      });
    });
    const total = profile.length;
    const text = cm.map(row => row.map(v => `<b>${v}</b><br>(${(v/total*100).toFixed(1)}%)`));
    return {
      data: [{
        type: 'heatmap',
        z: cm, x: labelNames, y: labelNames,
        colorscale: [[0,'#f7fbff'],[0.25,'#c6dbef'],[0.5,'#6baed6'],[0.75,'#2171b5'],[1.0,'#08306b']],
        zmin: 0,
        text, texttemplate: '%{text}',
        hovertemplate: 'Truth: <b>%{y}</b><br>Pred: <b>%{x}</b><br>Count: %{z}<extra></extra>',
        showscale: false, xgap: 2, ygap: 2,
      }],
      layout: {
        paper_bgcolor: 'white', plot_bgcolor: 'white',
        font: {family: 'Inter, -apple-system, sans-serif', size: 11, color: '#1e293b'},
        height: 320,
        xaxis: {title: 'Predicted', side: 'bottom', tickfont: {size: 10}},
        yaxis: {title: 'Ground Truth', autorange: 'reversed', tickfont: {size: 10}},
        margin: {l: 110, r: 20, t: 30, b: 80},
      },
    };
  }

  // ── Utilities ──────────────────────────────────────────────────────────────

  function escHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

})();
