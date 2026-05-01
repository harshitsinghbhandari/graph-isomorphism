#!/usr/bin/env python3
"""
Matrix Viewer Generator

Scans a matrices directory of the form {base_dir}/{n}/*.json and generates
a self-contained HTML viewer.
"""

import argparse
import json
import os
from pathlib import Path

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Matrix Viewer</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: #f5f5f4;
  color: #1a1a18;
  display: flex;
  height: 100vh;
  overflow: hidden;
}

/* Sidebar */
.sidebar {
  width: 280px;
  background: #fff;
  border-right: 1px solid #e5e5e3;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}
.sidebar-header {
  padding: 1.25rem 1rem;
  border-bottom: 1px solid #e5e5e3;
  font-weight: 600;
  font-size: 0.95rem;
}
.sidebar-content {
  flex: 1;
  overflow-y: auto;
  padding: 0.5rem 0;
}
.folder {
  user-select: none;
}
.folder-header {
  display: flex;
  align-items: center;
  padding: 0.5rem 1rem;
  cursor: pointer;
  font-weight: 500;
  font-size: 0.85rem;
  color: #555;
  transition: background 0.15s;
}
.folder-header:hover {
  background: #f5f5f4;
}
.folder-header .arrow {
  width: 16px;
  height: 16px;
  margin-right: 6px;
  transition: transform 0.2s;
  color: #888;
}
.folder.open > .folder-header .arrow {
  transform: rotate(90deg);
}
.folder-header .count {
  margin-left: auto;
  font-size: 0.75rem;
  color: #999;
  background: #f0f0ee;
  padding: 2px 6px;
  border-radius: 10px;
}
.folder-files {
  display: none;
  padding-left: 1.5rem;
}
.folder.open > .folder-files {
  display: block;
}
.file-item {
  padding: 0.4rem 1rem;
  font-size: 0.8rem;
  color: #666;
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: background 0.15s;
  border-radius: 4px;
  margin: 2px 8px 2px 0;
}
.file-item:hover {
  background: #e8e8e6;
}
.file-item.active {
  background: #3b82f6;
  color: #fff;
}

/* Main content */
.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.topbar {
  padding: 1rem 1.5rem;
  background: #fff;
  border-bottom: 1px solid #e5e5e3;
  display: flex;
  align-items: center;
  gap: 2rem;
  flex-shrink: 0;
}
.topbar-title {
  font-weight: 600;
  font-size: 1rem;
}
.topbar-meta {
  display: flex;
  gap: 1.5rem;
  font-size: 0.85rem;
}
.meta-item {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}
.meta-label {
  color: #888;
}
.meta-value {
  font-weight: 500;
  font-family: 'SF Mono', Monaco, 'Consolas', monospace;
}
.meta-value.good {
  color: #16a34a;
}
.meta-value.bad {
  color: #dc2626;
}
.meta-value.neutral {
  color: #7c3aed;
}

/* Matrix container */
.matrix-container {
  flex: 1;
  overflow: auto;
  padding: 1.5rem;
}
.case-layout {
  display: grid;
  grid-template-columns: minmax(280px, 1fr) minmax(360px, auto) minmax(280px, 1fr);
  gap: 1.5rem;
  align-items: start;
}
.panel {
  background: #fff;
  border-radius: 12px;
  padding: 1.25rem;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
.panel-title {
  font-size: 0.9rem;
  font-weight: 600;
  margin-bottom: 0.9rem;
}
.panel-subtitle {
  font-size: 0.75rem;
  color: #777;
  margin-bottom: 0.9rem;
  font-family: 'SF Mono', Monaco, 'Consolas', monospace;
}
.matrix-wrapper {
  padding: 0;
  box-shadow: none;
  background: transparent;
  border-radius: 0;
}
.graph-svg {
  width: 100%;
  aspect-ratio: 1;
  display: block;
  background: linear-gradient(180deg, #fcfcfb 0%, #f2f2ef 100%);
  border: 1px solid #e5e5e3;
  border-radius: 10px;
}
.graph-edge {
  stroke: #b8b8b3;
  stroke-width: 1.8;
}
.graph-node {
  fill: #1d4ed8;
  stroke: #ffffff;
  stroke-width: 2;
}
.graph-node-label {
  font-size: 10px;
  fill: #ffffff;
  font-family: 'SF Mono', Monaco, 'Consolas', monospace;
  text-anchor: middle;
  dominant-baseline: middle;
  pointer-events: none;
}
.graph-empty {
  aspect-ratio: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 1rem;
  color: #8a8a84;
  background: #f8f8f6;
  border: 1px dashed #d8d8d3;
  border-radius: 10px;
  font-size: 0.9rem;
}
.matrix {
  border-collapse: collapse;
  margin: 0 auto;
}
.matrix td {
  width: 42px;
  height: 42px;
  text-align: center;
  font-size: 0.7rem;
  font-family: 'SF Mono', Monaco, 'Consolas', monospace;
  border: 1px solid #e5e5e3;
  position: relative;
  transition: transform 0.1s;
}
.matrix.small td {
  width: 36px;
  height: 36px;
  font-size: 0.65rem;
}
.matrix.tiny td {
  width: 28px;
  height: 28px;
  font-size: 0.55rem;
}
.matrix td:hover {
  transform: scale(1.1);
  z-index: 10;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}
.matrix th {
  width: 42px;
  height: 28px;
  font-size: 0.7rem;
  font-weight: 500;
  color: #888;
  text-align: center;
}
.matrix.small th {
  width: 36px;
  font-size: 0.65rem;
}
.matrix.tiny th {
  width: 28px;
  font-size: 0.55rem;
}

/* Color scale legend */
.legend {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-top: 1rem;
  justify-content: center;
  font-size: 0.75rem;
  color: #666;
}
.legend-bar {
  width: 120px;
  height: 12px;
  border-radius: 3px;
  background: linear-gradient(to right, #ffffff, #dbeafe, #3b82f6, #1e40af);
  border: 1px solid #e5e5e3;
}

@media (max-width: 1200px) {
  .case-layout {
    grid-template-columns: 1fr;
  }
}

/* Empty state */
.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #888;
}
.empty-state svg {
  width: 64px;
  height: 64px;
  margin-bottom: 1rem;
  opacity: 0.4;
}
.empty-state p {
  font-size: 0.95rem;
}

/* Scrollbar styling */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: #d1d1cf;
  border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover {
  background: #b0b0ae;
}
</style>
</head>
<body>

<div class="sidebar">
  <div class="sidebar-header">Matrix Viewer</div>
  <div class="sidebar-content" id="fileTree"></div>
</div>

<div class="main">
  <div class="topbar">
    <div class="topbar-title" id="title">Select a matrix</div>
    <div class="topbar-meta" id="meta"></div>
  </div>

  <div class="matrix-container" id="container">
    <div class="empty-state">
      <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
          d="M4 6a2 2 0 012-2h12a2 2 0 012 2v12a2 2 0 01-2 2H6a2 2 0 01-2-2V6z" />
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
          d="M9 4v16M4 9h16M4 15h16M15 4v16" />
      </svg>
      <p>Select a matrix from the sidebar</p>
    </div>
  </div>
</div>

<script>
const DATA = __DATA_PLACEHOLDER__;
const SHOW_GRAPHS = __SHOW_GRAPHS_PLACEHOLDER__;

// Build file tree
const fileTree = document.getElementById('fileTree');
const sizes = Object.keys(DATA).map(Number).sort((a, b) => a - b);

sizes.forEach(n => {
  const files = DATA[n];
  const folder = document.createElement('div');
  folder.className = 'folder';

  folder.innerHTML = `
    <div class="folder-header">
      <svg class="arrow" viewBox="0 0 20 20" fill="currentColor">
        <path fill-rule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clip-rule="evenodd" />
      </svg>
      <span>n = ${n}</span>
      <span class="count">${files.length}</span>
    </div>
    <div class="folder-files"></div>
  `;

  const header = folder.querySelector('.folder-header');
  const filesContainer = folder.querySelector('.folder-files');

  header.addEventListener('click', () => {
    folder.classList.toggle('open');
  });

  files.forEach((file, idx) => {
    const item = document.createElement('div');
    item.className = 'file-item';
    item.textContent = file.id.substring(0, 8) + '...';
    item.title = file.id;
    item.addEventListener('click', () => {
      document.querySelectorAll('.file-item').forEach(el => el.classList.remove('active'));
      item.classList.add('active');
      renderMatrix(n, file);
    });
    filesContainer.appendChild(item);
  });

  fileTree.appendChild(folder);
});

// Open first folder by default
if (fileTree.firstChild) {
  fileTree.firstChild.classList.add('open');
}

function getColor(value) {
  // 0 = white, 0.5 = light blue, 1 = deep blue
  if (value < 0.001) return '#ffffff';
  if (value < 0.1) return `rgba(219, 234, 254, ${value * 5 + 0.3})`;
  if (value < 0.5) return `rgba(59, 130, 246, ${value * 0.8})`;
  return `rgba(30, 64, 175, ${0.4 + value * 0.6})`;
}

function getTextColor(value) {
  return value > 0.5 ? '#fff' : '#333';
}

function formatValue(v) {
  if (Math.abs(v) < 1e-6) return '0';
  if (Math.abs(v - 1) < 1e-6) return '1';
  if (v > 0.01) return v.toFixed(2);
  return v.toExponential(0);
}

function renderGraphPanel(title, graph, emptyMessage) {
  if (!graph || !graph.nodes || !graph.edges) {
    return `
      <div class="panel">
        <div class="panel-title">${title}</div>
        <div class="graph-empty">${emptyMessage}</div>
      </div>
    `;
  }

  const width = 320;
  const height = 320;
  const padding = 34;
  const nodes = graph.nodes.map(node => ({
    ...node,
    svgX: padding + ((node.x + 1) / 2) * (width - padding * 2),
    svgY: padding + ((1 - (node.y + 1) / 2)) * (height - padding * 2),
  }));
  const nodeMap = Object.fromEntries(nodes.map(node => [node.id, node]));

  const edgesSvg = graph.edges.map(edge => {
    const source = nodeMap[edge.source];
    const target = nodeMap[edge.target];
    return `<line class="graph-edge" x1="${source.svgX}" y1="${source.svgY}" x2="${target.svgX}" y2="${target.svgY}" />`;
  }).join('');

  const nodesSvg = nodes.map(node => `
    <g>
      <circle class="graph-node" cx="${node.svgX}" cy="${node.svgY}" r="15" />
      <text class="graph-node-label" x="${node.svgX}" y="${node.svgY}">${node.id}</text>
    </g>
  `).join('');

  return `
    <div class="panel">
      <div class="panel-title">${title}</div>
      <div class="panel-subtitle">${graph.edges.length} edges</div>
      <svg class="graph-svg" viewBox="0 0 ${width} ${height}" aria-label="${title}">
        ${edgesSvg}
        ${nodesSvg}
      </svg>
    </div>
  `;
}

function normalizeCaseType(file) {
  if (file.case_type) return file.case_type;
  return 'unspecified';
}

function getCertificateResult(file) {
  const isIsomorphic = file.is_isomorphic === true;
  return {
    label: isIsomorphic ? 'certified by AP = PB' : 'not certified',
    className: isIsomorphic ? 'good' : 'bad',
  };
}

function renderMatrix(n, file) {
  const title = document.getElementById('title');
  const meta = document.getElementById('meta');
  const container = document.getElementById('container');

  title.textContent = `Matrix n=${n}`;

  const iScore = file.I;
  const expectedType = normalizeCaseType(file);
  const certificateResult = getCertificateResult(file);

  meta.innerHTML = `
    <div class="meta-item">
      <span class="meta-label">Pair:</span>
      <span class="meta-value neutral">${expectedType}</span>
    </div>
    <div class="meta-item">
      <span class="meta-label">Result:</span>
      <span class="meta-value ${certificateResult.className}">${certificateResult.label}</span>
    </div>
    <div class="meta-item">
      <span class="meta-label">I =</span>
      <span class="meta-value neutral">${iScore.toFixed(6)}</span>
    </div>
    <div class="meta-item">
      <span class="meta-label">Z* =</span>
      <span class="meta-value">${file.Z_star.toExponential(4)}</span>
    </div>
    <div class="meta-item">
      <span class="meta-label">File:</span>
      <span class="meta-value" style="font-size: 0.75rem">${file.id.substring(0, 12)}...</span>
    </div>
  `;

  const matrix = file.permutation;
  const size = matrix.length;

  let sizeClass = '';
  if (size > 18) sizeClass = 'tiny';
  else if (size > 12) sizeClass = 'small';

  let html = `<div class="matrix-wrapper">`;
  html += `<table class="matrix ${sizeClass}">`;

  // Header row
  html += '<tr><th></th>';
  for (let j = 0; j < size; j++) {
    html += `<th>${j}</th>`;
  }
  html += '</tr>';

  // Data rows
  for (let i = 0; i < size; i++) {
    html += `<tr><th>${i}</th>`;
    for (let j = 0; j < size; j++) {
      const val = matrix[i][j];
      const bg = getColor(val);
      const fg = getTextColor(val);
      html += `<td style="background:${bg};color:${fg}" title="[${i},${j}] = ${val}">${formatValue(val)}</td>`;
    }
    html += '</tr>';
  }

  html += '</table>';
  html += `
    <div class="legend">
      <span>0</span>
      <div class="legend-bar"></div>
      <span>1</span>
    </div>
  `;
  html += '</div>';

  if (SHOW_GRAPHS) {
    container.innerHTML = `
      <div class="case-layout">
        ${renderGraphPanel('Graph A', file.graph_a, 'Graph A not stored in this result. Rerun the experiment to embed graph snapshots.')}
        <div class="panel">
          <div class="panel-title">Permutation Matrix P</div>
          <div class="panel-subtitle">${size} × ${size}</div>
          ${html}
        </div>
        ${renderGraphPanel('Graph B', file.graph_b, 'Graph B not stored in this result. Rerun the experiment to embed graph snapshots.')}
      </div>
    `;
  } else {
    container.innerHTML = `
      <div class="panel">
        <div class="panel-title">Permutation Matrix P</div>
        <div class="panel-subtitle">${size} × ${size}</div>
        ${html}
      </div>
    `;
  }
}
</script>

</body>
</html>
"""


def scan_matrices(base_dir="data/matrices"):
    """Scan all matrix JSON files and organize by n."""
    data = {}
    base_path = Path(base_dir)

    if not base_path.exists():
        print(f"  Warning: {base_dir} does not exist")
        return data

    for n_folder in sorted(base_path.iterdir()):
        if not n_folder.is_dir():
            continue
        try:
            n = int(n_folder.name)
        except ValueError:
            continue

        files = []
        for json_file in sorted(n_folder.glob("*.json")):
            try:
                with open(json_file) as f:
                    content = json.load(f)
                    content["id"] = json_file.stem
                    files.append(content)
            except Exception as e:
                print(f"  Warning: Could not load {json_file}: {e}")

        if files:
            data[n] = files

    return data


def generate_viewer(data, output_path="matrix_viewer.html", show_graphs=True):
    """Generate the HTML viewer with embedded data."""
    json_data = json.dumps(data)
    html = HTML_TEMPLATE.replace("__DATA_PLACEHOLDER__", json_data)
    html = html.replace("__SHOW_GRAPHS_PLACEHOLDER__", "true" if show_graphs else "false")

    Path(output_path).write_text(html, encoding="utf-8")

    total_files = sum(len(files) for files in data.values())
    print(f"  Generated {output_path}")
    print(f"  {len(data)} sizes, {total_files} matrices total")


def parse_args():
    parser = argparse.ArgumentParser(description="Generate a self-contained matrix viewer HTML.")
    parser.add_argument(
        "--base-dir",
        default="data/matrices",
        help="Directory containing per-n subfolders of matrix JSON files "
             "(default: data/matrices)",
    )
    parser.add_argument(
        "--output",
        default="matrix_viewer.html",
        help="Output HTML path (default: matrix_viewer.html)",
    )
    parser.add_argument(
        "--hide-graphs",
        action="store_true",
        help="Hide Graph A and Graph B panels and show only the permutation matrix",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    print("=" * 50)
    print("  Matrix Viewer Generator")
    print("=" * 50)
    print(f"  Base dir : {args.base_dir}")
    print(f"  Output   : {args.output}")
    print(f"  Graphs   : {'hidden' if args.hide_graphs else 'shown'}")

    data = scan_matrices(args.base_dir)

    if not data:
        print(f"  No matrices found in {args.base_dir}/")
    else:
        generate_viewer(data, args.output, show_graphs=not args.hide_graphs)

    print("=" * 50)
