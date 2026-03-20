/* browse-app.js — Static version of the Browse page */

(function () {
  'use strict';

  const ANN_KEY = 'sts_annotations';

  let CONFIG      = null;
  let METRICS     = null;
  let PAIRS       = null;
  let ANNOTATIONS = {};  // pair_id → annotation
  let RESPONSES   = {};  // pair_id → {model_name: response_text}
  let MODEL_ORDER = [];  // model names sorted by accuracy descending

  // Filter state
  let fCardA    = '';
  let fCardB    = '';
  let fGt       = '';
  let fCorrect  = {};   // {dsName: '1'|'0'|'-1'|'+1'|''}
  let fPred     = {};   // {dsName: '1'|'0'|'-1'|''}
  let fPair     = '';
  let fSortCol  = '';
  let fSortDir  = 'asc';

  // Pagination
  let perPage    = 50;
  let currentPage = 1;

  // ── Bootstrap ──────────────────────────────────────────────────────────────

  Promise.all([
    fetch('data/config.json').then(r => r.json()),
    fetch('data/metrics.json').then(r => r.json()),
    fetch('data/pairs.json').then(r => r.json()),
    fetch('data/annotations.json').then(r => r.json()),
    fetch('data/responses.json').then(r => r.json()).catch(() => ({})),
  ]).then(([cfg, met, pairs, seedAnn, responses]) => {
    RESPONSES = responses || {};
    CONFIG  = cfg;
    METRICS = met;
    PAIRS   = pairs;

    // Sort models by accuracy descending
    MODEL_ORDER = Object.keys(CONFIG.models).sort((a, b) => {
      const accA = METRICS[a] ? METRICS[a].accuracy : 0;
      const accB = METRICS[b] ? METRICS[b].accuracy : 0;
      return accB - accA;
    });

    // Load annotations from localStorage (merging seed)
    loadAnnotations(seedAnn);

    // Populate card datalist
    const dl = document.getElementById('card-list');
    CONFIG.cards.forEach(c => {
      const opt = document.createElement('option');
      opt.value = c;
      dl.appendChild(opt);
    });

    // Build correctness filter rows
    buildCorrFilter();

    // Build prediction filter rows
    buildPredFilter();

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

  // ── Correctness filter (5-state) ───────────────────────────────────────────

  function buildCorrFilter() {
    const container = document.getElementById('corr-rows');
    container.innerHTML = '';
    MODEL_ORDER.forEach(name => {
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
        // 5-state cycle: '' → '1' → '0' → '-1' → '+1' → ''
        const next = cur === '' ? '1' : cur === '1' ? '0' : cur === '0' ? '-1' : cur === '-1' ? '+1' : '';
        inp.value = next;
        fCorrect[ds] = next;
        applyCorrState(this, next);
      });
    });
  }

  function applyCorrState(btn, val) {
    btn.classList.remove('state-any', 'state-ok', 'state-err', 'state-under', 'state-over');
    if (val === '1') {
      btn.textContent = '✓';
      btn.classList.add('state-ok');
    } else if (val === '0') {
      btn.textContent = '✗';
      btn.classList.add('state-err');
    } else if (val === '-1') {
      btn.textContent = '-x';
      btn.classList.add('state-under');
    } else if (val === '+1') {
      btn.textContent = '+x';
      btn.classList.add('state-over');
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

  // ── Prediction filter ──────────────────────────────────────────────────────

  function buildPredFilter() {
    const container = document.getElementById('pred-rows');
    if (!container) return;
    container.innerHTML = '';
    MODEL_ORDER.forEach(name => {
      const div = document.createElement('div');
      div.className = 'pred-row';
      div.innerHTML = `
        <span class="pred-name">${escHtml(name)}</span>
        <button type="button" class="pred-state-btn state-any" data-ds="${escHtml(name)}">—</button>
        <input type="hidden" id="pred-inp-${escHtml(name)}" value="">`;
      container.appendChild(div);
      fPred[name] = '';
    });

    // Wire buttons
    document.querySelectorAll('.pred-state-btn').forEach(btn => {
      btn.addEventListener('click', function () {
        const ds  = this.dataset.ds;
        const inp = document.getElementById(`pred-inp-${ds}`);
        const cur = inp.value;
        // 4-state cycle: '' → '1' → '0' → '-1' → ''
        const next = cur === '' ? '1' : cur === '1' ? '0' : cur === '0' ? '-1' : '';
        inp.value = next;
        fPred[ds] = next;
        applyPredState(this, next);
      });
    });
  }

  function applyPredState(btn, val) {
    btn.classList.remove('state-any', 'state-pos', 'state-neu', 'state-neg');
    if (val === '1') {
      btn.textContent = '+1';
      btn.classList.add('state-pos');
    } else if (val === '0') {
      btn.textContent = '0';
      btn.classList.add('state-neu');
    } else if (val === '-1') {
      btn.textContent = '-1';
      btn.classList.add('state-neg');
    } else {
      btn.textContent = '—';
      btn.classList.add('state-any');
    }
  }

  function syncPredFilterUI() {
    document.querySelectorAll('.pred-state-btn').forEach(btn => {
      const ds  = btn.dataset.ds;
      const inp = document.getElementById(`pred-inp-${ds}`);
      const val = fPred[ds] || '';
      inp.value = val;
      applyPredState(btn, val);
    });
  }

  // ── URL params ─────────────────────────────────────────────────────────────

  function readUrlParams() {
    const params = new URLSearchParams(window.location.search);
    fCardA   = params.get('card_a') || '';
    fCardB   = params.get('card_b') || '';
    fGt      = params.get('gt')     || '';
    fPair    = params.get('pair')   || '';
    fSortCol = params.get('sort')   || '';
    fSortDir = params.get('order')  || 'asc';
    perPage  = parseInt(params.get('pp') || '50', 10);
    currentPage = parseInt(params.get('page') || '1', 10);

    // Correctness filters
    MODEL_ORDER.forEach(ds => {
      fCorrect[ds] = params.get(`correct_${ds}`) || '';
    });

    // Prediction filters
    MODEL_ORDER.forEach(ds => {
      fPred[ds] = params.get(`pred_${ds}`) || '';
    });

    // Sync UI
    document.getElementById('f-card-a').value = fCardA;
    document.getElementById('f-card-b').value = fCardB;
    document.getElementById('f-gt').value     = fGt;
    syncCorrFilterUI();
    syncPredFilterUI();
    updatePerPageUI();
  }

  function pushUrlParams() {
    const url = new URL(window.location.href);
    url.search = '';
    if (fCardA)  url.searchParams.set('card_a', fCardA);
    if (fCardB)  url.searchParams.set('card_b', fCardB);
    if (fGt)     url.searchParams.set('gt',     fGt);
    if (fPair)   url.searchParams.set('pair',   fPair);
    if (fSortCol) url.searchParams.set('sort',  fSortCol);
    if (fSortDir !== 'asc') url.searchParams.set('order', fSortDir);
    if (perPage !== 50) url.searchParams.set('pp', String(perPage));
    if (currentPage > 1) url.searchParams.set('page', String(currentPage));
    Object.entries(fCorrect).forEach(([ds, val]) => {
      if (val !== '') url.searchParams.set(`correct_${ds}`, val);
    });
    Object.entries(fPred).forEach(([ds, val]) => {
      if (val !== '') url.searchParams.set(`pred_${ds}`, val);
    });
    window.history.pushState({}, '', url.toString());
  }

  // ── Events ─────────────────────────────────────────────────────────────────

  function wireEvents() {
    // Filter button
    document.getElementById('filter-btn').addEventListener('click', collectAndFilter);

    // Clear button
    document.getElementById('clear-btn').addEventListener('click', () => {
      fCardA = ''; fCardB = ''; fGt = ''; fPair = ''; fSortCol = ''; fSortDir = 'asc';
      Object.keys(fCorrect).forEach(k => { fCorrect[k] = ''; });
      Object.keys(fPred).forEach(k => { fPred[k] = ''; });
      document.getElementById('f-card-a').value = '';
      document.getElementById('f-card-b').value = '';
      document.getElementById('f-gt').value     = '';
      syncCorrFilterUI();
      syncPredFilterUI();
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
      const predPanel = document.getElementById('pred-panel');
      if (predPanel) predPanel.classList.remove('open');
    });
    document.addEventListener('click', function (e) {
      if (!document.getElementById('corr-wrap').contains(e.target)) {
        document.getElementById('corr-panel').classList.remove('open');
      }
    });

    // Pred toggle
    const predToggle = document.getElementById('pred-toggle');
    if (predToggle) {
      predToggle.addEventListener('click', function (e) {
        e.stopPropagation();
        document.getElementById('pred-panel').classList.toggle('open');
        document.getElementById('corr-panel').classList.remove('open');
      });
      document.addEventListener('click', function (e) {
        const predWrap = document.getElementById('pred-wrap');
        if (predWrap && !predWrap.contains(e.target)) {
          document.getElementById('pred-panel').classList.remove('open');
        }
      });
    }

    // Pred apply
    const predApply = document.getElementById('pred-apply');
    if (predApply) {
      predApply.addEventListener('click', () => {
        document.getElementById('pred-panel').classList.remove('open');
        collectAndFilter();
      });
    }

    // Pred clear
    const predClear = document.getElementById('pred-clear');
    if (predClear) {
      predClear.addEventListener('click', () => {
        Object.keys(fPred).forEach(k => { fPred[k] = ''; });
        syncPredFilterUI();
      });
    }

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
    return PAIRS.filter(p => {
      // Pair filter
      if (fPair && p.pair_id !== fPair) return false;

      // Card A/B substring
      if (fCardA && !p.card_a.toLowerCase().includes(fCardA.toLowerCase())) return false;
      if (fCardB && !p.card_b.toLowerCase().includes(fCardB.toLowerCase())) return false;

      // GT
      if (fGt !== '' && p.gt !== parseInt(fGt, 10)) return false;

      // Correctness filters (5 states)
      for (const [ds, val] of Object.entries(fCorrect)) {
        if (val === '') continue;
        const pred = p[ds];
        if (val === '1'  && pred !== p.gt) return false;
        if (val === '0'  && pred === p.gt) return false;
        if (val === '-1' && !(pred < p.gt)) return false;
        if (val === '+1' && !(pred > p.gt)) return false;
      }

      // Prediction filters
      for (const [ds, val] of Object.entries(fPred)) {
        if (!val || ![-1, 0, 1].includes(parseInt(val, 10))) continue;
        if (p[ds] !== parseInt(val, 10)) return false;
      }

      return true;
    });
  }

  // ── Compute n_correct for a pair ──────────────────────────────────────────

  function computeNCorrect(p) {
    return MODEL_ORDER.reduce((sum, ds) => sum + (p[ds] === p.gt ? 1 : 0), 0);
  }

  // ── Sorting ────────────────────────────────────────────────────────────────

  function cardIndexOf(cardName) {
    return CONFIG.cards ? CONFIG.cards.indexOf(cardName) : -1;
  }

  function pairIdx(p) {
    const ai = cardIndexOf(p.card_a);
    const bi = cardIndexOf(p.card_b);
    return (ai < 0 ? 9999 : ai) * 1000 + (bi < 0 ? 9999 : bi);
  }

  function applySorting(rows) {
    const ds_name = MODEL_ORDER[0];
    const validCols = new Set(['ground_truth', 'predicted', 'n_correct', 'pair_idx',
      ...MODEL_ORDER.filter(n => n !== ds_name).map(n => `pred_${n}`)]);

    if (!fSortCol || !validCols.has(fSortCol)) {
      // Default: sort by pair_idx (card index order)
      return [...rows].sort((a, b) => pairIdx(a) - pairIdx(b));
    }

    return [...rows].sort((a, b) => {
      let av, bv;
      if (fSortCol === 'ground_truth') { av = a.gt; bv = b.gt; }
      else if (fSortCol === 'predicted') { av = a[ds_name]; bv = b[ds_name]; }
      else if (fSortCol === 'n_correct') { av = computeNCorrect(a); bv = computeNCorrect(b); }
      else if (fSortCol === 'pair_idx') { av = pairIdx(a); bv = pairIdx(b); }
      else {
        // pred_<n>
        const n = fSortCol.slice(5);
        av = a[n];
        bv = b[n];
      }
      if (av === bv) return 0;
      const dir = fSortDir === 'desc' ? -1 : 1;
      return (av < bv ? -1 : 1) * dir;
    });
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  function applyAndRender() {
    const filtered = applyFilters();
    const sorted   = applySorting(filtered);
    const total    = sorted.length;
    const totalPages = Math.max(1, Math.ceil(total / perPage));
    currentPage = Math.min(currentPage, totalPages);

    const start = (currentPage - 1) * perPage;
    const page  = sorted.slice(start, start + perPage);

    const ds_name = MODEL_ORDER[0] || '';
    const otherDs = MODEL_ORDER.slice(1);

    // Subtitle
    const active = Object.values(fCorrect).filter(v => v !== '').length;
    document.getElementById('browse-sub').textContent =
      `${total} pairs${active ? ` · ${active} correctness filter${active !== 1 ? 's' : ''}` : ''}`;

    // Table head
    const thead = document.getElementById('browse-thead');
    thead.innerHTML = buildTableHead(ds_name, otherDs);

    // Wire sort header clicks
    thead.querySelectorAll('[data-sort-col]').forEach(a => {
      a.addEventListener('click', e => {
        e.preventDefault();
        const col = a.dataset.sortCol;
        if (fSortCol === col) {
          fSortDir = fSortDir === 'asc' ? 'desc' : 'asc';
        } else {
          fSortCol = col;
          fSortDir = 'asc';
        }
        currentPage = 1;
        applyAndRender();
        pushUrlParams();
      });
    });

    // Table body
    const tbody = document.getElementById('browse-tbody');
    if (page.length === 0) {
      tbody.innerHTML = `<tr><td colspan="99" class="empty-state">No pairs match the current filters.</td></tr>`;
    } else {
      tbody.innerHTML = page.map(p => {
        const pid      = p.pair_id;
        const selected = fPair === pid;
        const hasAnn   = !!ANNOTATIONS[pid];

        const gtBadge = badge(p.gt);

        // Prediction cells in model_order
        const predCells = MODEL_ORDER.map(n => `<td>${badge(p[n])}</td>`).join('');

        // Correctness icons in model_order
        const corrIcons = MODEL_ORDER.map(n => {
          const pred = p[n];
          const gt   = p.gt;
          if (pred === gt) {
            return `<span class="c-icon c-ok" title="${escHtml(n)}: correct">✓</span>`;
          } else if (pred < gt) {
            return `<span class="c-icon c-under" title="${escHtml(n)}: under">-x</span>`;
          } else {
            return `<span class="c-icon c-over" title="${escHtml(n)}: over">+x</span>`;
          }
        }).join('');

        return `<tr class="pair-row${selected ? ' selected-row' : ''}" data-pair="${escHtml(pid)}">
          <td><strong>${escHtml(p.card_a)}</strong></td>
          <td>${escHtml(p.card_b)}</td>
          <td>${gtBadge}</td>
          ${predCells}
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
      if (pair) showDetailPanel(pair);
    } else {
      document.getElementById('detail-panel').style.display = 'none';
    }
  }

  function buildTableHead(ds_name, otherDs) {
    function sortLink(col, label) {
      const isActive = fSortCol === col;
      const nextDir  = (isActive && fSortDir === 'asc') ? 'desc' : 'asc';
      const arrow    = isActive ? (fSortDir === 'asc' ? ' ↑' : ' ↓') : '';
      const cls      = isActive ? `sortable sorted-${fSortDir}` : 'sortable';
      return `<th class="${cls}"><a href="#" data-sort-col="${escHtml(col)}">${escHtml(label)}${arrow}</a></th>`;
    }

    const modelHeaders = MODEL_ORDER.map(n => {
      const col = (n === ds_name) ? 'predicted' : `pred_${n}`;
      return sortLink(col, n);
    }).join('');

    return `<tr>
      ${sortLink('pair_idx', 'Card A \u2195 Card B')}
      <th>Card B</th>
      ${sortLink('ground_truth', 'GT')}
      ${modelHeaders}
      ${sortLink('n_correct', 'Correctness')}
      <th></th>
    </tr>`;
  }

  function buildPaginationHTML(totalPages, position) {
    if (totalPages <= 1) return '';
    const lo = Math.max(1, currentPage - 3);
    const hi = Math.min(totalPages, currentPage + 3);
    const parts = [];

    parts.push(`<a href="#" class="page-btn page-btn-first${currentPage === 1 ? ' disabled' : ''}" data-page="1" title="First">&laquo;&laquo;</a>`);
    if (currentPage > 1) {
      parts.push(`<a href="#" class="page-btn" data-page="${currentPage - 1}">&laquo; Prev</a>`);
    } else {
      parts.push(`<span class="page-btn disabled">&laquo; Prev</span>`);
    }
    for (let p = lo; p <= hi; p++) {
      parts.push(`<a href="#" class="page-btn${p === currentPage ? ' active' : ''}" data-page="${p}">${p}</a>`);
    }
    parts.push(`<span class="page-jump-wrap">page <input type="number" class="page-jump-input" id="page-jump-${position}" min="1" max="${totalPages}" value="${currentPage}" data-total="${totalPages}"> of ${totalPages}</span>`);
    if (currentPage < totalPages) {
      parts.push(`<a href="#" class="page-btn" data-page="${currentPage + 1}">Next &raquo;</a>`);
    } else {
      parts.push(`<span class="page-btn disabled">Next &raquo;</span>`);
    }
    parts.push(`<a href="#" class="page-btn page-btn-last${currentPage === totalPages ? ' disabled' : ''}" data-page="${totalPages}" title="Last">&raquo;&raquo;</a>`);
    return parts.join('');
  }

  function wirePaginationEvents(container) {
    container.querySelectorAll('.page-btn[data-page]').forEach(a => {
      a.addEventListener('click', e => {
        e.preventDefault();
        if (a.classList.contains('disabled')) return;
        currentPage = parseInt(a.dataset.page, 10);
        applyAndRender();
        pushUrlParams();
        window.scrollTo({ top: 0, behavior: 'smooth' });
      });
    });
    container.querySelectorAll('.page-jump-input').forEach(input => {
      function navigate() {
        const p = parseInt(input.value, 10);
        const total = parseInt(input.dataset.total, 10);
        if (!isNaN(p) && p >= 1 && p <= total) {
          currentPage = p;
          applyAndRender();
          pushUrlParams();
          window.scrollTo({ top: 0, behavior: 'smooth' });
        }
      }
      input.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') { e.preventDefault(); navigate(); }
      });
      input.addEventListener('change', navigate);
    });
  }

  function renderPagination(totalPages) {
    const html = buildPaginationHTML(totalPages, 'top');
    const pgTop = document.getElementById('pagination-top');
    const pgBottom = document.getElementById('pagination-bottom');
    const pgLegacy = document.getElementById('pagination');

    if (pgTop) { pgTop.innerHTML = html; wirePaginationEvents(pgTop); }
    if (pgBottom) { pgBottom.innerHTML = buildPaginationHTML(totalPages, 'bottom'); wirePaginationEvents(pgBottom); }
    if (pgLegacy) { pgLegacy.innerHTML = html; wirePaginationEvents(pgLegacy); }
  }

  function showDetailPanel(pair) {
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
      ...MODEL_ORDER.map(n => {
        const val     = pair[n];
        const correct = val === pair.gt;
        const cls     = correct ? 'detail-correct' : 'detail-wrong';
        let verdict;
        if (correct) { verdict = 'correct'; }
        else if (val < pair.gt) { verdict = '-x under'; }
        else { verdict = '+x over'; }
        const verdictCls = correct ? 'correct' : 'wrong';
        return `<div class="detail-value-row ${cls}">
          <span class="detail-ds-name">${escHtml(n)}</span>
          ${badgeLg(val)}
          <span class="detail-verdict ${verdictCls}">${verdict}</span>
        </div>`;
      }),
    ];
    valuesDiv.innerHTML = rows.join('');

    // Reasoning
    const reasoningSection = document.getElementById('reasoning-section');
    const reasoningItems   = document.getElementById('reasoning-items');
    const pairResponses    = RESPONSES[pair.pair_id] || {};
    const modelNames       = Object.keys(pairResponses);
    if (modelNames.length) {
      reasoningItems.innerHTML = modelNames.map(n =>
        `<details class="reasoning-item">
          <summary class="reasoning-summary">
            <span class="reasoning-model-name">${escHtml(n)}</span>
            <span class="reasoning-arrow">▶</span>
          </summary>
          <div class="reasoning-body">${escHtml(pairResponses[n])}</div>
        </details>`
      ).join('');
      reasoningSection.style.display = '';
    } else {
      reasoningSection.style.display = 'none';
    }

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
