/* browse-app.js — Static version of the Browse page */

(function () {
  'use strict';

  const ANN_KEY = 'sts_annotations';

  let CONFIG      = null;
  let PAIRS       = null;
  let ANNOTATIONS = {};  // pair_id → annotation

  // Filter state
  let fDs       = '';
  let fCardA    = '';
  let fCardB    = '';
  let fGt       = '';
  let fPred     = '';
  let fCorrect  = {};   // {dsName: '1'|'0'|''}
  let fPair     = '';

  // Pagination
  let perPage    = 50;
  let currentPage = 1;

  // ── Bootstrap ──────────────────────────────────────────────────────────────

  Promise.all([
    fetch('data/config.json').then(r => r.json()),
    fetch('data/pairs.json').then(r => r.json()),
    fetch('data/annotations.json').then(r => r.json()),
  ]).then(([cfg, pairs, seedAnn]) => {
    CONFIG = cfg;
    PAIRS  = pairs;

    // Load annotations from localStorage (merging seed)
    loadAnnotations(seedAnn);

    // Populate card datalist
    const dl = document.getElementById('card-list');
    CONFIG.cards.forEach(c => {
      const opt = document.createElement('option');
      opt.value = c;
      dl.appendChild(opt);
    });

    // Build dataset select
    const dsSel = document.getElementById('f-dataset');
    Object.keys(CONFIG.models).forEach(name => {
      const opt = document.createElement('option');
      opt.value = name;
      opt.textContent = name;
      dsSel.appendChild(opt);
    });

    // Build correctness filter rows
    buildCorrFilter();

    // Restore state from URL params
    readUrlParams();

    // Wire events
    wireEvents();

    // Initial render
    applyAndRender();
  }).catch(err => {
    console.error('Failed to load data:', err);
    showToast('Failed to load data files', 'error');
  });

  // ── Annotations (localStorage) ─────────────────────────────────────────────

  function loadAnnotations(seedArr) {
    const stored = localStorage.getItem(ANN_KEY);
    if (stored) {
      try {
        const arr = JSON.parse(stored);
        ANNOTATIONS = {};
        arr.forEach(a => { ANNOTATIONS[a.pair_id] = a; });
      } catch (_) { ANNOTATIONS = {}; }
    } else {
      // Seed from static file
      ANNOTATIONS = {};
      (seedArr || []).forEach(a => { ANNOTATIONS[a.pair_id] = a; });
    }
  }

  function saveAnnotations() {
    localStorage.setItem(ANN_KEY, JSON.stringify(Object.values(ANNOTATIONS)));
  }

  // ── Correctness filter ─────────────────────────────────────────────────────

  function buildCorrFilter() {
    const container = document.getElementById('corr-rows');
    container.innerHTML = '';
    Object.keys(CONFIG.models).forEach(name => {
      const div = document.createElement('div');
      div.className = 'corr-row';
      div.innerHTML = `
        <span class="corr-name">${escHtml(name)}</span>
        <button type="button" class="corr-state-btn state-any" data-ds="${escHtml(name)}">—</button>
        <input type="hidden" id="corr-${escHtml(name)}" value="">`;
      container.appendChild(div);
      fCorrect[name] = '';
    });

    // Wire buttons
    document.querySelectorAll('.corr-state-btn').forEach(btn => {
      btn.addEventListener('click', function () {
        const ds  = this.dataset.ds;
        const inp = document.getElementById(`corr-${ds}`);
        const cur = inp.value;
        const next = cur === '' ? '1' : cur === '1' ? '0' : '';
        inp.value = next;
        fCorrect[ds] = next;
        applyCorrState(this, next);
      });
    });
  }

  function applyCorrState(btn, val) {
    btn.classList.remove('state-any', 'state-ok', 'state-err');
    if (val === '1') {
      btn.textContent = '✓';
      btn.classList.add('state-ok');
    } else if (val === '0') {
      btn.textContent = '✗';
      btn.classList.add('state-err');
    } else {
      btn.textContent = '—';
      btn.classList.add('state-any');
    }
  }

  function syncCorrFilterUI() {
    document.querySelectorAll('.corr-state-btn').forEach(btn => {
      const ds  = btn.dataset.ds;
      const inp = document.getElementById(`corr-${ds}`);
      const val = fCorrect[ds] || '';
      inp.value = val;
      applyCorrState(btn, val);
    });
    // Update toggle button label
    const active = Object.values(fCorrect).filter(v => v !== '').length;
    const toggle = document.getElementById('corr-toggle');
    toggle.innerHTML = active
      ? `${active} filter${active !== 1 ? 's' : ''} active &#9660;`
      : 'Filter by model &#9660;';
  }

  // ── URL params ─────────────────────────────────────────────────────────────

  function readUrlParams() {
    const params = new URLSearchParams(window.location.search);
    fDs      = params.get('ds')     || Object.keys(CONFIG.models)[0];
    fCardA   = params.get('card_a') || '';
    fCardB   = params.get('card_b') || '';
    fGt      = params.get('gt')     || '';
    fPred    = params.get('pred')   || '';
    fPair    = params.get('pair')   || '';
    perPage  = parseInt(params.get('pp') || '50', 10);
    currentPage = parseInt(params.get('page') || '1', 10);

    // Correctness filters
    Object.keys(CONFIG.models).forEach(ds => {
      fCorrect[ds] = params.get(`correct_${ds}`) || '';
    });

    // Sync UI
    document.getElementById('f-dataset').value = fDs;
    document.getElementById('f-card-a').value  = fCardA;
    document.getElementById('f-card-b').value  = fCardB;
    document.getElementById('f-gt').value       = fGt;
    document.getElementById('f-pred').value     = fPred;
    syncCorrFilterUI();
    updatePerPageUI();
  }

  function pushUrlParams() {
    const url = new URL(window.location.href);
    url.search = '';
    if (fDs)     url.searchParams.set('ds',     fDs);
    if (fCardA)  url.searchParams.set('card_a', fCardA);
    if (fCardB)  url.searchParams.set('card_b', fCardB);
    if (fGt)     url.searchParams.set('gt',     fGt);
    if (fPred)   url.searchParams.set('pred',   fPred);
    if (fPair)   url.searchParams.set('pair',   fPair);
    if (perPage !== 50) url.searchParams.set('pp', String(perPage));
    if (currentPage > 1) url.searchParams.set('page', String(currentPage));
    Object.entries(fCorrect).forEach(([ds, val]) => {
      if (val !== '') url.searchParams.set(`correct_${ds}`, val);
    });
    window.history.pushState({}, '', url.toString());
  }

  // ── Events ─────────────────────────────────────────────────────────────────

  function wireEvents() {
    // Dataset change
    document.getElementById('f-dataset').addEventListener('change', function () {
      fDs = this.value;
      currentPage = 1;
      applyAndRender();
      pushUrlParams();
    });

    // Filter button
    document.getElementById('filter-btn').addEventListener('click', collectAndFilter);

    // Clear button
    document.getElementById('clear-btn').addEventListener('click', () => {
      fCardA = ''; fCardB = ''; fGt = ''; fPred = ''; fPair = '';
      Object.keys(fCorrect).forEach(k => { fCorrect[k] = ''; });
      document.getElementById('f-card-a').value = '';
      document.getElementById('f-card-b').value = '';
      document.getElementById('f-gt').value     = '';
      document.getElementById('f-pred').value   = '';
      syncCorrFilterUI();
      currentPage = 1;
      applyAndRender();
      pushUrlParams();
    });

    // Corr apply
    document.getElementById('corr-apply').addEventListener('click', () => {
      document.getElementById('corr-panel').classList.remove('open');
      collectAndFilter();
    });

    // Corr clear
    document.getElementById('corr-clear').addEventListener('click', () => {
      Object.keys(fCorrect).forEach(k => { fCorrect[k] = ''; });
      syncCorrFilterUI();
    });

    // Corr toggle
    document.getElementById('corr-toggle').addEventListener('click', function (e) {
      e.stopPropagation();
      document.getElementById('corr-panel').classList.toggle('open');
    });
    document.addEventListener('click', function (e) {
      if (!document.getElementById('corr-wrap').contains(e.target)) {
        document.getElementById('corr-panel').classList.remove('open');
      }
    });

    // Per-page
    document.querySelectorAll('.per-page-opt').forEach(a => {
      a.addEventListener('click', e => {
        e.preventDefault();
        perPage = parseInt(a.dataset.pp, 10);
        currentPage = 1;
        updatePerPageUI();
        applyAndRender();
        pushUrlParams();
      });
    });

    // Detail close
    document.getElementById('detail-close').addEventListener('click', () => {
      fPair = '';
      document.getElementById('detail-panel').style.display = 'none';
      pushUrlParams();
    });

    // Annotation form submit
    document.getElementById('ann-form').addEventListener('submit', function (e) {
      e.preventDefault();
      const pairId = document.getElementById('ann-pair-id').value;
      if (!pairId) return;
      const note   = document.getElementById('ann-note').value.trim();
      const tags   = document.getElementById('ann-tags').value.trim();
      const pair   = PAIRS.find(p => p.pair_id === pairId);
      ANNOTATIONS[pairId] = {
        pair_id:      pairId,
        card_a:       pair?.card_a || '',
        card_b:       pair?.card_b || '',
        ground_truth: String(pair?.gt ?? ''),
        note, tags,
        timestamp:    new Date().toISOString().slice(0, 19).replace('T', ' '),
      };
      saveAnnotations();
      showToast('Annotation saved', 'success');
      document.getElementById('ann-form-title').textContent = 'Edit Annotation';
      document.getElementById('ann-delete-btn').style.display = '';
    });

    // Delete annotation
    document.getElementById('ann-delete-btn').addEventListener('click', function () {
      const pairId = document.getElementById('ann-pair-id').value;
      if (!pairId || !confirm('Delete annotation?')) return;
      delete ANNOTATIONS[pairId];
      saveAnnotations();
      showToast('Deleted', 'success');
      document.getElementById('ann-form-title').textContent = 'Add Annotation';
      this.style.display = 'none';
      document.getElementById('ann-note').value = '';
      document.getElementById('ann-tags').value = '';
      applyAndRender();
    });
  }

  function collectAndFilter() {
    fCardA = document.getElementById('f-card-a').value.trim();
    fCardB = document.getElementById('f-card-b').value.trim();
    fGt    = document.getElementById('f-gt').value;
    fPred  = document.getElementById('f-pred').value;
    currentPage = 1;
    applyAndRender();
    pushUrlParams();
  }

  function updatePerPageUI() {
    document.querySelectorAll('.per-page-opt').forEach(a => {
      a.classList.toggle('active', parseInt(a.dataset.pp, 10) === perPage);
    });
  }

  // ── Filtering ──────────────────────────────────────────────────────────────

  function applyFilters() {
    const ds      = fDs || Object.keys(CONFIG.models)[0];
    const allDs   = Object.keys(CONFIG.models);

    return PAIRS.filter(p => {
      // Pair filter
      if (fPair && p.pair_id !== fPair) return false;

      // Card A/B substring
      if (fCardA && !p.card_a.toLowerCase().includes(fCardA.toLowerCase())) return false;
      if (fCardB && !p.card_b.toLowerCase().includes(fCardB.toLowerCase())) return false;

      // GT
      if (fGt !== '' && p.gt !== parseInt(fGt, 10)) return false;

      // Pred (uses current ds)
      if (fPred !== '' && p[ds] !== parseInt(fPred, 10)) return false;

      // Correctness filters
      for (const [corrDs, corrVal] of Object.entries(fCorrect)) {
        if (corrVal === '') continue;
        const correct = p[corrDs] === p.gt;
        if (corrVal === '1' && !correct) return false;
        if (corrVal === '0' &&  correct) return false;
      }

      return true;
    });
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  function applyAndRender() {
    const filtered = applyFilters();
    const total    = filtered.length;
    const totalPages = Math.max(1, Math.ceil(total / perPage));
    currentPage = Math.min(currentPage, totalPages);

    const start = (currentPage - 1) * perPage;
    const page  = filtered.slice(start, start + perPage);

    const ds      = fDs || Object.keys(CONFIG.models)[0];
    const allDs   = Object.keys(CONFIG.models);
    const otherDs = allDs.filter(n => n !== ds);

    // Subtitle
    const active = Object.values(fCorrect).filter(v => v !== '').length;
    document.getElementById('browse-sub').textContent =
      `${total} pairs${active ? ` · ${active} correctness filter${active !== 1 ? 's' : ''}` : ''}`;

    // Table head
    const thead = document.getElementById('browse-thead');
    thead.innerHTML = `<tr>
      <th>Card A</th>
      <th>Card B</th>
      <th>GT</th>
      <th>${escHtml(ds)}</th>
      ${otherDs.map(n => `<th>${escHtml(n)}</th>`).join('')}
      <th class="corr-col-header" title="Correctness per model (${allDs.map(escHtml).join(', ')})">Correctness</th>
      <th></th>
    </tr>`;

    // Table body
    const tbody = document.getElementById('browse-tbody');
    if (page.length === 0) {
      tbody.innerHTML = `<tr><td colspan="99" class="empty-state">No pairs match the current filters.</td></tr>`;
    } else {
      tbody.innerHTML = page.map(p => {
        const pid      = p.pair_id;
        const selected = fPair === pid;
        const hasAnn   = !!ANNOTATIONS[pid];

        const gtBadge   = badge(p.gt);
        const predBadge = badge(p[ds]);
        const otherCells = otherDs.map(n => `<td>${badge(p[n])}</td>`).join('');

        const corrIcons = allDs.map(n => {
          const ok = p[n] === p.gt;
          return `<span class="c-icon ${ok ? 'c-ok' : 'c-err'}" title="${escHtml(n)}: ${ok ? 'correct' : 'wrong'}">${ok ? '✓' : '✗'}</span>`;
        }).join('');

        return `<tr class="pair-row${selected ? ' selected-row' : ''}" data-pair="${escHtml(pid)}">
          <td><strong>${escHtml(p.card_a)}</strong></td>
          <td>${escHtml(p.card_b)}</td>
          <td>${gtBadge}</td>
          <td>${predBadge}</td>
          ${otherCells}
          <td class="corr-col">${corrIcons}</td>
          <td class="action-col">${hasAnn ? '<span class="ann-indicator" title="Has annotation">&#9632;</span>' : ''}</td>
        </tr>`;
      }).join('');

      // Row click
      tbody.querySelectorAll('.pair-row').forEach(row => {
        row.addEventListener('click', () => {
          const pid = row.dataset.pair;
          fPair = (fPair === pid) ? '' : pid;
          applyAndRender();
          pushUrlParams();
          if (fPair) {
            const panel = document.getElementById('detail-panel');
            setTimeout(() => panel.scrollIntoView({ behavior: 'smooth', block: 'start' }), 50);
          }
        });
      });
    }

    // Pagination
    renderPagination(totalPages);

    // Table count
    document.getElementById('table-count').textContent =
      `${total} results${total > perPage ? ` — page ${currentPage} of ${totalPages}` : ''}`;

    // Detail panel
    if (fPair) {
      const pair = PAIRS.find(p => p.pair_id === fPair);
      if (pair) showDetailPanel(pair, ds, allDs);
    } else {
      document.getElementById('detail-panel').style.display = 'none';
    }
  }

  function renderPagination(totalPages) {
    const pg = document.getElementById('pagination');
    if (totalPages <= 1) { pg.innerHTML = ''; return; }

    const pages = [];
    const lo = Math.max(1, currentPage - 3);
    const hi = Math.min(totalPages, currentPage + 3);

    if (currentPage > 1) {
      pages.push(`<a href="#" class="page-btn" data-page="${currentPage - 1}">&laquo; Prev</a>`);
    }
    for (let p = lo; p <= hi; p++) {
      pages.push(`<a href="#" class="page-btn${p === currentPage ? ' active' : ''}" data-page="${p}">${p}</a>`);
    }
    if (currentPage < totalPages) {
      pages.push(`<a href="#" class="page-btn" data-page="${currentPage + 1}">Next &raquo;</a>`);
    }
    pg.innerHTML = pages.join('');

    pg.querySelectorAll('.page-btn').forEach(a => {
      a.addEventListener('click', e => {
        e.preventDefault();
        currentPage = parseInt(a.dataset.page, 10);
        applyAndRender();
        pushUrlParams();
        window.scrollTo({ top: 0, behavior: 'smooth' });
      });
    });
  }

  function showDetailPanel(pair, ds, allDs) {
    const panel = document.getElementById('detail-panel');
    panel.style.display = '';

    document.getElementById('detail-card-a').textContent = pair.card_a;
    document.getElementById('detail-card-b').textContent = pair.card_b;

    const valuesDiv = document.getElementById('detail-values');
    const rows = [
      `<div class="detail-value-row detail-truth">
        <span class="detail-ds-name">Ground Truth</span>
        ${badgeLg(pair.gt)}
      </div>`,
      ...allDs.map(n => {
        const val     = pair[n];
        const correct = val === pair.gt;
        const cls     = correct ? 'detail-correct' : 'detail-wrong';
        const verdict = correct ? 'correct' : 'wrong';
        return `<div class="detail-value-row ${cls}">
          <span class="detail-ds-name">${escHtml(n)}</span>
          ${badgeLg(val)}
          <span class="detail-verdict ${verdict}">${verdict}</span>
        </div>`;
      }),
    ];
    valuesDiv.innerHTML = rows.join('');

    // Annotation form
    document.getElementById('ann-pair-id').value = pair.pair_id;
    const ann = ANNOTATIONS[pair.pair_id];
    document.getElementById('ann-note').value     = ann?.note  || '';
    document.getElementById('ann-tags').value     = ann?.tags  || '';
    document.getElementById('ann-form-title').textContent = ann ? 'Edit Annotation' : 'Add Annotation';
    document.getElementById('ann-delete-btn').style.display = ann ? '' : 'none';
  }

  // ── Badge helpers ──────────────────────────────────────────────────────────

  function badge(val) {
    const cls = val === 1 ? 'badge-pos' : (val === -1 ? 'badge-neg' : 'badge-neu');
    const txt = val === 1 ? '+1' : String(val);
    return `<span class="badge ${cls}">${escHtml(txt)}</span>`;
  }

  function badgeLg(val) {
    const cls = val === 1 ? 'badge-pos' : (val === -1 ? 'badge-neg' : 'badge-neu');
    const txt = val === 1 ? '+1' : String(val);
    return `<span class="badge ${cls} badge-lg">${escHtml(txt)}</span>`;
  }

  function escHtml(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

})();
