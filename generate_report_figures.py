#!/usr/bin/env python3
"""Generate report figures that do not require external screenshots."""

from __future__ import annotations

import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

from generators import make_isomorphic_pair, make_non_isomorphic_pair
from isomorphism import (
    _adjacency_matrix_for_solver,
    _degree_cost_matrix,
    _normalize_cost_matrix,
)

try:
    import gurobipy as gp
    from gurobipy import GRB
except ImportError:  # pragma: no cover - figure generation can skip this plot.
    gp = None
    GRB = None


ROOT = Path(__file__).resolve().parent
FIGURES = ROOT / "figures"
REPORT_JSON = ROOT / "data" / "isomorphism_report.json"
MATRIX_DIR = ROOT / "data" / "matrices"
ABLATION_JSON = ROOT / "data" / "index_ablation.json"


plt.rcParams.update(
    {
        "figure.dpi": 150,
        "savefig.dpi": 240,
        "font.family": "DejaVu Sans",
        "axes.titlesize": 12,
        "axes.labelsize": 10,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
    }
)


def save(fig: plt.Figure, name: str) -> None:
    FIGURES.mkdir(exist_ok=True)
    path = FIGURES / name
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"wrote {path.relative_to(ROOT)}")


def arrow(ax, start, end, color="#385c8a") -> None:
    ax.annotate(
        "",
        xy=end,
        xytext=start,
        arrowprops=dict(arrowstyle="-|>", lw=1.8, color=color, shrinkA=8, shrinkB=8),
    )


def rounded_box(ax, xy, text, width=1.9, height=0.85, fc="#eef5ff", ec="#2b5c9a"):
    x, y = xy
    patch = plt.matplotlib.patches.FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle="round,pad=0.08,rounding_size=0.09",
        linewidth=1.3,
        edgecolor=ec,
        facecolor=fc,
    )
    ax.add_patch(patch)
    ax.text(x + width / 2, y + height / 2, text, ha="center", va="center", fontsize=9)


def make_pipeline() -> None:
    fig, ax = plt.subplots(figsize=(11.5, 2.4))
    ax.set_axis_off()
    boxes = [
        ((0.0, 0.72), "Graphs\n$G_A, G_B$"),
        ((2.15, 0.72), "Adjacency\n$A, B$"),
        ((4.3, 0.72), "QP over\n$\\mathcal{B}_n$"),
        ((6.45, 0.72), "Relaxed\n$X^*$"),
        ((8.6, 0.72), "Hyperplane\nrounding"),
        ((10.75, 0.72), "Certificate\n$A\\hat P=\\hat P B$"),
    ]
    for xy, label in boxes:
        rounded_box(ax, xy, label)
    for x in [1.9, 4.05, 6.2, 8.35, 10.5]:
        arrow(ax, (x, 1.145), (x + 0.28, 1.145))
    ax.text(
        5.3,
        0.22,
        "$\\min_{X \\in \\mathcal{B}_n} w_C\\langle C,X\\rangle + w_Q\\|AX-XB\\|_F^2$",
        ha="center",
        va="center",
        fontsize=11,
        color="#2b405f",
    )
    ax.set_xlim(-0.15, 12.9)
    ax.set_ylim(0, 2.1)
    save(fig, "pipeline.png")


def make_graph_perm_example() -> None:
    n = 9
    g_a = nx.random_geometric_graph(n, radius=0.52, seed=11)
    # Keep a deterministic, nontrivial relabeling so B is visibly the same
    # structure but not drawn as a copied toy graph.
    perm = [4, 7, 1, 8, 2, 6, 0, 5, 3]
    mapping = {i: perm[i] for i in range(n)}
    g_b = nx.relabel_nodes(g_a, mapping)

    nodes = list(range(n))
    a = nx.to_numpy_array(g_a, nodelist=nodes, dtype=int)
    b = nx.to_numpy_array(g_b, nodelist=nodes, dtype=int)
    p = np.zeros((n, n), dtype=int)
    for i, j in mapping.items():
        p[i, j] = 1

    fig = plt.figure(figsize=(12.5, 6.4))
    gs = fig.add_gridspec(2, 4, height_ratios=[1.35, 1], width_ratios=[1.1, 1.1, 1, 0.95])
    ax_g1 = fig.add_subplot(gs[0, 0])
    ax_g2 = fig.add_subplot(gs[0, 1])
    ax_map = fig.add_subplot(gs[0, 2:])
    pos_a = nx.get_node_attributes(g_a, "pos")
    pos_b = nx.spring_layout(g_b, seed=29)
    nx.draw_networkx(
        g_a,
        pos=pos_a,
        ax=ax_g1,
        node_size=520,
        node_color="#dbeafe",
        edge_color="#475569",
        linewidths=1.0,
        edgecolors="#1e3a8a",
        font_size=9,
    )
    nx.draw_networkx(
        g_b,
        pos=pos_b,
        ax=ax_g2,
        node_size=520,
        node_color="#dcfce7",
        edge_color="#475569",
        linewidths=1.0,
        edgecolors="#166534",
        font_size=9,
    )
    ax_g1.set_title("$G_A$")
    ax_g2.set_title("$G_B$ after hidden relabeling")
    ax_g1.axis("off")
    ax_g2.axis("off")
    ax_map.axis("off")
    ax_map.set_title("Permutation represented by $P$")
    left_x, right_x = 0.2, 0.78
    ys = np.linspace(0.88, 0.12, n)
    for i, y in enumerate(ys):
        ax_map.scatter(left_x, y, s=150, color="#dbeafe", edgecolor="#1e3a8a")
        ax_map.scatter(right_x, y, s=150, color="#dcfce7", edgecolor="#166534")
        ax_map.text(left_x, y, str(i), ha="center", va="center", fontsize=8)
        ax_map.text(right_x, y, str(i), ha="center", va="center", fontsize=8)
    for i, j in mapping.items():
        ax_map.plot([left_x + 0.03, right_x - 0.03], [ys[i], ys[j]], color="#64748b", alpha=0.55)
    ax_map.text(left_x, 0.98, "$G_A$ labels", ha="center", fontsize=9)
    ax_map.text(right_x, 0.98, "$G_B$ labels", ha="center", fontsize=9)
    ax_map.set_xlim(0, 1)
    ax_map.set_ylim(0, 1.05)

    for idx, (mat, title) in enumerate([(a, "$A$"), (p, "$P$"), (b, "$B$")]):
        ax = fig.add_subplot(gs[1, idx])
        ax.imshow(mat, cmap="Greys", vmin=0, vmax=1)
        ax.set_title(title)
        ax.set_xticks(range(n))
        ax.set_yticks(range(n))
        ax.tick_params(labelsize=6, length=0)
        ax.set_xticklabels(range(n), fontsize=6)
        ax.set_yticklabels(range(n), fontsize=6)
        ax.set_xticks(np.arange(-0.5, n, 1), minor=True)
        ax.set_yticks(np.arange(-0.5, n, 1), minor=True)
        ax.grid(which="minor", color="#e2e8f0", linewidth=0.5)

    ax_eq = fig.add_subplot(gs[1, 3])
    ax_eq.axis("off")
    ax_eq.text(
        0.5,
        0.62,
        "$AP = PB$",
        ha="center",
        va="center",
        fontsize=22,
        color="#166534",
    )
    ax_eq.text(
        0.5,
        0.35,
        "The permutation matrix\nis the certificate.",
        ha="center",
        va="center",
        fontsize=10,
    )
    fig.suptitle("Graph isomorphism as a permutation matrix equation", y=0.98)
    save(fig, "graph_perm_example.png")


def make_birkhoff_relaxation() -> None:
    n = 12
    rng = np.random.default_rng(7)
    perm = rng.permutation(n)
    p = np.zeros((n, n))
    p[np.arange(n), perm] = 1
    soft = rng.gamma(shape=1.4, scale=1.0, size=(n, n))
    x_soft = 0.42 * p + 0.58 * soft / soft.sum(axis=1, keepdims=True)
    for _ in range(18):
        x_soft = x_soft / x_soft.sum(axis=1, keepdims=True)
        x_soft = x_soft / x_soft.sum(axis=0, keepdims=True)

    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.1))
    for ax, mat, title in [
        (axes[0], p, "Vertex of $\\mathcal{B}_n$\n(permutation $P$)"),
        (axes[1], x_soft, "Interior of $\\mathcal{B}_n$\n(relaxed $X^*$)"),
    ]:
        im = ax.imshow(mat, cmap="YlGnBu", vmin=0, vmax=1)
        ax.set_title(title)
        ax.set_xlabel("vertex in $G_B$")
        ax.set_ylabel("vertex in $G_A$")
        ax.set_xticks(np.arange(-0.5, n, 1), minor=True)
        ax.set_yticks(np.arange(-0.5, n, 1), minor=True)
        ax.grid(which="minor", color="white", linewidth=0.8)
        ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
    fig.colorbar(im, ax=axes.ravel().tolist(), shrink=0.75, label="assignment weight")
    save(fig, "birkhoff_relaxation.png")


def make_rounding_diagram() -> None:
    rng = np.random.default_rng(2)
    centers = np.array([[-1.4, 0.8], [-0.2, -0.95], [1.2, 0.55], [0.65, 1.35], [-1.0, -0.35]])
    rows = centers + rng.normal(0, 0.08, centers.shape)
    cols = centers + rng.normal(0, 0.08, centers.shape)
    colors = ["#2563eb", "#16a34a", "#dc2626", "#9333ea", "#f59e0b"]

    fig, ax = plt.subplots(figsize=(7.2, 5.2))
    for i, (r, c) in enumerate(zip(rows, cols)):
        ax.scatter(*r, marker="o", s=100, color=colors[i], label="row embeddings" if i == 0 else None)
        ax.scatter(*c, marker="s", s=90, color=colors[i], edgecolor="black", linewidth=0.7, label="column embeddings" if i == 0 else None)
        ax.plot([r[0], c[0]], [r[1], c[1]], color=colors[i], alpha=0.35, linewidth=1)
        ax.text(r[0] + 0.05, r[1] + 0.05, f"$u_{i}$", fontsize=9)
        ax.text(c[0] + 0.05, c[1] - 0.12, f"$v_{i}$", fontsize=9)

    xs = np.linspace(-2.1, 2.0, 100)
    for slope, intercept in [(0.55, 0.0), (-0.9, 0.25), (2.8, -1.0)]:
        ax.plot(xs, slope * xs + intercept, "--", color="#334155", alpha=0.65)

    ax.set_title("Hyperplane rounding: match embeddings by sign signatures")
    ax.set_xlabel("SVD coordinate 1")
    ax.set_ylabel("SVD coordinate 2")
    ax.legend(loc="lower right", frameon=True)
    ax.set_xlim(-2.1, 2.0)
    ax.set_ylim(-1.45, 1.85)
    ax.grid(alpha=0.16)
    save(fig, "rounding_diagram.png")


def load_report_summary():
    if not REPORT_JSON.exists():
        return []
    data = json.loads(REPORT_JSON.read_text())
    return data if isinstance(data, list) else []


def mean_or_nan(row, key):
    value = row.get(key, {})
    if isinstance(value, dict):
        return value.get("mean", math.nan)
    return math.nan


def make_qp_plots() -> None:
    rows = load_report_summary()
    if not rows:
        print("skipping qp plots: data/isomorphism_report.json missing or empty")
        return
    rows = sorted(rows, key=lambda r: r["n"])
    n = np.array([r["n"] for r in rows])

    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.plot(n, [mean_or_nan(r, "iso_time") for r in rows], marker="o", label="isomorphic pairs")
    ax.plot(n, [mean_or_nan(r, "non_iso_time") for r in rows], marker="s", label="random pairs")
    ax.set_xlabel("nodes $n$")
    ax.set_ylabel("mean wall-clock time (s)")
    ax.set_title("QP solver runtime")
    ax.grid(alpha=0.2)
    ax.legend()
    save(fig, "qp_runtime.png")

    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.plot(n, [mean_or_nan(r, "iso_score") for r in rows], marker="o", label="isomorphic pairs")
    ax.plot(n, [mean_or_nan(r, "non_iso_score") for r in rows], marker="s", label="random pairs")
    ax.set_xlabel("nodes $n$")
    ax.set_ylabel("mean isomorphism index $I$")
    ax.set_ylim(0, 1.05)
    ax.set_title("Relaxed score separation")
    ax.grid(alpha=0.2)
    ax.legend()
    save(fig, "iso_index_separation.png")


def solve_relaxed_index(
    g_a: nx.Graph,
    g_b: nx.Graph,
    *,
    degree_scale: float,
    adjacency_scale: float = 1.0,
    lambda_val: float = 0.1,
) -> tuple[float, float]:
    """Solve only the relaxation objective for a small ablation figure."""
    if gp is None or GRB is None:
        raise RuntimeError("gurobipy is unavailable")

    a = _adjacency_matrix_for_solver(g_a)
    b = _adjacency_matrix_for_solver(g_b)
    n = a.shape[0]
    c = _degree_cost_matrix(a, b, degree_weight=1.0, neighbor_degree_weight=0.35)
    c = _normalize_cost_matrix(c)

    model = gp.Model("IndexAblation")
    model.setParam("OutputFlag", 0)
    model.setParam("TimeLimit", 45)

    x = model.addVars(n, n, lb=0.0, ub=1.0, vtype=GRB.CONTINUOUS, name="X")
    for i in range(n):
        model.addConstr(gp.quicksum(x[i, j] for j in range(n)) == 1)
    for j in range(n):
        model.addConstr(gp.quicksum(x[i, j] for i in range(n)) == 1)

    linear_part = degree_scale * gp.quicksum(c[i, j] * x[i, j] for i in range(n) for j in range(n))
    adjacency_part = 0
    for p in range(n):
        for q in range(n):
            diff_expr = gp.quicksum(a[p, k] * x[k, q] - x[p, k] * b[k, q] for k in range(n))
            adjacency_part += diff_expr * diff_expr
    model.setObjective(linear_part + adjacency_scale * adjacency_part, GRB.MINIMIZE)
    model.optimize()

    if model.status not in (GRB.OPTIMAL, GRB.TIME_LIMIT):
        raise RuntimeError(f"Gurobi status {model.status}")
    z_star = float(model.objVal)
    return z_star, float(np.exp(-lambda_val * z_star))


def run_index_ablation() -> list[dict[str, float | str | int]]:
    """Create or reuse data for the AX-XB-only vs full-objective figure."""
    if ABLATION_JSON.exists():
        data = json.loads(ABLATION_JSON.read_text())
        if isinstance(data, list) and data:
            return data

    rng = np.random.default_rng(20260502)
    rows: list[dict[str, float | str | int]] = []
    n_values = [6, 7, 8]
    pairs_per_n = 3
    density_range = (0.55, 0.85)

    for n in n_values:
        for pair_idx in range(pairs_per_n):
            for case_type, maker in [
                ("isomorphic", make_isomorphic_pair),
                ("random", make_non_isomorphic_pair),
            ]:
                g_a, g_b = maker(n, rng, density_range=density_range)
                for objective_name, degree_scale in [
                    ("AX-XB only", 0.0),
                    ("degree + AX-XB", 1.0),
                ]:
                    z_star, index = solve_relaxed_index(
                        g_a,
                        g_b,
                        degree_scale=degree_scale,
                    )
                    row = {
                        "n": n,
                        "pair": pair_idx,
                        "case_type": case_type,
                        "objective": objective_name,
                        "Z_star": z_star,
                        "I": index,
                    }
                    rows.append(row)
                    print(
                        "ablation",
                        f"n={n}",
                        f"pair={pair_idx}",
                        case_type,
                        objective_name,
                        f"I={index:.4f}",
                    )

    ABLATION_JSON.parent.mkdir(exist_ok=True)
    ABLATION_JSON.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return rows


def make_index_ablation() -> None:
    if gp is None:
        print("skipping index_ablation: gurobipy unavailable")
        return
    rows = run_index_ablation()
    objectives = ["AX-XB only", "degree + AX-XB"]
    cases = ["isomorphic", "random"]
    colors = {"isomorphic": "#166534", "random": "#b91c1c"}
    markers = {"isomorphic": "o", "random": "s"}

    fig, axes = plt.subplots(1, 2, figsize=(9.4, 4.2), sharey=True)
    for ax, objective in zip(axes, objectives):
        subset = [r for r in rows if r["objective"] == objective]
        for offset, case_type in [(-0.06, "isomorphic"), (0.06, "random")]:
            values = [float(r["I"]) for r in subset if r["case_type"] == case_type]
            xvals = np.full(len(values), 0.5 + offset)
            if values:
                ax.scatter(
                    xvals,
                    values,
                    color=colors[case_type],
                    marker=markers[case_type],
                    s=48,
                    alpha=0.78,
                    label=case_type,
                    edgecolor="white",
                    linewidth=0.5,
                )
                ax.hlines(
                    np.mean(values),
                    0.25,
                    0.75,
                    color=colors[case_type],
                    linewidth=2.2,
                    alpha=0.9,
                )
        ax.set_title(objective)
        ax.set_xlim(0.15, 0.85)
        ax.set_xticks([])
        ax.grid(axis="y", alpha=0.22)
        ax.set_xlabel("same generated pairs")
    axes[0].set_ylabel("Isomorphism index $I = e^{-0.1Z^*}$")
    axes[0].legend(loc="lower left", frameon=True)
    fig.suptitle("Degree-profile cost improves score separation in the relaxation")
    save(fig, "index_ablation.png")


def load_matrix_cases():
    cases = []
    for path in sorted(MATRIX_DIR.rglob("*.json")):
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue
        matrix = data.get("matrix")
        if not matrix:
            continue
        data["_path"] = path
        data["_case_type"] = data.get("case_type") or data.get("comparison_type") or "unspecified"
        cases.append(data)
    return cases


def adjacency_from_saved(graph):
    if not graph:
        return None
    adj = graph.get("adjacency")
    if adj is not None:
        return np.array(adj, dtype=float)
    nodes = [node["id"] for node in graph.get("nodes", [])]
    index = {node: i for i, node in enumerate(nodes)}
    a = np.zeros((len(nodes), len(nodes)))
    for edge in graph.get("edges", []):
        u, v = edge
        if u in index and v in index:
            a[index[u], index[v]] = 1
            a[index[v], index[u]] = 1
    return a


def degree_cost(a, b):
    da = a.sum(axis=1)
    db = b.sum(axis=1)
    sa = a @ da
    sb = b @ db
    c = np.abs(da[:, None] - db[None, :]) + 0.35 * np.abs(sa[:, None] - sb[None, :])
    m = np.max(np.abs(c))
    return c / m if m > 0 else c


def make_objective_heatmaps() -> None:
    cases = load_matrix_cases()
    case = next((c for c in cases if c.get("_case_type") == "random"), cases[0] if cases else None)
    if case is None:
        print("skipping objective heatmaps: no matrix JSON available")
        return
    x = np.array(case["matrix"], dtype=float)
    a = adjacency_from_saved(case.get("graph_a"))
    b = adjacency_from_saved(case.get("graph_b"))
    if a is None or b is None:
        print("skipping objective heatmaps: saved graphs missing")
        return
    c = degree_cost(a, b)
    residual = a @ x - x @ b
    p = np.array(case.get("permutation", np.zeros_like(x)), dtype=float)

    fig, axes = plt.subplots(1, 4, figsize=(12.5, 3.2))
    panels = [
        (c, "degree cost $C$", "magma", None),
        (x, "relaxed $X^*$", "viridis", (0, 1)),
        (p, "rounded $\\hat P$", "Blues", (0, 1)),
        (residual, "residual $AX^*-X^*B$", "coolwarm", None),
    ]
    for ax, (mat, title, cmap, limits) in zip(axes, panels):
        kwargs = {"cmap": cmap}
        if limits:
            kwargs.update(vmin=limits[0], vmax=limits[1])
        im = ax.imshow(mat, **kwargs)
        ax.set_title(title)
        ax.set_xticks([])
        ax.set_yticks([])
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.suptitle(f"Saved solver run: n={x.shape[0]}, case={case.get('_case_type')}, certified={case.get('is_isomorphic')}")
    save(fig, "objective_heatmaps.png")


def make_diffuse_vs_sharp() -> None:
    n = 12
    rng = np.random.default_rng(21)
    sharp = np.zeros((n, n))
    sharp[np.arange(n), rng.permutation(n)] = 1
    diffuse = np.ones((n, n)) / n
    uncertain = rng.uniform(0, 1, size=(n, n))
    uncertain = uncertain / uncertain.sum(axis=1, keepdims=True)
    for _ in range(14):
        uncertain = uncertain / uncertain.sum(axis=1, keepdims=True)
        uncertain = uncertain / uncertain.sum(axis=0, keepdims=True)
    soft = 0.35 * sharp + 0.65 * uncertain
    for _ in range(10):
        soft = soft / soft.sum(axis=1, keepdims=True)
        soft = soft / soft.sum(axis=0, keepdims=True)

    fig, axes = plt.subplots(1, 3, figsize=(10.6, 3.6))
    for ax, mat, title in [
        (axes[0], diffuse, "flat interior point"),
        (axes[1], soft, "ambiguous relaxed solution"),
        (axes[2], sharp, "sharp permutation"),
    ]:
        im = ax.imshow(mat, cmap="YlOrRd", vmin=0, vmax=1)
        ax.set_title(title)
        ax.set_xticks(np.arange(-0.5, n, 1), minor=True)
        ax.set_yticks(np.arange(-0.5, n, 1), minor=True)
        ax.grid(which="minor", color="white", linewidth=0.8)
        ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
    fig.colorbar(im, ax=axes.ravel().tolist(), shrink=0.75, label="assignment weight")
    save(fig, "diffuse_vs_sharp.png")


def main() -> None:
    make_pipeline()
    make_graph_perm_example()
    make_birkhoff_relaxation()
    make_rounding_diagram()
    make_qp_plots()
    make_index_ablation()
    make_objective_heatmaps()
    make_diffuse_vs_sharp()


if __name__ == "__main__":
    main()
