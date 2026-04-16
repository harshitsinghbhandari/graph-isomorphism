#!/usr/bin/env python3
"""
Matrix Viewer Generator

Scans data/matrices/{n}/*.json and generates a self-contained HTML viewer.
"""

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

/* Matrix container */
.matrix-container {
  flex: 1;
  overflow: auto;
  padding: 1.5rem;
  display: flex;
  justify-content: center;
  align-items: flex-start;
}
.matrix-wrapper {
  background: #fff;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
.matrix {
  border-collapse: collapse;
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

function renderMatrix(n, file) {
  const title = document.getElementById('title');
  const meta = document.getElementById('meta');
  const container = document.getElementById('container');

  title.textContent = `Matrix n=${n}`;

  const iScore = file.I;
  const isGood = iScore > 0.9;

  meta.innerHTML = `
    <div class="meta-item">
      <span class="meta-label">I =</span>
      <span class="meta-value ${isGood ? 'good' : 'bad'}">${iScore.toFixed(6)}</span>
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

  const matrix = file.matrix;
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

  container.innerHTML = html;
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


def generate_viewer(data, output_path="matrix_viewer.html"):
    """Generate the HTML viewer with embedded data."""
    json_data = json.dumps(data)
    html = HTML_TEMPLATE.replace("__DATA_PLACEHOLDER__", json_data)

    Path(output_path).write_text(html, encoding="utf-8")

    total_files = sum(len(files) for files in data.values())
    print(f"  Generated {output_path}")
    print(f"  {len(data)} sizes, {total_files} matrices total")


if __name__ == "__main__":
    print("=" * 50)
    print("  Matrix Viewer Generator")
    print("=" * 50)

    data = scan_matrices()

    if not data:
        print("  No matrices found in data/matrices/")
    else:
        generate_viewer(data)

    print("=" * 50)
