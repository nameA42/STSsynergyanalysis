/* annotate-app.js — Static version of the Annotate page */

(function () {
  'use strict';

  const ANN_KEY = 'sts_annotations';

  let CONFIG = null;
  let PAIRS  = null;
  let ANNOTATIONS = {};  // pair_id → annotation

  let filterCard = '';
  let filterTag  = '';

  // ── Bootstrap ──────────────────────────────────────────────────────────────

  Promise.all([
    fetch('data/config.json').then(r => r.json()),
    fetch('data/pairs.json').then(r => r.json()),
    fetch('data/annotations.json').then(r => r.json()),
  ]).then(([cfg, pairs, seedAnn]) => {
    CONFIG = cfg;
    PAIRS  = pairs;

    // Load from localStorage, seed from static file if empty
    loadAnnotations(seedAnn);

    // Populate card datalists
    const dl = document.getElementById('card-list');
    CONFIG.cards.forEach(c => {
      const opt = document.createElement('option');
      opt.value = c;
      dl.appendChild(opt);
    });

    wireEvents();
    renderTable();
  }).catch(err => {
    console.error('Failed to load data:', err);
    showToast('Failed to load data files', 'error');
  });

  // ── Annotations ───────────────────────────────────────────────────────────

  function loadAnnotations(seedArr) {
    const stored = localStorage.getItem(ANN_KEY);
    if (stored) {
      try {
        const arr = JSON.parse(stored);
        ANNOTATIONS = {};
        arr.forEach(a => { ANNOTATIONS[a.pair_id] = a; });
      } catch (_) { ANNOTATIONS = {}; }
    } else {
      ANNOTATIONS = {};
      (seedArr || []).forEach(a => { ANNOTATIONS[a.pair_id] = a; });
    }
  }

  function saveAnnotations() {
    localStorage.setItem(ANN_KEY, JSON.stringify(Object.values(ANNOTATIONS)));
  }

  function annCount() {
    return Object.keys(ANNOTATIONS).length;
  }

  // ── Events ─────────────────────────────────────────────────────────────────

  function wireEvents() {
    // Look up pair
    document.getElementById('lookup-btn').addEventListener('click', lookupPair);

    // Add/save annotation form
    document.getElementById('ann-add-form').addEventListener('submit', function (e) {
      e.preventDefault();
      const ca = document.getElementById('new-card-a').value.trim();
      const cb = document.getElementById('new-card-b').value.trim();
      const note = document.getElementById('new-note').value.trim();
      const tags = document.getElementById('new-tags').value.trim();
      if (!ca || !cb) { showToast('Enter both card names', 'error'); return; }

      // Validate pair exists
      const pair = findPair(ca, cb);
      if (!pair) { showToast('Pair not found', 'error'); return; }

      const pairId = pair.pair_id;
      ANNOTATIONS[pairId] = {
        pair_id:      pairId,
        card_a:       pair.card_a,
        card_b:       pair.card_b,
        ground_truth: String(pair.gt),
        note, tags,
        timestamp:    new Date().toISOString().slice(0, 19).replace('T', ' '),
      };
      // Add model predictions
      Object.keys(CONFIG.models).forEach(ds => {
        ANNOTATIONS[pairId][`pred_${ds}`] = String(pair[ds]);
      });

      saveAnnotations();
      showToast('Saved!', 'success');
      // Reset form
      document.getElementById('new-card-a').value = '';
      document.getElementById('new-card-b').value = '';
      document.getElementById('new-note').value   = '';
      document.getElementById('new-tags').value   = '';
      document.getElementById('pair-preview').classList.add('hidden');
      renderTable();
    });

    // Filter
    document.getElementById('filter-ann-btn').addEventListener('click', () => {
      filterCard = document.getElementById('filter-card').value.trim();
      filterTag  = document.getElementById('filter-tag').value.trim();
      renderTable();
    });

    document.getElementById('clear-ann-btn').addEventListener('click', () => {
      filterCard = '';
      filterTag  = '';
      document.getElementById('filter-card').value = '';
      document.getElementById('filter-tag').value  = '';
      renderTable();
    });

    // Export
    document.getElementById('export-btn').addEventListener('click', exportJson);

    // Import
    document.getElementById('import-input').addEventListener('change', importJson);
  }

  // ── Look up pair ───────────────────────────────────────────────────────────

  function lookupPair() {
    const ca = document.getElementById('new-card-a').value.trim();
    const cb = document.getElementById('new-card-b').value.trim();
    if (!ca || !cb) { showToast('Enter both card names', 'error'); return; }

    const pair = findPair(ca, cb);
    if (!pair) { showToast('Pair not found', 'error'); return; }

    const preview  = document.getElementById('pair-preview');
    const valuesEl = document.getElementById('preview-values');

    const gt = pair.gt;
    const rows = [
      `<div class="detail-value-row detail-truth">
        <span class="detail-ds-name">Ground Truth</span>
        ${badgeLg(gt)}
      </div>`,
      ...Object.keys(CONFIG.models).map(name => {
        const val     = pair[name];
        const correct = val === gt;
        const cls     = correct ? 'detail-correct' : 'detail-wrong';
        const verdict = correct ? 'correct' : 'wrong';
        return `<div class="detail-value-row ${cls}">
          <span class="detail-ds-name">${escHtml(name)}</span>
          ${badgeLg(val)}
          <span class="detail-verdict ${verdict}">${verdict}</span>
        </div>`;
      }),
    ];
    valuesEl.innerHTML = rows.join('');

    // Pre-fill note/tags if annotation exists
    const ann = ANNOTATIONS[pair.pair_id];
    if (ann) {
      document.getElementById('new-note').value = ann.note || '';
      document.getElementById('new-tags').value = ann.tags || '';
    } else {
      document.getElementById('new-note').value = '';
      document.getElementById('new-tags').value = '';
    }

    preview.classList.remove('hidden');
  }

  function findPair(ca, cb) {
    // Exact first
    let pair = PAIRS.find(p =>
      p.card_a.toLowerCase() === ca.toLowerCase() &&
      p.card_b.toLowerCase() === cb.toLowerCase()
    );
    // Then substring
    if (!pair) {
      pair = PAIRS.find(p =>
        p.card_a.toLowerCase().includes(ca.toLowerCase()) &&
        p.card_b.toLowerCase().includes(cb.toLowerCase())
      );
    }
    return pair || null;
  }

  // ── Render annotations table ───────────────────────────────────────────────

  function renderTable() {
    document.getElementById('ann-sub').textContent =
      `${annCount()} saved annotation${annCount() !== 1 ? 's' : ''}`;

    let anns = Object.values(ANNOTATIONS);

    // Apply filters
    if (filterCard) {
      const q = filterCard.toLowerCase();
      anns = anns.filter(a =>
        (a.card_a || '').toLowerCase().includes(q) ||
        (a.card_b || '').toLowerCase().includes(q)
      );
    }
    if (filterTag) {
      const q = filterTag.toLowerCase();
      anns = anns.filter(a =>
        (a.tags || '').toLowerCase().includes(q)
      );
    }

    const modelNames = Object.keys(CONFIG.models);
    const wrap = document.getElementById('ann-table-wrap');

    if (anns.length === 0) {
      wrap.innerHTML = '<div class="empty-state">No annotations yet. Browse card pairs and add notes from the Browse tab.</div>';
      return;
    }

    const predCols = modelNames.map(n => `pred_${n}`);

    const rows = anns.map(ann => {
      const gt   = ann.ground_truth;
      const gtBadge = gtBadgeFromStr(gt);

      const predCells = predCols.map(col => {
        const v = ann[col];
        return `<td>${v !== undefined ? badgeFromStr(v) : '<span class="text-muted">—</span>'}</td>`;
      }).join('');

      const tags = (ann.tags || '').split(',').map(t => t.trim()).filter(Boolean)
        .map(t => `<span class="tag-chip">${escHtml(t)}</span>`).join('');

      return `<tr class="ann-row" data-pair="${escHtml(ann.pair_id)}">
        <td>
          <a href="browse.html?pair=${encodeURIComponent(ann.pair_id)}" class="pair-link">
            <strong>${escHtml(ann.card_a || '')}</strong> → ${escHtml(ann.card_b || '')}
          </a>
        </td>
        <td>${gtBadge}</td>
        ${predCells}
        <td class="note-cell">${escHtml(ann.note || '')}</td>
        <td>${tags}</td>
        <td class="text-muted text-sm">${escHtml(ann.timestamp || '')}</td>
        <td>
          <button class="btn btn-ghost btn-xs ann-delete-btn"
                  data-pair-id="${escHtml(ann.pair_id)}" title="Delete">&#10007;</button>
        </td>
      </tr>`;
    }).join('');

    const predHeaders = modelNames.map(n => `<th>${escHtml(n)}</th>`).join('');

    wrap.innerHTML = `
      <div class="table-scroll">
      <table class="data-table ann-table">
        <thead>
          <tr>
            <th>Pair</th>
            <th>GT</th>
            ${predHeaders}
            <th>Note</th>
            <th>Tags</th>
            <th>Added</th>
            <th></th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
      </div>`;

    // Delete buttons
    wrap.querySelectorAll('.ann-delete-btn').forEach(btn => {
      btn.addEventListener('click', function (e) {
        e.stopPropagation();
        const pid = this.dataset.pairId;
        if (!confirm(`Delete annotation for ${pid}?`)) return;
        delete ANNOTATIONS[pid];
        saveAnnotations();
        showToast('Deleted', 'success');
        renderTable();
      });
    });
  }

  // ── Export / Import ────────────────────────────────────────────────────────

  function exportJson() {
    const data = JSON.stringify(Object.values(ANNOTATIONS), null, 2);
    const blob = new Blob([data], { type: 'application/json' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href = url;
    a.download = 'annotations.json';
    a.click();
    URL.revokeObjectURL(url);
  }

  function importJson(e) {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = function (ev) {
      try {
        const arr = JSON.parse(ev.target.result);
        if (!Array.isArray(arr)) throw new Error('Expected array');
        let added = 0, skipped = 0;
        arr.forEach(a => {
          if (!a.pair_id) return;
          if (!ANNOTATIONS[a.pair_id]) { ANNOTATIONS[a.pair_id] = a; added++; }
          else skipped++;
        });
        saveAnnotations();
        renderTable();
        showToast(`Imported ${added} new, ${skipped} skipped (existing kept)`, 'success');
      } catch (err) {
        showToast('Invalid JSON file', 'error');
      }
    };
    reader.readAsText(file);
    // Reset input so same file can be re-imported
    e.target.value = '';
  }

  // ── Badge helpers ──────────────────────────────────────────────────────────

  function badgeLg(val) {
    const cls = val === 1  ? 'badge-pos' : (val === -1 ? 'badge-neg' : 'badge-neu');
    const txt = val === 1  ? '+1' : String(val);
    return `<span class="badge ${cls} badge-lg">${escHtml(txt)}</span>`;
  }

  function badgeFromStr(v) {
    const cls = v === '1'  ? 'badge-pos' : (v === '-1' ? 'badge-neg' : 'badge-neu');
    const txt = v === '1'  ? '+1' : v;
    return `<span class="badge ${cls}">${escHtml(txt)}</span>`;
  }

  function gtBadgeFromStr(v) {
    return badgeFromStr(v);
  }

  function escHtml(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

})();
