/* STS Synergy — app.js
   Handles: chart rendering, Plotly click events, toast notifications
*/

// ── Toast ──────────────────────────────────────────────────────────────────

function showToast(msg, type = 'success') {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = `toast ${type} show`;
  clearTimeout(el._timer);
  el._timer = setTimeout(() => el.classList.remove('show'), 3000);
}

// ── Chart rendering ────────────────────────────────────────────────────────
// Convention: for every <div id="chart-X"> there must be a
// <script type="application/json" id="chart-X-data">...</script>
// containing the Plotly figure JSON.

const CHART_CONFIG = {
  responsive: true,
  displaylogo: false,
  modeBarButtonsToRemove: ['select2d', 'lasso2d'],
  toImageButtonOptions: { format: 'png', scale: 2 },
};

function renderCharts() {
  document.querySelectorAll('[id^="chart-"]').forEach(el => {
    if (el.tagName === 'SCRIPT') return;  // skip data scripts
    const dataEl = document.getElementById(el.id + '-data');
    if (!dataEl) return;
    try {
      const fig = JSON.parse(dataEl.textContent);
      Plotly.react(el, fig.data, fig.layout, CHART_CONFIG);

      // After rendering, attach a custom event dispatcher for click events
      // so page-specific scripts can listen cleanly.
      el.on('plotly_click', function(data) {
        if (!data.points || !data.points.length) return;
        const pt = data.points[0];
        el.dispatchEvent(new CustomEvent('sts:plotly_click', { detail: pt, bubbles: true }));
      });
    } catch (e) {
      console.warn('Chart render failed for', el.id, e);
    }
  });
}

// Run chart rendering once the DOM is ready.
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', renderCharts);
} else {
  renderCharts();
}
