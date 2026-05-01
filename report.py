"""Generate a compact self-contained HTML report for small solver runs."""

import json
from pathlib import Path

import numpy as np

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Isomorphism Index Benchmark Report</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #f8f8f6; color: #1a1a18; line-height: 1.6; }
  .page { max-width: 1100px; margin: 0 auto; padding: 2rem 1.5rem; }
  h1 { font-size: 1.8rem; font-weight: 600; margin-bottom: 0.25rem; }
  .subtitle { color: #6b6b67; font-size: 0.9rem; margin-bottom: 2rem; }
  .metrics-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 2rem; }
  .metric-card { background: #fff; border: 0.5px solid rgba(0,0,0,0.12);
                 border-radius: 10px; padding: 1rem 1.2rem; }
  .metric-label { font-size: 12px; color: #888; text-transform: uppercase;
                  letter-spacing: 0.05em; margin-bottom: 4px; }
  .metric-value { font-size: 1.5rem; font-weight: 600; }
  .metric-sub { font-size: 12px; color: #888; margin-top: 2px; }
  .chart-card { background: #fff; border: 0.5px solid rgba(0,0,0,0.12);
                border-radius: 10px; padding: 1.25rem 1.5rem; margin-bottom: 1.5rem; }
  .chart-title { font-size: 1rem; font-weight: 500; margin-bottom: 4px; }
  .chart-desc { font-size: 13px; color: #888; margin-bottom: 1rem; }
  .chart-wrap { position: relative; height: 300px; }
  .legend { display: flex; gap: 20px; margin-bottom: 12px; font-size: 13px; color: #555; }
  .legend-dot { width: 10px; height: 10px; border-radius: 2px; display: inline-block;
                margin-right: 5px; vertical-align: middle; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 1rem; }
  th { background: #f4f4f2; text-align: left; padding: 8px 12px;
       font-weight: 500; color: #555; border-bottom: 1px solid #e0e0dc; font-size: 12px; }
  td { padding: 7px 12px; border-bottom: 0.5px solid #ebebeb; }
  tr:hover td { background: #fafafa; }
  .tag-iso { background: #e8f5e9; color: #2e7d32; border-radius: 4px;
             padding: 1px 7px; font-size: 11px; font-weight: 500; }
  .tag-non { background: #fce4ec; color: #c62828; border-radius: 4px;
             padding: 1px 7px; font-size: 11px; font-weight: 500; }
  .section-title { font-size: 1.1rem; font-weight: 500; margin: 2rem 0 1rem; }
  @media (max-width: 700px) { .metrics-grid { grid-template-columns: repeat(2,1fr); } }
</style>
</head>
<body>
<div class="page">
  <h1>Isomorphism Index &mdash; Benchmark Report</h1>
  <p class="subtitle">Gurobi QP solver &bull; nodes 1&ndash;{N_MAX} &bull; {PAIRS} pairs per type per n &bull; &lambda; = {LAMBDA}</p>

  <div class="metrics-grid">
    <div class="metric-card">
      <div class="metric-label">Total solves</div>
      <div class="metric-value">{TOTAL_SOLVES}</div>
      <div class="metric-sub">{PAIRS} iso + {PAIRS} non-iso &times; n</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Slowest solve</div>
      <div class="metric-value">{SLOWEST}s</div>
      <div class="metric-sub">at n = {SLOWEST_N}</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Avg iso score</div>
      <div class="metric-value">{AVG_ISO_SCORE}</div>
      <div class="metric-sub">should be &rarr; 1</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Avg non-iso score</div>
      <div class="metric-value">{AVG_NON_SCORE}</div>
      <div class="metric-sub">should be &rarr; 0</div>
    </div>
  </div>

  <div class="chart-card">
    <div class="chart-title">Solve time vs. graph size</div>
    <div class="chart-desc">Mean wall-clock time per QP solve across all pairs. Error bars show min/max range.</div>
    <div class="legend">
      <span><span class="legend-dot" style="background:#378add"></span>Isomorphic pairs (mean)</span>
      <span><span class="legend-dot" style="background:#d85a30"></span>Non-isomorphic pairs (mean)</span>
    </div>
    <div class="chart-wrap"><canvas id="timeChart"></canvas></div>
  </div>

  <div class="chart-card">
    <div class="chart-title">Isomorphism index I vs. graph size</div>
    <div class="chart-desc">Mean index value I = exp(&minus;&lambda;Z*). Isomorphic pairs should stay near 1; non-isomorphic should be lower.</div>
    <div class="legend">
      <span><span class="legend-dot" style="background:#378add"></span>Isomorphic (mean I)</span>
      <span><span class="legend-dot" style="background:#d85a30"></span>Non-isomorphic (mean I)</span>
    </div>
    <div class="chart-wrap"><canvas id="scoreChart"></canvas></div>
  </div>

  <div class="chart-card">
    <div class="chart-title">Objective value Z* vs. graph size</div>
    <div class="chart-desc">Mean optimal QP objective value. Higher Z* = more structural mismatch.</div>
    <div class="legend">
      <span><span class="legend-dot" style="background:#378add"></span>Isomorphic (mean Z*)</span>
      <span><span class="legend-dot" style="background:#d85a30"></span>Non-isomorphic (mean Z*)</span>
    </div>
    <div class="chart-wrap"><canvas id="zChart"></canvas></div>
  </div>

  <div class="section-title">Full results table</div>
  <div class="chart-card" style="padding: 0; overflow-x: auto;">
    <table>
      <thead>
        <tr>
          <th>n</th>
          <th>Type</th>
          <th>Mean time (s)</th>
          <th>Min time (s)</th>
          <th>Max time (s)</th>
          <th>Std (s)</th>
          <th>Mean I</th>
          <th>Mean Z*</th>
        </tr>
      </thead>
      <tbody id="tableBody"></tbody>
    </table>
  </div>
</div>

<script>
// Parse embedded JSON data defensively so a malformed report fails visibly.
let raw;
try {
  raw = {JSON_DATA};
  if (typeof raw === 'string') {
    raw = JSON.parse(raw);
  }
} catch (e) {
  console.error("Error parsing JSON data:", e);
  raw = [];
}

const ns = raw.map(r => r.n);
const isoMean = raw.map(r => r.iso_time.mean !== null ? +r.iso_time.mean.toFixed(4) : null);
const nonMean = raw.map(r => r.non_iso_time.mean !== null ? +r.non_iso_time.mean.toFixed(4) : null);
const isoMin  = raw.map(r => r.iso_time.min !== null ? +r.iso_time.min.toFixed(4) : null);
const nonMin  = raw.map(r => r.non_iso_time.min !== null ? +r.non_iso_time.min.toFixed(4) : null);
const isoMax  = raw.map(r => r.iso_time.max !== null ? +r.iso_time.max.toFixed(4) : null);
const nonMax  = raw.map(r => r.non_iso_time.max !== null ? +r.non_iso_time.max.toFixed(4) : null);
const isoScore = raw.map(r => r.iso_score.mean !== null ? +r.iso_score.mean.toFixed(4) : null);
const nonScore = raw.map(r => r.non_iso_score.mean !== null ? +r.non_iso_score.mean.toFixed(4) : null);
const isoZ = raw.map(r => r.iso_z.mean !== null ? +r.iso_z.mean.toFixed(4) : null);
const nonZ = raw.map(r => r.non_iso_z.mean !== null ? +r.non_iso_z.mean.toFixed(4) : null);

const BLUE = '#378add', CORAL = '#d85a30';
const BLUE_A = 'rgba(55,138,221,0.15)', CORAL_A = 'rgba(216,90,48,0.15)';

// Chart.js core does not support error bars without an extra plugin.
function makeChart(id, label1, label2, data1, data2, yLabel) {
  const ctx = document.getElementById(id);
  if (!ctx) {
    console.error("Canvas element not found:", id);
    return;
  }

  new Chart(ctx.getContext('2d'), {
    type: 'line',
    data: {
      labels: ns,
      datasets: [
        { label: label1, data: data1, borderColor: BLUE, backgroundColor: BLUE_A,
          pointRadius: 2, borderWidth: 1.5, tension: 0.3, fill: false },
        { label: label2, data: data2, borderColor: CORAL, backgroundColor: CORAL_A,
          pointRadius: 2, borderWidth: 1.5, tension: 0.3, fill: false }
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { title: { display: true, text: 'Number of nodes (n)', font: { size: 12 } },
             ticks: { maxTicksLimit: 20 } },
        y: { title: { display: true, text: yLabel, font: { size: 12 } },
             beginAtZero: true }
      }
    }
  });
}

makeChart('timeChart', 'Isomorphic', 'Non-isomorphic',
          isoMean, nonMean, 'Time (s)');
makeChart('scoreChart', 'Isomorphic', 'Non-isomorphic',
          isoScore, nonScore, 'Index I');
makeChart('zChart', 'Isomorphic', 'Non-isomorphic',
          isoZ, nonZ, 'Objective Z*');

// Render the full table after validating that the target element exists.
const tbody = document.getElementById('tableBody');
if (!tbody) {
  console.error("Table body element not found");
} else {
  try {
    raw.forEach(r => {
      function row(type, time, score, z, cls) {
        const tr = document.createElement('tr');
        const fmt = v => v !== null ? v.toFixed(4) : '—';
        tr.innerHTML = `
          <td>${r.n}</td>
          <td><span class="${cls}">${type}</span></td>
          <td>${fmt(time.mean)}</td>
          <td>${fmt(time.min)}</td>
          <td>${fmt(time.max)}</td>
          <td>${fmt(time.std)}</td>
          <td>${fmt(score.mean)}</td>
          <td>${fmt(z.mean)}</td>`;
        tbody.appendChild(tr);
      }
      row('Isomorphic', r.iso_time, r.iso_score, r.iso_z, 'tag-iso');
      row('Non-iso', r.non_iso_time, r.non_iso_score, r.non_iso_z, 'tag-non');
    });
  } catch (e) {
    console.error("Error populating table:", e);
  }
}
</script>
</body>
</html>
"""

def generate_report(results, n_max, pairs, lambda_val, out_path):
    """Write a self-contained HTML report from aggregated benchmark rows."""
    all_iso_times = [r["iso_time"]["mean"] for r in results if r["iso_time"]["mean"]]
    all_non_times = [r["non_iso_time"]["mean"] for r in results if r["non_iso_time"]["mean"]]
    all_times = all_iso_times + all_non_times

    slowest_val = max(all_times) if all_times else 0
    slowest_n = max(
        results,
        key=lambda r: max(r["iso_time"]["mean"] or 0, r["non_iso_time"]["mean"] or 0),
    )["n"] if results else "n/a"

    iso_scores = [r["iso_score"]["mean"] for r in results if r["iso_score"]["mean"]]
    non_scores = [r["non_iso_score"]["mean"] for r in results if r["non_iso_score"]["mean"]]
    avg_iso_score = float(np.mean(iso_scores)) if iso_scores else 0.0
    avg_non_score = float(np.mean(non_scores)) if non_scores else 0.0

    total_solves = sum(
        (pairs if r["iso_time"]["mean"] else 0) + (pairs if r["non_iso_time"]["mean"] else 0)
        for r in results
    )

    html = HTML_TEMPLATE.replace("{N_MAX}", str(n_max))
    html = html.replace("{PAIRS}", str(pairs))
    html = html.replace("{LAMBDA}", str(lambda_val))
    html = html.replace("{TOTAL_SOLVES}", str(total_solves))
    html = html.replace("{SLOWEST}", f"{slowest_val:.3f}")
    html = html.replace("{SLOWEST_N}", str(slowest_n))
    html = html.replace("{AVG_ISO_SCORE}", f"{avg_iso_score:.4f}")
    html = html.replace("{AVG_NON_SCORE}", f"{avg_non_score:.4f}")

    # Compact JSON is embedded directly into the self-contained HTML report.
    json_str = json.dumps(results)
    html = html.replace("{JSON_DATA}", json_str)

    Path(out_path).write_text(html, encoding="utf-8")
    print(f"  Report saved → {out_path}")
