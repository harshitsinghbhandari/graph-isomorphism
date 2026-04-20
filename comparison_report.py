#!/usr/bin/env python3

import json
import math
from html import escape
from pathlib import Path


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Detailed Comparison Report</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: #f6f6f3;
  color: #1c1c19;
  line-height: 1.5;
}
.page {
  max-width: 1480px;
  margin: 0 auto;
  padding: 1.5rem;
}
.hero {
  margin-bottom: 1.5rem;
}
.hero h1 {
  font-size: 1.8rem;
  font-weight: 700;
}
.hero p {
  margin-top: 0.35rem;
  color: #676760;
  font-size: 0.95rem;
}
.metrics {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
  margin-bottom: 1.5rem;
}
.metric-card, .section-card, .result-card {
  background: #fff;
  border: 1px solid #e6e6e2;
  border-radius: 14px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}
.metric-card {
  padding: 1rem 1.1rem;
}
.metric-label {
  font-size: 0.72rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #7d7d76;
  margin-bottom: 0.3rem;
}
.metric-value {
  font-size: 1.45rem;
  font-weight: 700;
}
.metric-sub {
  margin-top: 0.2rem;
  font-size: 0.82rem;
  color: #7d7d76;
}
.section-card {
  padding: 1.2rem;
  margin-bottom: 1.5rem;
}
.section-title {
  font-size: 1.05rem;
  font-weight: 650;
  margin-bottom: 0.9rem;
}
.flag-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.88rem;
}
.flag-table th,
.flag-table td {
  padding: 0.7rem 0.75rem;
  border-bottom: 1px solid #ecece8;
  text-align: left;
}
.flag-table th {
  color: #6c6c66;
  font-size: 0.76rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.badge {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 0.18rem 0.55rem;
  font-size: 0.74rem;
  font-weight: 600;
}
.badge.iso { background: #e8f5e9; color: #226b2d; }
.badge.non { background: #fdebec; color: #b52739; }
.badge.warn { background: #fff4d7; color: #9a6700; }
.badge.ok { background: #e8f5ff; color: #1257a5; }
.results {
  display: grid;
  gap: 1rem;
}
.result-card {
  padding: 1.1rem;
}
.result-header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.9rem;
  margin-bottom: 0.9rem;
}
.result-title {
  font-size: 1rem;
  font-weight: 650;
}
.result-subtitle {
  color: #707069;
  font-size: 0.84rem;
  font-family: 'SF Mono', Monaco, 'Consolas', monospace;
}
.result-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
}
.pill {
  background: #f1f1ed;
  border-radius: 999px;
  padding: 0.35rem 0.65rem;
  font-size: 0.8rem;
}
.pill.warn {
  background: #fff1cf;
}
.visual-grid {
  display: grid;
  grid-template-columns: minmax(260px, 1fr) minmax(360px, auto) minmax(260px, 1fr);
  gap: 1rem;
  align-items: start;
}
.panel {
  border: 1px solid #ecece8;
  border-radius: 12px;
  padding: 0.9rem;
  background: #fcfcfa;
}
.panel-title {
  font-size: 0.88rem;
  font-weight: 650;
  margin-bottom: 0.25rem;
}
.panel-subtitle {
  font-size: 0.75rem;
  color: #777771;
  margin-bottom: 0.7rem;
  font-family: 'SF Mono', Monaco, 'Consolas', monospace;
}
.graph-svg {
  width: 100%;
  aspect-ratio: 1;
  display: block;
  background: linear-gradient(180deg, #fbfbf8 0%, #f1f1ed 100%);
  border: 1px solid #e5e5df;
  border-radius: 10px;
}
.graph-edge {
  stroke: #b9b9b2;
  stroke-width: 1.8;
}
.graph-node {
  fill: #1d4ed8;
  stroke: #fff;
  stroke-width: 2;
}
.graph-node-label {
  font-size: 10px;
  fill: #fff;
  font-family: 'SF Mono', Monaco, 'Consolas', monospace;
  text-anchor: middle;
  dominant-baseline: middle;
}
.matrix {
  border-collapse: collapse;
  margin: 0 auto;
}
.matrix th, .matrix td {
  width: 34px;
  height: 34px;
  border: 1px solid #e7e7e2;
  text-align: center;
  font-size: 0.64rem;
  font-family: 'SF Mono', Monaco, 'Consolas', monospace;
}
.matrix th {
  color: #88867d;
  font-weight: 500;
}
.matrix.tiny th, .matrix.tiny td {
  width: 28px;
  height: 28px;
  font-size: 0.56rem;
}
.legend {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.7rem;
  margin-top: 0.7rem;
  font-size: 0.75rem;
  color: #707069;
}
.legend-bar {
  width: 110px;
  height: 10px;
  border-radius: 999px;
  background: linear-gradient(to right, #ffffff, #dbeafe, #3b82f6, #1e40af);
  border: 1px solid #e5e5df;
}
.analysis-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.75rem;
  margin-top: 1rem;
}
.analysis-card {
  background: #f7f7f4;
  border: 1px solid #ecece8;
  border-radius: 10px;
  padding: 0.8rem;
}
.analysis-label {
  font-size: 0.73rem;
  color: #73736d;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.analysis-value {
  font-size: 1.05rem;
  font-weight: 650;
  margin-top: 0.18rem;
}
.analysis-copy {
  font-size: 0.8rem;
  color: #6e6e68;
  margin-top: 0.35rem;
}
@media (max-width: 1260px) {
  .metrics { grid-template-columns: repeat(2, 1fr); }
  .visual-grid { grid-template-columns: 1fr; }
  .analysis-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 760px) {
  .metrics, .analysis-grid { grid-template-columns: 1fr; }
}
</style>
</head>
<body>
<div class="page">
  <section class="hero">
    <h1>Detailed Comparison Report</h1>
    <p>Per-comparison diagnostics for graph pair classification, ambiguity, and soft assignment quality.</p>
  </section>

  <section class="metrics">
    <div class="metric-card">
      <div class="metric-label">Comparisons</div>
      <div class="metric-value">{TOTAL_RESULTS}</div>
      <div class="metric-sub">all saved matrix results</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Label Disagreements</div>
      <div class="metric-value">{DISAGREEMENTS}</div>
      <div class="metric-sub">ground truth vs score interpretation</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">High Ambiguity</div>
      <div class="metric-value">{AMBIGUOUS_COUNT}</div>
      <div class="metric-sub">soft/fractional assignments</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Avg Row Max</div>
      <div class="metric-value">{AVG_ROW_MAX}</div>
      <div class="metric-sub">closer to 1 means sharper matching</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Avg Entropy</div>
      <div class="metric-value">{AVG_ENTROPY}</div>
      <div class="metric-sub">higher means more diffuse X*</div>
    </div>
  </section>

  <section class="section-card">
    <div class="section-title">Flagged Cases</div>
    <table class="flag-table">
      <thead>
        <tr>
          <th>n</th>
          <th>Expected</th>
          <th>Score Interpretation</th>
          <th>I</th>
          <th>Row Max</th>
          <th>Entropy</th>
          <th>Flags</th>
          <th>File</th>
        </tr>
      </thead>
      <tbody>
        {FLAG_ROWS}
      </tbody>
    </table>
  </section>

  <section class="section-card">
    <div class="section-title">All Comparisons</div>
    <div class="results">
      {RESULT_CARDS}
    </div>
  </section>
</div>
</body>
</html>
"""


def _sorted_matrix_paths(base_dir):
    return sorted(Path(base_dir).glob("*/*.json"), key=lambda p: (int(p.parent.name), p.name))


def _row_ambiguity_metrics(matrix):
    row_maxes = []
    margins = []
    entropies = []
    fractional_count = 0

    for row in matrix:
        sorted_row = sorted(row, reverse=True)
        max_val = sorted_row[0] if sorted_row else 0.0
        second = sorted_row[1] if len(sorted_row) > 1 else 0.0
        row_maxes.append(max_val)
        margins.append(max_val - second)

        positive = [value for value in row if value > 1e-12]
        if len(row) > 1 and positive:
            entropy = -sum(value * math.log(value) for value in positive) / math.log(len(row))
        else:
            entropy = 0.0
        entropies.append(entropy)

        fractional_count += sum(1 for value in row if 1e-6 < value < 1 - 1e-6)

    return {
        "mean_row_max": sum(row_maxes) / len(row_maxes) if row_maxes else 0.0,
        "mean_margin": sum(margins) / len(margins) if margins else 0.0,
        "normalized_entropy": sum(entropies) / len(entropies) if entropies else 0.0,
        "fractional_count": fractional_count,
    }


def _entry_analysis(entry):
    matrix = entry["matrix"]
    metrics = _row_ambiguity_metrics(matrix)
    expected_type = entry.get("comparison_type")
    cert = entry.get("is_isomorphic")
    predicted_type = "likely isomorphic" if entry["I"] > 0.9 else "likely non-isomorphic"
    cert_label = "isomorphic (certified)" if cert else "non-isomorphic (certified)" if cert is not None else "no certificate"
    flags = []

    if expected_type == "isomorphic" and predicted_type != "likely isomorphic":
        flags.append("label disagreement")
    if expected_type == "non-isomorphic" and predicted_type != "likely non-isomorphic":
        flags.append("label disagreement")
    if cert is not None and expected_type == "non-isomorphic" and cert:
        flags.append("false positive (certificate)")
    if metrics["mean_row_max"] < 0.85:
        flags.append("diffuse rows")
    if metrics["mean_margin"] < 0.15:
        flags.append("low match margin")
    if metrics["normalized_entropy"] > 0.35:
        flags.append("high entropy")
    if metrics["fractional_count"] > len(matrix):
        flags.append("fractional X*")

    if flags:
        summary = "The result is either inconsistent with the expected pair type or the assignment remains notably soft."
    else:
        summary = "The score and assignment shape are internally consistent with a sharp correspondence."

    return {
        **entry,
        **metrics,
        "expected_type": expected_type or "unknown",
        "predicted_type": predicted_type,
        "cert_label": cert_label,
        "score_gap": abs(entry["I"] - 0.9),
        "flags": flags,
        "summary": summary,
    }


def _summary(entries):
    total = len(entries)
    disagreements = sum(1 for entry in entries if "label disagreement" in entry["flags"])
    ambiguous = sum(1 for entry in entries if len(entry["flags"]) > 0)
    avg_row_max = sum(entry["mean_row_max"] for entry in entries) / total if total else 0.0
    avg_entropy = sum(entry["normalized_entropy"] for entry in entries) / total if total else 0.0
    return {
        "total": total,
        "disagreements": disagreements,
        "ambiguous": ambiguous,
        "avg_row_max": avg_row_max,
        "avg_entropy": avg_entropy,
    }


def _value_color(value):
    if value < 0.001:
        return "#ffffff", "#333333"
    if value < 0.1:
        return f"rgba(219, 234, 254, {value * 5 + 0.3})", "#333333"
    if value < 0.5:
        return f"rgba(59, 130, 246, {value * 0.8})", "#333333"
    return f"rgba(30, 64, 175, {0.4 + value * 0.6})", "#ffffff"


def _format_matrix_value(value):
    if abs(value) < 1e-6:
        return "0"
    if abs(value - 1) < 1e-6:
        return "1"
    if value > 0.01:
        return f"{value:.2f}"
    return f"{value:.0e}"


def _render_matrix_html(matrix):
    size = len(matrix)
    size_class = " tiny" if size > 12 else ""
    header = "".join(f"<th>{idx}</th>" for idx in range(size))
    rows = []
    for row_idx, row in enumerate(matrix):
        cells = []
        for value in row:
            bg, fg = _value_color(value)
            cells.append(
                f'<td style="background:{bg};color:{fg}">{escape(_format_matrix_value(value))}</td>'
            )
        rows.append(f"<tr><th>{row_idx}</th>{''.join(cells)}</tr>")
    return (
        f'<table class="matrix{size_class}"><tr><th></th>{header}</tr>{"".join(rows)}</table>'
        '<div class="legend"><span>0</span><div class="legend-bar"></div><span>1</span></div>'
    )


def _render_graph_html(graph, title):
    width = 320
    height = 320
    padding = 34
    nodes = []
    node_map = {}
    for node in graph["nodes"]:
        svg_x = padding + ((node["x"] + 1) / 2) * (width - padding * 2)
        svg_y = padding + ((1 - (node["y"] + 1) / 2)) * (height - padding * 2)
        node_info = {
            "id": node["id"],
            "svg_x": svg_x,
            "svg_y": svg_y,
        }
        nodes.append(node_info)
        node_map[node["id"]] = node_info

    edges_svg = []
    for edge in graph["edges"]:
        source = node_map.get(edge["source"])
        target = node_map.get(edge["target"])
        if not source or not target:
            continue
        edges_svg.append(
            f'<line class="graph-edge" x1="{source["svg_x"]:.2f}" y1="{source["svg_y"]:.2f}" '
            f'x2="{target["svg_x"]:.2f}" y2="{target["svg_y"]:.2f}"></line>'
        )

    nodes_svg = []
    for node in nodes:
        nodes_svg.append(
            "<g>"
            f'<circle class="graph-node" cx="{node["svg_x"]:.2f}" cy="{node["svg_y"]:.2f}" r="15"></circle>'
            f'<text class="graph-node-label" x="{node["svg_x"]:.2f}" y="{node["svg_y"]:.2f}">{escape(str(node["id"]))}</text>'
            "</g>"
        )

    return (
        '<div class="panel">'
        f'<div class="panel-title">{escape(title)}</div>'
        f'<div class="panel-subtitle">{len(graph["edges"])} edges</div>'
        f'<svg class="graph-svg" viewBox="0 0 {width} {height}">'
        f'{"".join(edges_svg)}{"".join(nodes_svg)}'
        "</svg>"
        "</div>"
    )


def _badge_html(text, kind):
    return f'<span class="badge {kind}">{escape(text)}</span>'


def _render_flag_rows(entries):
    flagged = [entry for entry in entries if entry["flags"]]
    if not flagged:
        return '<tr><td colspan="8">No flagged cases in this run.</td></tr>'

    rows = []
    for entry in flagged:
        expected_badge = _badge_html(
            entry["expected_type"], "iso" if entry["expected_type"] == "isomorphic" else "non"
        )
        predicted_badge = _badge_html(
            entry["predicted_type"], "ok" if entry["predicted_type"] == "likely isomorphic" else "warn"
        )
        flags = " ".join(_badge_html(flag, "warn") for flag in entry["flags"])
        rows.append(
            "<tr>"
            f"<td>{entry['n']}</td>"
            f"<td>{expected_badge}</td>"
            f"<td>{predicted_badge}</td>"
            f"<td>{entry['I']:.6f}</td>"
            f"<td>{entry['mean_row_max']:.4f}</td>"
            f"<td>{entry['normalized_entropy']:.4f}</td>"
            f"<td>{flags}</td>"
            f"<td>{escape(entry['id'][:12])}...</td>"
            "</tr>"
        )
    return "".join(rows)


def _render_result_cards(entries):
    cards = []
    for entry in entries:
        flags_text = " · ".join(entry["flags"]) if entry["flags"] else "no major flags"
        card = (
            '<article class="result-card">'
            '<div class="result-header">'
            "<div>"
            f'<div class="result-title">n={entry["n"]} · {escape(entry["expected_type"])} · {escape(entry["predicted_type"])} · {escape(entry["cert_label"])}</div>'
            f'<div class="result-subtitle">{escape(entry["id"])}</div>'
            "</div>"
            '<div class="result-meta">'
            f'<span class="pill">I={entry["I"]:.6f}</span>'
            f'<span class="pill">Z*={entry["Z_star"]:.4e}</span>'
            f'<span class="pill">row max={entry["mean_row_max"]:.4f}</span>'
            f'<span class="pill">entropy={entry["normalized_entropy"]:.4f}</span>'
            f'<span class="pill{" warn" if entry["flags"] else ""}">{escape(flags_text)}</span>'
            "</div>"
            "</div>"
            '<div class="visual-grid">'
            f'{_render_graph_html(entry["graph_a"], "Graph A")}'
            '<div class="panel">'
            '<div class="panel-title">Permutation Matrix X*</div>'
            f'<div class="panel-subtitle">{len(entry["matrix"])} × {len(entry["matrix"])}</div>'
            f'{_render_matrix_html(entry["matrix"])}'
            "</div>"
            f'{_render_graph_html(entry["graph_b"], "Graph B")}'
            "</div>"
            '<div class="analysis-grid">'
            '<div class="analysis-card">'
            '<div class="analysis-label">Interpretation Gap</div>'
            f'<div class="analysis-value">{entry["score_gap"]:.4f}</div>'
            '<div class="analysis-copy">Distance from the I = 0.9 decision boundary.</div>'
            "</div>"
            '<div class="analysis-card">'
            '<div class="analysis-label">Best-vs-Second Margin</div>'
            f'<div class="analysis-value">{entry["mean_margin"]:.4f}</div>'
            '<div class="analysis-copy">Low margin means multiple candidate matches per row.</div>'
            "</div>"
            '<div class="analysis-card">'
            '<div class="analysis-label">Fractional Entries</div>'
            f'<div class="analysis-value">{entry["fractional_count"]}</div>'
            '<div class="analysis-copy">Non-binary values in X* indicate a soft assignment.</div>'
            "</div>"
            '<div class="analysis-card">'
            '<div class="analysis-label">Assessment</div>'
            f'<div class="analysis-value">{"Needs Review" if entry["flags"] else "Clean"}</div>'
            f'<div class="analysis-copy">{escape(entry["summary"])}</div>'
            "</div>"
            "</div>"
            "</article>"
        )
        cards.append(card)
    return "".join(cards)


def generate_comparison_report(base_dir="data/matrices", output_path="comparison_report.html"):
    entries = []
    for path in _sorted_matrix_paths(base_dir):
        data = json.loads(path.read_text())
        data["id"] = path.stem
        data["n"] = int(path.parent.name)
        entries.append(_entry_analysis(data))

    entries.sort(key=lambda entry: (len(entry["flags"]) == 0, entry["score_gap"], entry["n"], entry["id"]))
    summary = _summary(entries)

    html = HTML_TEMPLATE
    html = html.replace("{TOTAL_RESULTS}", str(summary["total"]))
    html = html.replace("{DISAGREEMENTS}", str(summary["disagreements"]))
    html = html.replace("{AMBIGUOUS_COUNT}", str(summary["ambiguous"]))
    html = html.replace("{AVG_ROW_MAX}", f"{summary['avg_row_max']:.4f}")
    html = html.replace("{AVG_ENTROPY}", f"{summary['avg_entropy']:.4f}")
    html = html.replace("{FLAG_ROWS}", _render_flag_rows(entries))
    html = html.replace("{RESULT_CARDS}", _render_result_cards(entries))

    Path(output_path).write_text(html, encoding="utf-8")
    print(f"  Comparison report saved → {output_path}")


if __name__ == "__main__":
    generate_comparison_report()
