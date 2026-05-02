#!/usr/bin/env python3
"""Generate an HTML viewer for relaxed X* and rounded permutation P matrices."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Relaxed and Rounded Matrix Viewer</title>
<style>
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: #f4f1ea;
  color: #171717;
  height: 100vh;
  display: flex;
  overflow: hidden;
}
.sidebar {
  width: 310px;
  background: #111827;
  color: #f9fafb;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #030712;
}
.sidebar-header {
  padding: 18px 18px 14px;
  border-bottom: 1px solid rgba(255,255,255,0.1);
}
.sidebar-title {
  font-weight: 750;
  letter-spacing: -0.02em;
}
.sidebar-subtitle {
  margin-top: 5px;
  color: #9ca3af;
  font-size: 12px;
}
.file-tree {
  overflow: auto;
  padding: 10px 8px 16px;
}
.folder {
  margin-bottom: 7px;
}
.folder-title {
  color: #d1d5db;
  font-size: 13px;
  font-weight: 700;
  padding: 8px 10px;
}
.file-item {
  border: 1px solid transparent;
  border-radius: 10px;
  padding: 9px 10px;
  margin: 5px 4px;
  cursor: pointer;
  background: rgba(255,255,255,0.04);
}
.file-item:hover {
  background: rgba(255,255,255,0.08);
}
.file-item.active {
  background: #f59e0b;
  color: #111827;
}
.file-main {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  font-size: 12px;
  font-weight: 700;
}
.file-meta {
  margin-top: 4px;
  color: inherit;
  opacity: 0.72;
  font-size: 11px;
}
.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.topbar {
  background: #fffaf0;
  border-bottom: 1px solid #e7dcc6;
  padding: 15px 22px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px 20px;
}
.title {
  font-weight: 800;
  font-size: 18px;
  margin-right: 10px;
}
.pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border-radius: 999px;
  padding: 6px 10px;
  font-size: 12px;
  font-weight: 700;
  background: #f3ead8;
  color: #4b3520;
}
.pill.good { background: #dcfce7; color: #166534; }
.pill.bad { background: #fee2e2; color: #991b1b; }
.content {
  flex: 1;
  overflow: auto;
  padding: 22px;
}
.empty {
  min-height: 65vh;
  display: grid;
  place-items: center;
  color: #78716c;
  font-weight: 600;
}
.matrix-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(360px, 1fr));
  gap: 22px;
  align-items: start;
}
.panel {
  background: #fff;
  border: 1px solid #eadfca;
  border-radius: 18px;
  padding: 18px;
  box-shadow: 0 18px 50px rgba(56, 42, 20, 0.08);
}
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 14px;
  margin-bottom: 13px;
}
.panel-title {
  font-size: 16px;
  font-weight: 850;
  letter-spacing: -0.02em;
}
.panel-note {
  color: #78716c;
  font-size: 12px;
}
.matrix-wrap {
  overflow: auto;
  max-width: 100%;
  border-radius: 12px;
  border: 1px solid #eee2cb;
}
table.matrix {
  border-collapse: collapse;
  margin: 0;
  background: #fff;
}
.matrix th,
.matrix td {
  min-width: 38px;
  width: 38px;
  height: 34px;
  border: 1px solid #eee2cb;
  text-align: center;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 10px;
  line-height: 1;
}
.matrix th {
  background: #faf5e9;
  color: #78716c;
  font-weight: 650;
  position: sticky;
  z-index: 1;
}
.matrix th.row-head {
  left: 0;
}
.matrix th.corner {
  left: 0;
  z-index: 2;
}
.matrix td:hover {
  outline: 2px solid #111827;
  outline-offset: -2px;
}
.legend {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  margin-top: 13px;
  color: #78716c;
  font-size: 12px;
}
.legend-bar {
  width: 140px;
  height: 12px;
  border-radius: 999px;
  border: 1px solid #e7dcc6;
  background: linear-gradient(90deg, #ffffff, #fef3c7, #f59e0b, #7c2d12);
}
.diagnostics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px;
  margin-top: 16px;
}
.metric {
  background: #fffbeb;
  border: 1px solid #f3e6bd;
  border-radius: 12px;
  padding: 10px;
}
.metric-label {
  color: #78716c;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.metric-value {
  margin-top: 4px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 13px;
  font-weight: 750;
}
@media (max-width: 1100px) {
  body { display: block; overflow: auto; }
  .sidebar { width: 100%; max-height: 260px; }
  .main { min-height: 70vh; }
  .matrix-grid { grid-template-columns: 1fr; }
}
</style>
</head>
<body>
<aside class="sidebar">
  <div class="sidebar-header">
    <div class="sidebar-title">Relaxed Matrix Viewer</div>
    <div class="sidebar-subtitle">Compare relaxed $X*$ and rounded permutation $P$</div>
  </div>
  <div class="file-tree" id="fileTree"></div>
</aside>
<main class="main">
  <div class="topbar" id="topbar">
    <div class="title">Select a saved run</div>
  </div>
  <div class="content" id="content">
    <div class="empty">Choose a matrix JSON from the sidebar.</div>
  </div>
</main>
<script>
const DATA = __DATA_PLACEHOLDER__;

function fmt(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return 'n/a';
  const n = Number(value);
  if (Math.abs(n) < 1e-10) return '0';
  if (Math.abs(n - 1) < 1e-10) return '1';
  if (Math.abs(n) >= 1000 || Math.abs(n) < 0.001) return n.toExponential(3);
  return n.toFixed(4).replace(/0+$/, '').replace(/[.]$/, '');
}

function caseType(file) {
  return file.case_type || file.comparison_type || 'unspecified';
}

function certificate(file) {
  return file.is_isomorphic === true
    ? { text: 'certified AP = PB', cls: 'good' }
    : { text: 'not certified', cls: 'bad' };
}

function colorFor(value) {
  const v = Math.max(0, Math.min(1, Number(value) || 0));
  if (v < 1e-9) return '#ffffff';
  const light = 96 - Math.round(v * 50);
  const sat = 88 - Math.round(v * 18);
  return `hsl(38, ${sat}%, ${light}%)`;
}

function textColor(value) {
  return Number(value) > 0.62 ? '#fff7ed' : '#1f2937';
}

function matrixTable(matrix, kind) {
  const n = matrix.length;
  let html = '<div class="matrix-wrap"><table class="matrix"><tr><th class="corner"></th>';
  for (let j = 0; j < n; j++) html += `<th>${j}</th>`;
  html += '</tr>';
  for (let i = 0; i < n; i++) {
    html += `<tr><th class="row-head">${i}</th>`;
    for (let j = 0; j < n; j++) {
      const value = Number(matrix[i][j] || 0);
      const display = kind === 'permutation' ? (value > 0.5 ? '1' : '') : fmt(value);
      html += `<td title="${kind}[${i}, ${j}] = ${fmt(value)}" style="background:${colorFor(value)};color:${textColor(value)}">${display}</td>`;
    }
    html += '</tr>';
  }
  html += '</table></div>';
  return html;
}

function metrics(file) {
  const components = file.objective_components || {};
  const rounding = file.rounding || {};
  const items = [
    ['Z*', fmt(file.Z_star)],
    ['I', fmt(file.I)],
    ['degree objective', fmt(components.degree_profile)],
    ['adjacency objective', fmt(components.adjacency)],
    ['best residual', fmt(rounding.best_residual)],
    ['trials run', fmt(rounding.trials_run)],
  ];
  return `<div class="diagnostics">${items.map(([label, value]) => `
    <div class="metric">
      <div class="metric-label">${label}</div>
      <div class="metric-value">${value}</div>
    </div>
  `).join('')}</div>`;
}

function render(file) {
  const cert = certificate(file);
  const n = file.matrix.length;
  document.getElementById('topbar').innerHTML = `
    <div class="title">n = ${n}</div>
    <span class="pill">case: ${caseType(file)}</span>
    <span class="pill ${cert.cls}">${cert.text}</span>
    <span class="pill">I = ${fmt(file.I)}</span>
    <span class="pill">Z* = ${fmt(file.Z_star)}</span>
  `;
  document.getElementById('content').innerHTML = `
    <div class="matrix-grid">
      <section class="panel">
        <div class="panel-header">
          <div>
            <div class="panel-title">Relaxed permutation matrix $X^*$</div>
            <div class="panel-note">Continuous doubly stochastic solver output</div>
          </div>
          <div class="panel-note">${n} x ${n}</div>
        </div>
        ${matrixTable(file.matrix, 'relaxed')}
        <div class="legend"><span>0</span><div class="legend-bar"></div><span>1</span></div>
      </section>
      <section class="panel">
        <div class="panel-header">
          <div>
            <div class="panel-title">Rounded permutation matrix $\\hat P$</div>
            <div class="panel-note">Final discrete candidate after rounding</div>
          </div>
          <div class="panel-note">${n} x ${n}</div>
        </div>
        ${matrixTable(file.permutation || [], 'permutation')}
        <div class="legend"><span>0</span><div class="legend-bar"></div><span>1</span></div>
      </section>
    </div>
    ${metrics(file)}
  `;
}

function buildTree() {
  const tree = document.getElementById('fileTree');
  const sizes = Object.keys(DATA).map(Number).sort((a, b) => a - b);
  for (const n of sizes) {
    const folder = document.createElement('div');
    folder.className = 'folder';
    folder.innerHTML = `<div class="folder-title">n = ${n} (${DATA[n].length})</div>`;
    for (const file of DATA[n]) {
      const item = document.createElement('div');
      item.className = 'file-item';
      const cert = certificate(file);
      item.innerHTML = `
        <div class="file-main">
          <span>${caseType(file)}</span>
          <span>${cert.text.replace(' AP = PB', '')}</span>
        </div>
        <div class="file-meta">${file.id.slice(0, 8)}... | I=${fmt(file.I)} | Z*=${fmt(file.Z_star)}</div>
      `;
      item.addEventListener('click', () => {
        document.querySelectorAll('.file-item').forEach(el => el.classList.remove('active'));
        item.classList.add('active');
        render(file);
      });
      folder.appendChild(item);
    }
    tree.appendChild(folder);
  }
}

buildTree();
</script>
</body>
</html>
"""


def scan_matrices(base_dir: str) -> dict[int, list[dict]]:
    """Read matrix JSON files from base_dir/{n}/*.json."""
    root = Path(base_dir)
    data: dict[int, list[dict]] = {}
    if not root.exists():
        raise FileNotFoundError(f"Matrix directory not found: {base_dir}")

    for path in sorted(root.glob("*/*.json")):
        try:
            n = int(path.parent.name)
        except ValueError:
            continue
        with path.open(encoding="utf-8") as handle:
            entry = json.load(handle)
        if "matrix" not in entry:
            continue
        if "permutation" not in entry:
            continue
        entry["id"] = path.stem
        data.setdefault(n, []).append(entry)

    return dict(sorted(data.items()))


def generate_viewer(data: dict[int, list[dict]], output: str) -> None:
    html = HTML_TEMPLATE.replace("__DATA_PLACEHOLDER__", json.dumps(data))
    Path(output).write_text(html, encoding="utf-8")
    total = sum(len(files) for files in data.values())
    print(f"wrote {output} with {total} saved runs")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build an HTML viewer showing relaxed X* and rounded P side-by-side."
    )
    parser.add_argument("--base-dir", default="data/matrices", help="Directory containing {n}/*.json matrix files")
    parser.add_argument("--output", default="relaxed_matrix_viewer.html", help="Output HTML file")
    args = parser.parse_args()

    data = scan_matrices(args.base_dir)
    generate_viewer(data, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
