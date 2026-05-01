"""big_benchmark.py - QP+hyperplane vs VF2 / nauty / bliss across n=5..100.

Sizes
-----
    n in {5..20}                         (16 sizes, every integer)
    n in {30, 40, 50, 60, 70, 80, 90, 100}   (8 sizes)
    => 24 sizes

Pairs per n
-----------
    5 isomorphic pairs (label: "iso")
    7 random pairs     (label: "random" - VF2 is treated as ground truth)
    => 12 pairs per n -> 288 pairs total

Algorithms run on each pair
---------------------------
    ours   : QP relaxation + Goemans-Williamson hyperplane rounding
    vf2    : networkx.is_isomorphic (VF2 algorithm)
    nauty  : pynauty.isomorphic (canonical labelling)
    bliss  : igraph.Graph.isomorphic_bliss

=> 288 * 4 = 1152 individual runs.

Disk layout (everything saved, nothing reused)
----------------------------------------------
    benchmark_data/
        graphs.json                      every (G_a, G_b) pair as edge lists
        runs/<n>_<idx>_<kind>_<algo>.json one file per algorithm-pair run
        matrices/<n>/<uuid>.json          QP X*, P, etc. (from compute_isomorphism_index)
        summary.json                     aggregated metrics
        plots/*.png                      figures

Resume semantics
----------------
- If graphs.json exists, the same pairs are reused (deterministic).
- If a runs/<...>.json already exists, that run is skipped on re-execution.
- `python big_benchmark.py --plots-only` regenerates every plot from the
  existing run files without re-running anything.

Common flags
------------
    --algos ours,vf2,nauty,bliss     subset of algorithms (default: all)
    --sizes 5,6,...,100              override the size schedule
    --max-n 50                       cap the largest n (use to skip n=60..100)
    --plots-only                     skip benchmarking, just rebuild plots
    --regenerate-graphs              wipe graphs.json and resample pairs
    --seed 42                        RNG seed for reproducible pairs
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Any

import numpy as np
import networkx as nx

# --- Optional deps; missing libs degrade to a recorded "missing" error. ----
try:
    import pynauty  # type: ignore

    HAVE_NAUTY = True
except Exception:  # pragma: no cover - import-time only
    HAVE_NAUTY = False

try:
    import igraph as ig  # type: ignore

    HAVE_BLISS = True
except Exception:  # pragma: no cover
    HAVE_BLISS = False

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt  # type: ignore

    HAVE_MPL = True
except Exception:  # pragma: no cover
    HAVE_MPL = False

from isomorphism import compute_isomorphism_index
from generators import make_isomorphic_pair, make_non_isomorphic_pair


# --------------------------------------------------------------------------- #
# Constants                                                                   #
# --------------------------------------------------------------------------- #

SIZES_DEFAULT: list[int] = list(range(5, 21)) + list(range(30, 101, 10))
ISO_PAIRS_PER_N = 5
RAND_PAIRS_PER_N = 7
ALL_ALGOS = ["ours", "vf2", "nauty", "bliss"]

OUT_DIR = Path("benchmark_data")
GRAPHS_PATH = OUT_DIR / "graphs.json"
RUNS_DIR = OUT_DIR / "runs"
MATRICES_DIR = OUT_DIR / "matrices"
SUMMARY_PATH = OUT_DIR / "summary.json"
PLOTS_DIR = OUT_DIR / "plots"


# --------------------------------------------------------------------------- #
# Graph generation                                                            #
# --------------------------------------------------------------------------- #

def _edge_list(G: nx.Graph) -> list[list[int]]:
    return [[int(u), int(v)] for u, v in G.edges()]


def _graph_from_edges(edges: list[list[int]], n: int) -> nx.Graph:
    G = nx.Graph()
    G.add_nodes_from(range(n))
    G.add_edges_from((int(u), int(v)) for u, v in edges)
    return G


def _relabel_to_zero_based(G: nx.Graph) -> nx.Graph:
    nodes = sorted(G.nodes())
    mapping = {old: new for new, old in enumerate(nodes)}
    return nx.relabel_nodes(G, mapping)


def generate_all_pairs(sizes: list[int], seed: int) -> list[dict[str, Any]]:
    rng = np.random.default_rng(seed)
    pairs: list[dict[str, Any]] = []
    for n in sizes:
        for k in range(ISO_PAIRS_PER_N):
            G1, G2 = make_isomorphic_pair(n, rng)
            G1 = _relabel_to_zero_based(G1)
            G2 = _relabel_to_zero_based(G2)
            pairs.append(
                {
                    "n": int(n),
                    "pair_idx": int(k),
                    "kind": "iso",
                    "edges_a": _edge_list(G1),
                    "edges_b": _edge_list(G2),
                }
            )
        for k in range(RAND_PAIRS_PER_N):
            G1, G2 = make_non_isomorphic_pair(n, rng)
            G1 = _relabel_to_zero_based(G1)
            G2 = _relabel_to_zero_based(G2)
            pairs.append(
                {
                    "n": int(n),
                    "pair_idx": int(k),
                    "kind": "random",
                    "edges_a": _edge_list(G1),
                    "edges_b": _edge_list(G2),
                }
            )
    return pairs


def load_or_generate_pairs(
    sizes: list[int], seed: int, regenerate: bool
) -> list[dict[str, Any]]:
    if GRAPHS_PATH.exists() and not regenerate:
        with open(GRAPHS_PATH) as f:
            pairs = json.load(f)
        existing_sizes = sorted({p["n"] for p in pairs})
        if existing_sizes == sorted(sizes):
            print(f"  Reusing {len(pairs)} pairs from {GRAPHS_PATH}")
            return pairs
        print(
            f"  Existing graphs.json covers sizes {existing_sizes}, "
            f"requested {sorted(sizes)}. Regenerating."
        )
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pairs = generate_all_pairs(sizes, seed)
    with open(GRAPHS_PATH, "w") as f:
        json.dump(pairs, f)
    print(f"  Wrote {len(pairs)} pairs to {GRAPHS_PATH}")
    return pairs


# --------------------------------------------------------------------------- #
# Algorithm wrappers - each returns a JSON-serialisable dict                   #
# --------------------------------------------------------------------------- #

def run_ours(G1: nx.Graph, G2: nx.Graph, n: int) -> dict[str, Any]:
    matrices_dir = str(MATRICES_DIR)
    t0 = time.perf_counter()
    try:
        Z, I, is_iso = compute_isomorphism_index(G1, G2, base_dir=matrices_dir)
        elapsed = time.perf_counter() - t0
        if Z is None:
            return {
                "algorithm": "ours",
                "decision": None,
                "time_s": elapsed,
                "error": "solver returned no solution",
            }
        return {
            "algorithm": "ours",
            "decision": bool(is_iso),
            "time_s": elapsed,
            "Z_star": float(Z),
            "I": float(I),
        }
    except Exception as exc:
        return {
            "algorithm": "ours",
            "decision": None,
            "time_s": time.perf_counter() - t0,
            "error": f"{type(exc).__name__}: {exc}",
            "traceback": traceback.format_exc(),
        }


def run_vf2(G1: nx.Graph, G2: nx.Graph, n: int) -> dict[str, Any]:
    t0 = time.perf_counter()
    try:
        is_iso = nx.is_isomorphic(G1, G2)
        return {
            "algorithm": "vf2",
            "decision": bool(is_iso),
            "time_s": time.perf_counter() - t0,
        }
    except Exception as exc:
        return {
            "algorithm": "vf2",
            "decision": None,
            "time_s": time.perf_counter() - t0,
            "error": f"{type(exc).__name__}: {exc}",
        }


def run_nauty(G1: nx.Graph, G2: nx.Graph, n: int) -> dict[str, Any]:
    if not HAVE_NAUTY:
        return {
            "algorithm": "nauty",
            "decision": None,
            "time_s": None,
            "error": "pynauty not installed",
        }
    t0 = time.perf_counter()
    try:
        g1 = pynauty.Graph(n)
        g1.set_adjacency_dict({i: list(G1.neighbors(i)) for i in range(n)})
        g2 = pynauty.Graph(n)
        g2.set_adjacency_dict({i: list(G2.neighbors(i)) for i in range(n)})
        is_iso = pynauty.isomorphic(g1, g2)
        return {
            "algorithm": "nauty",
            "decision": bool(is_iso),
            "time_s": time.perf_counter() - t0,
        }
    except Exception as exc:
        return {
            "algorithm": "nauty",
            "decision": None,
            "time_s": time.perf_counter() - t0,
            "error": f"{type(exc).__name__}: {exc}",
        }


def run_bliss(G1: nx.Graph, G2: nx.Graph, n: int) -> dict[str, Any]:
    if not HAVE_BLISS:
        return {
            "algorithm": "bliss",
            "decision": None,
            "time_s": None,
            "error": "igraph not installed",
        }
    t0 = time.perf_counter()
    try:
        g1 = ig.Graph(n=n, edges=list(G1.edges()))
        g2 = ig.Graph(n=n, edges=list(G2.edges()))
        is_iso = g1.isomorphic_bliss(g2)
        return {
            "algorithm": "bliss",
            "decision": bool(is_iso),
            "time_s": time.perf_counter() - t0,
        }
    except Exception as exc:
        return {
            "algorithm": "bliss",
            "decision": None,
            "time_s": time.perf_counter() - t0,
            "error": f"{type(exc).__name__}: {exc}",
        }


ALGO_FNS = {
    "ours": run_ours,
    "vf2": run_vf2,
    "nauty": run_nauty,
    "bliss": run_bliss,
}


# --------------------------------------------------------------------------- #
# Main run loop with resume                                                   #
# --------------------------------------------------------------------------- #

def _run_filename(n: int, pair_idx: int, kind: str, algo: str) -> Path:
    return RUNS_DIR / f"n{n:03d}_pair{pair_idx:02d}_{kind}_alg-{algo}.json"


def execute_benchmark(pairs: list[dict[str, Any]], algos: list[str]) -> None:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    MATRICES_DIR.mkdir(parents=True, exist_ok=True)

    todo: list[tuple[dict[str, Any], str]] = []
    for pair in pairs:
        for algo in algos:
            path = _run_filename(pair["n"], pair["pair_idx"], pair["kind"], algo)
            if not path.exists():
                todo.append((pair, algo))

    total_runs = len(pairs) * len(algos)
    completed = total_runs - len(todo)
    print(
        f"  {completed}/{total_runs} runs already on disk; "
        f"executing the remaining {len(todo)}."
    )

    for idx, (pair, algo) in enumerate(todo, 1):
        n = pair["n"]
        kind = pair["kind"]
        pair_idx = pair["pair_idx"]
        path = _run_filename(n, pair_idx, kind, algo)
        G1 = _graph_from_edges(pair["edges_a"], n)
        G2 = _graph_from_edges(pair["edges_b"], n)

        t_start = time.perf_counter()
        result = ALGO_FNS[algo](G1, G2, n)
        wall = time.perf_counter() - t_start

        result.update(
            {
                "n": n,
                "pair_idx": pair_idx,
                "kind": kind,
                "wall_time_s": wall,
            }
        )
        with open(path, "w") as f:
            json.dump(result, f, indent=2)

        marker = "iso" if result.get("decision") else (
            "no" if result.get("decision") is False else "ERR"
        )
        print(
            f"  [{idx:4d}/{len(todo)}]  n={n:3d} pair={pair_idx} {kind:6s} "
            f"{algo:6s}  decision={marker:3s}  t={result.get('time_s', 0):.3f}s"
        )


# --------------------------------------------------------------------------- #
# Aggregation + plotting                                                      #
# --------------------------------------------------------------------------- #

def load_all_runs() -> list[dict[str, Any]]:
    runs = []
    for path in sorted(RUNS_DIR.glob("*.json")):
        with open(path) as f:
            runs.append(json.load(f))
    return runs


def build_summary(runs: list[dict[str, Any]]) -> dict[str, Any]:
    by_pair: dict[tuple[int, int, str], dict[str, dict[str, Any]]] = {}
    for r in runs:
        key = (r["n"], r["pair_idx"], r["kind"])
        by_pair.setdefault(key, {})[r["algorithm"]] = r

    sizes = sorted({k[0] for k in by_pair})
    algos = sorted({a for d in by_pair.values() for a in d})

    # Per-(n, kind, algorithm) aggregates: mean time, median time, decision counts.
    per_n_kind_algo: dict[str, dict[str, dict[str, dict[str, Any]]]] = {}
    for n in sizes:
        per_n_kind_algo[str(n)] = {}
        for kind in ("iso", "random"):
            per_n_kind_algo[str(n)][kind] = {}
            for algo in algos:
                rs = [
                    by_pair[(n, idx, kind)][algo]
                    for (nn, idx, kk) in by_pair
                    if nn == n and kk == kind and algo in by_pair[(nn, idx, kk)]
                ]
                times = [r["time_s"] for r in rs if r.get("time_s") is not None]
                yes = sum(1 for r in rs if r.get("decision") is True)
                no = sum(1 for r in rs if r.get("decision") is False)
                err = sum(
                    1
                    for r in rs
                    if r.get("decision") is None or r.get("error") is not None
                )
                per_n_kind_algo[str(n)][kind][algo] = {
                    "count": len(rs),
                    "yes": yes,
                    "no": no,
                    "err": err,
                    "mean_time_s": float(np.mean(times)) if times else None,
                    "median_time_s": float(np.median(times)) if times else None,
                    "max_time_s": float(np.max(times)) if times else None,
                }

    # Pairwise agreement using VF2 as ground truth.
    agreement: dict[str, dict[str, int]] = {a: {"agree": 0, "disagree": 0, "n_decided": 0} for a in algos}
    if "vf2" in algos:
        for key, by_algo in by_pair.items():
            vf2_dec = by_algo.get("vf2", {}).get("decision")
            if vf2_dec is None:
                continue
            for algo in algos:
                dec = by_algo.get(algo, {}).get("decision")
                if dec is None:
                    continue
                agreement[algo]["n_decided"] += 1
                if dec == vf2_dec:
                    agreement[algo]["agree"] += 1
                else:
                    agreement[algo]["disagree"] += 1

    # Confusion (algo x algo): number of pairs where they agree.
    confusion: dict[str, dict[str, int]] = {a: {b: 0 for b in algos} for a in algos}
    for by_algo in by_pair.values():
        for a in algos:
            for b in algos:
                da = by_algo.get(a, {}).get("decision")
                db = by_algo.get(b, {}).get("decision")
                if da is not None and db is not None and da == db:
                    confusion[a][b] += 1

    return {
        "sizes": sizes,
        "algorithms": algos,
        "per_n_kind_algo": per_n_kind_algo,
        "agreement_vs_vf2": agreement,
        "confusion": confusion,
        "total_runs": len(runs),
        "total_pairs": len(by_pair),
    }


# --------------------------------------------------------------------------- #
# Plots                                                                       #
# --------------------------------------------------------------------------- #

PLOT_COLORS = {
    "ours": "#1f77b4",
    "vf2": "#2ca02c",
    "nauty": "#d62728",
    "bliss": "#9467bd",
}


def _ensure_plots_dir() -> None:
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)


def _save(fig, name: str) -> None:
    out = PLOTS_DIR / name
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  Wrote {out}")


def plot_time_vs_n(summary: dict[str, Any]) -> None:
    sizes = summary["sizes"]
    algos = summary["algorithms"]
    fig, ax = plt.subplots(figsize=(9, 5))
    for algo in algos:
        ys = []
        for n in sizes:
            stats = summary["per_n_kind_algo"][str(n)]
            iso = stats["iso"].get(algo, {})
            rand = stats["random"].get(algo, {})
            times = []
            if iso.get("mean_time_s") is not None:
                times.append(iso["mean_time_s"])
            if rand.get("mean_time_s") is not None:
                times.append(rand["mean_time_s"])
            ys.append(float(np.mean(times)) if times else np.nan)
        ax.plot(sizes, ys, marker="o", label=algo, color=PLOT_COLORS.get(algo))
    ax.set_xlabel("n (number of nodes)")
    ax.set_ylabel("mean wall time per pair (s)")
    ax.set_yscale("log")
    ax.set_title("Time per pair vs n  (mean over 12 pairs/n; log y)")
    ax.grid(True, which="both", linestyle=":", alpha=0.5)
    ax.legend()
    _save(fig, "time_vs_n.png")


def plot_certificate_rate_iso(summary: dict[str, Any]) -> None:
    sizes = summary["sizes"]
    algos = summary["algorithms"]
    fig, ax = plt.subplots(figsize=(9, 5))
    for algo in algos:
        ys = []
        for n in sizes:
            iso = summary["per_n_kind_algo"][str(n)]["iso"].get(algo, {})
            count = iso.get("count", 0)
            yes = iso.get("yes", 0)
            ys.append(yes / count if count else np.nan)
        ax.plot(sizes, ys, marker="o", label=algo, color=PLOT_COLORS.get(algo))
    ax.set_xlabel("n")
    ax.set_ylabel("certificate rate on iso pairs")
    ax.set_ylim(-0.02, 1.05)
    ax.set_title("Iso-pair certificate rate vs n  (5 pairs/n)")
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.legend()
    _save(fig, "certificate_rate_iso.png")


def plot_iso_rate_random(summary: dict[str, Any]) -> None:
    """Fraction of *random* pairs each algorithm calls isomorphic.
    Treat VF2 as ground truth; the gap between curves and VF2 is the FP rate."""
    sizes = summary["sizes"]
    algos = summary["algorithms"]
    fig, ax = plt.subplots(figsize=(9, 5))
    for algo in algos:
        ys = []
        for n in sizes:
            rnd = summary["per_n_kind_algo"][str(n)]["random"].get(algo, {})
            count = rnd.get("count", 0)
            yes = rnd.get("yes", 0)
            ys.append(yes / count if count else np.nan)
        ax.plot(sizes, ys, marker="o", label=algo, color=PLOT_COLORS.get(algo))
    ax.set_xlabel("n")
    ax.set_ylabel("fraction called isomorphic on random pairs")
    ax.set_ylim(-0.02, 1.05)
    ax.set_title("Iso-rate on random pairs vs n  (7 pairs/n; gap to VF2 ~ FP)")
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.legend()
    _save(fig, "iso_rate_random.png")


def plot_agreement(summary: dict[str, Any]) -> None:
    agree = summary["agreement_vs_vf2"]
    algos = list(agree.keys())
    fractions = []
    for algo in algos:
        a = agree[algo]
        denom = a["n_decided"] or 1
        fractions.append(a["agree"] / denom)
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(algos, fractions, color=[PLOT_COLORS.get(a, "#888") for a in algos])
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("agreement with VF2")
    ax.set_title("Per-algorithm agreement with VF2 (ground truth)")
    for i, frac in enumerate(fractions):
        ax.text(i, frac + 0.02, f"{frac:.3f}", ha="center")
    _save(fig, "agreement_vs_vf2.png")


def plot_confusion(summary: dict[str, Any]) -> None:
    algos = summary["algorithms"]
    M = np.array(
        [[summary["confusion"][a][b] for b in algos] for a in algos], dtype=float
    )
    total = summary["total_pairs"] or 1
    M = M / total
    fig, ax = plt.subplots(figsize=(5.5, 5))
    im = ax.imshow(M, cmap="Blues", vmin=0, vmax=1)
    ax.set_xticks(range(len(algos)))
    ax.set_yticks(range(len(algos)))
    ax.set_xticklabels(algos)
    ax.set_yticklabels(algos)
    for i in range(len(algos)):
        for j in range(len(algos)):
            ax.text(j, i, f"{M[i, j]:.2f}", ha="center", va="center",
                    color="white" if M[i, j] > 0.5 else "black")
    ax.set_title("Pairwise agreement (fraction of all pairs)")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    _save(fig, "confusion.png")


def plot_z_star_distribution(runs: list[dict[str, Any]]) -> None:
    iso_z = [r["Z_star"] for r in runs if r.get("algorithm") == "ours"
             and r.get("kind") == "iso" and r.get("Z_star") is not None]
    rnd_z = [r["Z_star"] for r in runs if r.get("algorithm") == "ours"
             and r.get("kind") == "random" and r.get("Z_star") is not None]
    if not iso_z and not rnd_z:
        print("  (no Z* data; skipping z_star_distribution plot)")
        return
    fig, ax = plt.subplots(figsize=(8, 5))
    if iso_z:
        ax.hist(iso_z, bins=30, alpha=0.6, label=f"iso (n={len(iso_z)})", color="#1f77b4")
    if rnd_z:
        ax.hist(rnd_z, bins=30, alpha=0.6, label=f"random (n={len(rnd_z)})", color="#ff7f0e")
    ax.set_xlabel("Z*  (objective value of the QP)")
    ax.set_ylabel("count")
    ax.set_title("Z* distribution: iso vs random pairs (our QP)")
    ax.legend()
    ax.grid(True, linestyle=":", alpha=0.5)
    _save(fig, "z_star_distribution.png")


def plot_z_star_vs_n(runs: list[dict[str, Any]]) -> None:
    """Scatter of Z* vs n, separated by pair kind."""
    iso_xy = [(r["n"], r["Z_star"]) for r in runs if r.get("algorithm") == "ours"
              and r.get("kind") == "iso" and r.get("Z_star") is not None]
    rnd_xy = [(r["n"], r["Z_star"]) for r in runs if r.get("algorithm") == "ours"
              and r.get("kind") == "random" and r.get("Z_star") is not None]
    if not iso_xy and not rnd_xy:
        return
    fig, ax = plt.subplots(figsize=(9, 5))
    if iso_xy:
        xs, ys = zip(*iso_xy)
        ax.scatter(xs, ys, label="iso", color="#1f77b4", alpha=0.7, s=30)
    if rnd_xy:
        xs, ys = zip(*rnd_xy)
        ax.scatter(xs, ys, label="random", color="#ff7f0e", alpha=0.7, s=30, marker="x")
    ax.set_xlabel("n")
    ax.set_ylabel("Z*")
    ax.set_yscale("symlog", linthresh=1e-3)
    ax.set_title("Z* vs n (every individual pair)")
    ax.legend()
    ax.grid(True, which="both", linestyle=":", alpha=0.5)
    _save(fig, "z_star_vs_n.png")


def plot_total_time_per_algo(summary: dict[str, Any]) -> None:
    algos = summary["algorithms"]
    totals = []
    for algo in algos:
        t = 0.0
        for n in summary["sizes"]:
            for kind in ("iso", "random"):
                stats = summary["per_n_kind_algo"][str(n)][kind].get(algo, {})
                mean_t = stats.get("mean_time_s")
                cnt = stats.get("count", 0) or 0
                if mean_t is not None:
                    t += mean_t * cnt
        totals.append(t)
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(algos, totals, color=[PLOT_COLORS.get(a, "#888") for a in algos])
    ax.set_ylabel("cumulative time across all pairs (s)")
    ax.set_yscale("log")
    ax.set_title("Total time per algorithm")
    for i, val in enumerate(totals):
        ax.text(i, val * 1.05, f"{val:.1f}s", ha="center")
    _save(fig, "total_time_per_algo.png")


def make_all_plots(summary: dict[str, Any], runs: list[dict[str, Any]]) -> None:
    if not HAVE_MPL:
        print("  matplotlib not available; skipping plots")
        return
    _ensure_plots_dir()
    plot_time_vs_n(summary)
    plot_certificate_rate_iso(summary)
    plot_iso_rate_random(summary)
    plot_agreement(summary)
    plot_confusion(summary)
    plot_total_time_per_algo(summary)
    plot_z_star_distribution(runs)
    plot_z_star_vs_n(runs)


# --------------------------------------------------------------------------- #
# Entry point                                                                 #
# --------------------------------------------------------------------------- #

def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    p.add_argument("--algos", default=",".join(ALL_ALGOS),
                   help="comma-separated list of algorithms to run")
    p.add_argument("--sizes", default=None,
                   help="comma-separated explicit size schedule (overrides default)")
    p.add_argument("--max-n", type=int, default=None,
                   help="cap the largest n (after default schedule)")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--plots-only", action="store_true",
                   help="skip benchmarking, regenerate plots from existing runs")
    p.add_argument("--regenerate-graphs", action="store_true",
                   help="wipe graphs.json and resample pairs")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv if argv is not None else sys.argv[1:])

    if args.sizes:
        sizes = [int(s) for s in args.sizes.split(",") if s.strip()]
    else:
        sizes = list(SIZES_DEFAULT)
    if args.max_n is not None:
        sizes = [s for s in sizes if s <= args.max_n]

    algos = [a.strip() for a in args.algos.split(",") if a.strip()]
    for a in algos:
        if a not in ALGO_FNS:
            print(f"unknown algorithm: {a}", file=sys.stderr)
            sys.exit(2)

    print("=" * 64)
    print("  BIG BENCHMARK")
    print(f"  Sizes      : {sizes}")
    print(f"  Algorithms : {algos}")
    print(f"  Pairs/n    : {ISO_PAIRS_PER_N} iso + {RAND_PAIRS_PER_N} random = "
          f"{ISO_PAIRS_PER_N + RAND_PAIRS_PER_N}")
    print(f"  Total runs : {len(sizes) * (ISO_PAIRS_PER_N + RAND_PAIRS_PER_N) * len(algos)}")
    print(f"  Output     : {OUT_DIR}/")
    print(f"  pynauty    : {'yes' if HAVE_NAUTY else 'NO'}")
    print(f"  bliss(igr) : {'yes' if HAVE_BLISS else 'NO'}")
    print(f"  matplotlib : {'yes' if HAVE_MPL else 'NO'}")
    print("=" * 64)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pairs = load_or_generate_pairs(sizes, args.seed, args.regenerate_graphs)

    if not args.plots_only:
        execute_benchmark(pairs, algos)

    print("\n  Aggregating results...")
    runs = load_all_runs()
    summary = build_summary(runs)
    with open(SUMMARY_PATH, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"  Wrote {SUMMARY_PATH}")

    print("\n  Generating plots...")
    make_all_plots(summary, runs)

    print("\n  DONE.")
    print(f"  Open {PLOTS_DIR}/ for figures or {SUMMARY_PATH} for the JSON summary.")


if __name__ == "__main__":
    main()
