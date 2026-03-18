/* charts.js — JS mirror of lib/plotly_charts.py
   All functions return {data: [...], layout: {...}} objects (not JSON strings).
   Call Plotly.react(el, fig.data, fig.layout, CHART_CONFIG) to render.
*/

// ── Base layout helper ────────────────────────────────────────────────────────

function baseLayout(overrides) {
  const base = {
    paper_bgcolor: 'white',
    plot_bgcolor:  'white',
    font: { family: 'Inter, -apple-system, sans-serif', size: 12, color: '#1e293b' },
    margin: { l: 20, r: 20, t: 50, b: 20 },
    hoverlabel: { bgcolor: 'white', bordercolor: '#e2e8f0', font: { size: 12 } },
  };
  // Deep-ish merge for one level
  const result = Object.assign({}, base, overrides);
  // Merge sub-objects
  ['font', 'margin', 'hoverlabel', 'xaxis', 'yaxis', 'legend'].forEach(k => {
    if (base[k] && overrides && overrides[k]) {
      result[k] = Object.assign({}, base[k], overrides[k]);
    }
  });
  return result;
}

// ── Helper: pairs array → 2D matrix ──────────────────────────────────────────

/**
 * Build a 2D array [row][col] from a flat pairs array.
 * @param {Array}  pairs    - flat pairs from pairs.json
 * @param {Array}  cards    - ordered card names
 * @param {string} valueKey - 'gt' or a model name
 * @returns {number[][]}    - 75×75 2D array
 */
function pairsToMatrix(pairs, cards, valueKey) {
  const n = cards.length;
  const idx = {};
  cards.forEach((c, i) => { idx[c] = i; });

  // Initialise with 0 on diagonal, fill from pairs
  const mat = Array.from({ length: n }, () => new Array(n).fill(0));
  pairs.forEach(p => {
    const i = idx[p.card_a];
    const j = idx[p.card_b];
    if (i !== undefined && j !== undefined) {
      mat[i][j] = p[valueKey] !== undefined ? p[valueKey] : 0;
    }
  });
  return mat;
}

// ── Synergy heatmap ───────────────────────────────────────────────────────────

/**
 * @param {number[][]} matrix2d - 75×75 2D array of values
 * @param {string[]}   cards    - card names
 * @param {string}     title
 */
function synergyHeatmap(matrix2d, cards, title) {
  const hover = matrix2d.map((row, i) =>
    row.map((val, j) => `<b>${cards[i]} \u2192 ${cards[j]}</b><br>Value: ${val}`)
  );

  const colorscale = [
    [0.0,  '#dc2626'],  // -1 red
    [0.5,  '#f1f5f9'],  //  0 near-white
    [1.0,  '#16a34a'],  // +1 green
  ];

  return {
    data: [{
      type: 'heatmap',
      z: matrix2d,
      x: cards, y: cards,
      colorscale,
      zmid: 0, zmin: -1, zmax: 1,
      text: hover,
      hovertemplate: '%{text}<extra></extra>',
      colorbar: {
        tickvals: [-1, 0, 1],
        ticktext: ['Anti-synergy (-1)', 'Neutral (0)', 'Synergy (+1)'],
        thickness: 14, len: 0.6,
      },
      xgap: 0.5, ygap: 0.5,
    }],
    layout: baseLayout({
      title: { text: title, font: { size: 15 } },
      height: 780,
      xaxis: { tickangle: 90, tickfont: { size: 7 }, side: 'bottom' },
      yaxis: { tickfont: { size: 7 }, autorange: 'reversed' },
      margin: { l: 130, r: 100, t: 60, b: 140 },
    }),
  };
}

// ── Error heatmap ─────────────────────────────────────────────────────────────

/**
 * @param {number[][]} predMatrix  - 75×75 predictions
 * @param {number[][]} truthMatrix - 75×75 ground truth
 * @param {string[]}   cards
 * @param {string}     title
 */
function errorHeatmap(predMatrix, truthMatrix, cards, title) {
  const n = cards.length;
  const errMatrix = predMatrix.map((row, i) =>
    row.map((val, j) => val - truthMatrix[i][j])
  );

  const hover = errMatrix.map((row, i) =>
    row.map((err, j) => {
      const sign = err >= 0 ? '+' : '';
      return `<b>${cards[i]} \u2192 ${cards[j]}</b><br>Error: ${sign}${err}<br>GT=${truthMatrix[i][j]}  Pred=${predMatrix[i][j]}`;
    })
  );

  const colorscale = [
    [0.0,  '#7c3aed'],  // -2
    [0.25, '#dc2626'],  // -1
    [0.5,  '#f8fafc'],  //  0
    [0.75, '#f97316'],  // +1
    [1.0,  '#b45309'],  // +2
  ];

  return {
    data: [{
      type: 'heatmap',
      z: errMatrix,
      x: cards, y: cards,
      colorscale,
      zmid: 0, zmin: -2, zmax: 2,
      text: hover,
      hovertemplate: '%{text}<extra></extra>',
      colorbar: {
        tickvals: [-2, -1, 0, 1, 2],
        ticktext: ['-2', '-1', '0', '+1', '+2'],
        title: { text: 'Error', side: 'right' },
        thickness: 14, len: 0.6,
      },
      xgap: 0.5, ygap: 0.5,
    }],
    layout: baseLayout({
      title: { text: title, font: { size: 15 } },
      height: 780,
      xaxis: { tickangle: 90, tickfont: { size: 7 }, side: 'bottom' },
      yaxis: { tickfont: { size: 7 }, autorange: 'reversed' },
      margin: { l: 130, r: 100, t: 60, b: 140 },
    }),
  };
}

// ── Confusion matrix ──────────────────────────────────────────────────────────

/**
 * @param {number[][]} cm   - 3×3 array [[TN…][…][…]] labels: -1, 0, +1
 * @param {string}     title
 */
function confusionMatrix(cm, title) {
  const labelNames = ['Negative (-1)', 'Neutral (0)', 'Positive (+1)'];
  const total = cm.flat().reduce((a, b) => a + b, 0);

  const text = cm.map(row =>
    row.map(v => `<b>${v.toLocaleString()}</b><br>(${(v / total * 100).toFixed(1)}%)`)
  );

  return {
    data: [{
      type: 'heatmap',
      z: cm,
      x: labelNames,
      y: labelNames,
      colorscale: [[0, '#f7fbff'], [0.25, '#c6dbef'], [0.5, '#6baed6'], [0.75, '#2171b5'], [1.0, '#08306b']],
      zmin: 0,
      text,
      texttemplate: '%{text}',
      hovertemplate: 'Truth: <b>%{y}</b><br>Predicted: <b>%{x}</b><br>Count: %{z:,}<extra></extra>',
      showscale: false,
      xgap: 2, ygap: 2,
    }],
    layout: baseLayout({
      title: { text: title, font: { size: 15 } },
      height: 380,
      xaxis: { title: 'Predicted', side: 'bottom', tickfont: { size: 11 } },
      yaxis: { title: 'Ground Truth', autorange: 'reversed', tickfont: { size: 11 } },
      margin: { l: 130, r: 20, t: 60, b: 80 },
    }),
  };
}

// ── Class distribution ────────────────────────────────────────────────────────

/**
 * @param {Array}  pairsForDs - pairs filtered/all, has .<dsname> value
 * @param {string} dsName     - key for predicted value
 * @param {string} title
 */
function classDistribution(pairsForDs, dsName, title) {
  const labels = [-1, 0, 1];
  const names  = ['Negative (\u22121)', 'Neutral (0)', 'Positive (+1)'];

  const gtCounts   = labels.map(l => pairsForDs.filter(p => p.gt === l).length);
  const predCounts = labels.map(l => pairsForDs.filter(p => p[dsName] === l).length);

  return {
    data: [
      {
        type: 'bar', name: 'Ground Truth',
        x: names, y: gtCounts,
        marker: { color: '#2563eb' }, opacity: 0.85,
        text: gtCounts.map(String), textposition: 'outside',
        hovertemplate: '%{x}<br>Count: %{y:,}<extra>Ground Truth</extra>',
      },
      {
        type: 'bar', name: 'Predicted',
        x: names, y: predCounts,
        marker: { color: '#ea580c' }, opacity: 0.85,
        text: predCounts.map(String), textposition: 'outside',
        hovertemplate: '%{x}<br>Count: %{y:,}<extra>Predicted</extra>',
      },
    ],
    layout: baseLayout({
      title: { text: title, font: { size: 15 } },
      barmode: 'group', height: 360,
      legend: { orientation: 'h', yanchor: 'bottom', y: 1.02, x: 0 },
      yaxis: { title: 'Count' },
      margin: { l: 60, r: 20, t: 60, b: 60 },
    }),
  };
}

// ── Error breakdown ───────────────────────────────────────────────────────────

/**
 * @param {Array}  pairsForDs - all pairs (has .gt and .<dsName>)
 * @param {string} dsName
 * @param {string} title
 */
function errorBreakdown(pairsForDs, dsName, title) {
  const colorMap = {
    'GT=+1 \u2192 Pred=0':  '#f97316',
    'GT=+1 \u2192 Pred=-1': '#dc2626',
    'GT=0 \u2192 Pred=+1':  '#84cc16',
    'GT=0 \u2192 Pred=-1':  '#94a3b8',
    'GT=-1 \u2192 Pred=0':  '#a855f7',
    'GT=-1 \u2192 Pred=+1': '#7c3aed',
  };

  const total = pairsForDs.length;
  const combos = [
    [-1, 0], [-1, 1],
    [ 0,-1], [ 0, 1],
    [ 1,-1], [ 1, 0],
  ];

  const rows = combos
    .map(([gt, pred]) => {
      const gtStr   = gt   === 1 ? '+1' : String(gt);
      const predStr = pred === 1 ? '+1' : String(pred);
      const label   = `GT=${gtStr} \u2192 Pred=${predStr}`;
      const count   = pairsForDs.filter(p => p.gt === gt && p[dsName] === pred).length;
      return { label, count, pct: count / total * 100 };
    })
    .filter(r => r.count > 0)
    .sort((a, b) => b.count - a.count);

  return {
    data: [{
      type: 'bar',
      x: rows.map(r => r.label),
      y: rows.map(r => r.count),
      marker: { color: rows.map(r => colorMap[r.label] || '#64748b') },
      text: rows.map(r => `${r.pct.toFixed(1)}%`),
      textposition: 'outside',
      hovertemplate: '%{x}<br>Count: %{y:,}<br>%{text} of all pairs<extra></extra>',
    }],
    layout: baseLayout({
      title: { text: title, font: { size: 15 } },
      height: 380,
      xaxis: { tickangle: 20, tickfont: { size: 11 } },
      yaxis: { title: 'Count' },
      margin: { l: 60, r: 20, t: 60, b: 110 },
    }),
  };
}

// ── Per-card accuracy ─────────────────────────────────────────────────────────

/**
 * @param {Object} perCardData - {cardname: {accuracy, n_errors, n_total, macro_f1}}
 * @param {string} title
 */
function perCardAccuracy(perCardData, title) {
  const cards = Object.keys(perCardData);

  // Sort by accuracy ascending
  cards.sort((a, b) => perCardData[a].accuracy - perCardData[b].accuracy);

  const accs = cards.map(c => perCardData[c].accuracy);
  const errs = cards.map(c => perCardData[c].n_errors);

  function colorFor(a) {
    if (a < 0.60) return '#dc2626';
    if (a < 0.75) return '#f97316';
    if (a < 0.90) return '#84cc16';
    return '#16a34a';
  }

  const mean = accs.reduce((s, v) => s + v, 0) / accs.length;

  return {
    data: [{
      type: 'bar',
      x: accs.map(a => a * 100),
      y: cards,
      orientation: 'h',
      marker: { color: accs.map(colorFor) },
      text: accs.map(a => `${(a * 100).toFixed(1)}%`),
      textposition: 'outside',
      customdata: cards.map((c, i) => [c, errs[i]]),
      hovertemplate: '<b>%{y}</b><br>Accuracy: %{x:.1f}%<br>Errors: %{customdata[1]}<extra></extra>',
    }],
    layout: baseLayout({
      title: { text: title, font: { size: 15 } },
      height: 920,
      xaxis: { range: [0, 112], title: 'Accuracy (%)', tickfont: { size: 11 } },
      yaxis: { tickfont: { size: 9 } },
      margin: { l: 150, r: 80, t: 60, b: 60 },
      shapes: [{
        type: 'line',
        x0: mean * 100, x1: mean * 100,
        y0: 0, y1: 1, yref: 'paper',
        line: { dash: 'dash', color: '#1e293b', width: 1.5 },
      }],
      annotations: [{
        x: mean * 100, y: 1, yref: 'paper',
        text: `Mean ${(mean * 100).toFixed(1)}%`,
        showarrow: false,
        xanchor: 'left', yanchor: 'top',
        font: { size: 11 },
      }],
    }),
  };
}

// ── Metrics comparison ────────────────────────────────────────────────────────

/**
 * @param {Object} metricsDict - {dsname: metricsObj}
 * @param {string} title
 */
function metricsComparison(metricsDict, title) {
  const names  = Object.keys(metricsDict);
  const keys   = ['accuracy', 'macro_f1', 'weighted_f1', 'macro_precision', 'macro_recall'];
  const labels = ['Accuracy', 'Macro F1', 'Weighted F1', 'Macro Prec.', 'Macro Rec.'];
  // Set2-like palette
  const palette = ['#66c2a5','#fc8d62','#8da0cb','#e78ac3','#a6d854','#ffd92f','#e5c494'];

  return {
    data: names.map((ds, i) => ({
      type: 'bar', name: ds,
      x: labels,
      y: keys.map(k => metricsDict[ds][k]),
      marker: { color: palette[i % palette.length] }, opacity: 0.88,
      text: keys.map(k => metricsDict[ds][k].toFixed(3)),
      textposition: 'outside',
      hovertemplate: `%{x}: <b>%{y:.4f}</b><extra>${ds}</extra>`,
    })),
    layout: baseLayout({
      title: { text: title, font: { size: 15 } },
      barmode: 'group', height: 440,
      yaxis: { range: [0, 1.15], title: 'Score' },
      legend: { orientation: 'h', yanchor: 'bottom', y: 1.02, x: 0 },
      margin: { l: 60, r: 20, t: 70, b: 60 },
    }),
  };
}

// ── Per-card comparison ───────────────────────────────────────────────────────

/**
 * @param {Object} perCardDict - {dsname: {cardname: {accuracy}}}
 * @param {string} title
 */
function perCardComparison(perCardDict, title) {
  const names = Object.keys(perCardDict);
  const allCards = Object.keys(perCardDict[names[0]]);

  // Sort by mean accuracy
  allCards.sort((a, b) => {
    const ma = names.reduce((s, n) => s + (perCardDict[n][a]?.accuracy || 0), 0) / names.length;
    const mb = names.reduce((s, n) => s + (perCardDict[n][b]?.accuracy || 0), 0) / names.length;
    return ma - mb;
  });

  const palette = ['#e41a1c','#377eb8','#4daf4a','#984ea3','#ff7f00','#a65628','#f781bf'];

  return {
    data: names.map((ds, i) => ({
      type: 'bar', name: ds,
      x: allCards.map(c => (perCardDict[ds][c]?.accuracy || 0) * 100),
      y: allCards,
      orientation: 'h',
      marker: { color: palette[i % palette.length] }, opacity: 0.82,
      hovertemplate: `<b>%{y}</b><br>${ds}: %{x:.1f}%<extra></extra>`,
    })),
    layout: baseLayout({
      title: { text: title, font: { size: 15 } },
      barmode: 'group', height: 1100,
      xaxis: { range: [0, 112], title: 'Accuracy (%)', tickfont: { size: 10 } },
      yaxis: { tickfont: { size: 8 } },
      legend: { orientation: 'h', yanchor: 'bottom', y: 1.01, x: 0 },
      margin: { l: 160, r: 20, t: 70, b: 60 },
    }),
  };
}

// ── Agreement heatmap ─────────────────────────────────────────────────────────

/**
 * @param {string[]} names      - dataset names
 * @param {Array}    pairsData  - all pairs (each has .<dsname> key)
 * @param {string}   title
 */
function agreementHeatmap(names, pairsData, title) {
  const mat = names.map(n1 =>
    names.map(n2 => {
      let agree = 0;
      pairsData.forEach(p => { if (p[n1] === p[n2]) agree++; });
      return agree / pairsData.length;
    })
  );
  const text = mat.map(row => row.map(v => v.toFixed(3)));

  return {
    data: [{
      type: 'heatmap',
      z: mat, x: names, y: names,
      colorscale: 'YlOrRd', zmin: 0, zmax: 1,
      text, texttemplate: '%{text}',
      hovertemplate: '%{y} vs %{x}: %{z:.3f}<extra></extra>',
    }],
    layout: baseLayout({
      title: { text: title, font: { size: 15 } },
      height: Math.max(300, names.length * 100 + 120),
      margin: { l: 120, r: 20, t: 60, b: 80 },
    }),
  };
}

// ── Card profile charts ───────────────────────────────────────────────────────

/**
 * Fused view: all models + GT as grouped bars, one group per other card.
 * @param {Array}    profileData  - list of {other_card, gt, model1, model2, ...}
 * @param {string[]} modelNames   - enabled model names
 * @param {string}   card
 * @param {string}   role         - 'a' or 'b'
 * @param {string}   title
 */
function cardProfileFused(profileData, modelNames, card, role, title) {
    const otherCards = profileData.map(r => r.other_card);
    const gtVals = profileData.map(r => r.gt);
    const COLORS = {
        GT: '#1e293b', gpt4o: '#2563eb', gpt54: '#7c3aed',
        gemini10pro: '#16a34a', gemini15flash: '#059669',
        gpt4omini: '#ea580c', gpt4ominift: '#dc2626',
    };
    const DEF_COLORS = ['#2563eb','#7c3aed','#16a34a','#ea580c','#dc2626','#0891b2','#ca8a04'];

    const traces = [{
        type: 'bar', name: 'GT', x: otherCards, y: gtVals,
        marker: {color: COLORS.GT || '#1e293b'}, opacity: 0.9,
        hovertemplate: '<b>%{x}</b><br>GT: %{y}<extra></extra>',
    }];
    modelNames.forEach((n, i) => {
        traces.push({
            type: 'bar', name: n,
            x: otherCards, y: profileData.map(r => r[n] !== undefined ? r[n] : 0),
            marker: {color: COLORS[n] || DEF_COLORS[i % DEF_COLORS.length]},
            opacity: 0.82,
            hovertemplate: `<b>%{x}</b><br>${n}: %{y}<extra></extra>`,
        });
    });
    return {
        data: traces,
        layout: baseLayout({
            title: {text: title, font: {size: 15}},
            barmode: 'group', height: 500,
            yaxis: {title: 'Synergy Value', tickvals: [-1,0,1], ticktext: ['-1','0','+1'], range: [-1.5,1.5]},
            xaxis: {tickangle: 90, tickfont: {size: 7}},
            legend: {orientation: 'h', yanchor: 'bottom', y: 1.02, x: 0},
            margin: {l: 80, r: 20, t: 70, b: 160},
        }),
    };
}

/**
 * Separate view for one model: GT vs model predictions as grouped bars.
 * @param {Array}  profileData - list of {other_card, gt, <modelName>}
 * @param {string} modelName
 * @param {string} card
 * @param {string} role        - 'a' or 'b'
 * @param {string} title
 */
function cardProfileSeparate(profileData, modelName, card, role, title) {
    const otherCards = profileData.map(r => r.other_card);
    return {
        data: [
            {type:'bar', name:'GT', x: otherCards, y: profileData.map(r=>r.gt),
             marker:{color:'#1e293b'}, opacity:0.85,
             hovertemplate:'<b>%{x}</b><br>GT: %{y}<extra></extra>'},
            {type:'bar', name: modelName, x: otherCards, y: profileData.map(r=>r[modelName]||0),
             marker:{color:'#2563eb'}, opacity:0.82,
             hovertemplate:`<b>%{x}</b><br>${modelName}: %{y}<extra></extra>`},
        ],
        layout: baseLayout({
            title: {text: title, font: {size: 15}},
            barmode: 'group', height: 460,
            yaxis: {title:'Synergy Value', tickvals:[-1,0,1], ticktext:['-1','0','+1'], range:[-1.5,1.5]},
            xaxis: {tickangle:90, tickfont:{size:7}},
            legend: {orientation:'h', yanchor:'bottom', y:1.02, x:0},
            margin: {l:80, r:20, t:70, b:160},
        }),
    };
}

// ── Delta per-card ────────────────────────────────────────────────────────────

/**
 * @param {Object} perCard1 - {cardname: {accuracy}}
 * @param {Object} perCard2 - {cardname: {accuracy}}
 * @param {string} name1
 * @param {string} name2
 * @param {string} title
 */
function deltaPerCard(perCard1, perCard2, name1, name2, title) {
  const cards = Object.keys(perCard1);
  const deltas = cards.map(c =>
    ((perCard2[c]?.accuracy || 0) - (perCard1[c]?.accuracy || 0)) * 100
  );

  // Sort by delta
  const order = cards.map((c, i) => i).sort((a, b) => deltas[a] - deltas[b]);
  const sortedCards  = order.map(i => cards[i]);
  const sortedDeltas = order.map(i => deltas[i]);

  return {
    data: [{
      type: 'bar',
      x: sortedDeltas,
      y: sortedCards,
      orientation: 'h',
      marker: { color: sortedDeltas.map(v => v >= 0 ? '#16a34a' : '#dc2626') },
      hovertemplate: '<b>%{y}</b><br>Delta: %{x:+.1f}%<extra></extra>',
    }],
    layout: baseLayout({
      title: { text: `${title}: ${name1} \u2192 ${name2}`, font: { size: 15 } },
      height: 920,
      xaxis: { title: `Accuracy change (%) ${name1} \u2192 ${name2}`, tickfont: { size: 10 } },
      yaxis: { tickfont: { size: 9 } },
      margin: { l: 160, r: 20, t: 60, b: 60 },
      shapes: [{
        type: 'line',
        x0: 0, x1: 0, y0: 0, y1: 1, yref: 'paper',
        line: { color: '#1e293b', width: 1.2 },
      }],
    }),
  };
}
