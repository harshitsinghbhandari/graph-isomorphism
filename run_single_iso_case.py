#!/usr/bin/env python3
"""Run one clearly isomorphic test case and generate a dedicated matrix viewer."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import networkx as nx
import numpy as np

from generators import DEFAULT_DENSITY_RANGE, make_isomorphic_pair
from isomorphism import compute_isomorphism_index
from matrix_viewer import generate_viewer, scan_matrices


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate one isomorphic graph pair, run the solver, and build a matrix viewer."
    )
    parser.add_argument("--n", type=int, default=101, help="Number of nodes (default: 101)")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed (default: 42)")
    parser.add_argument(
        "--density-min",
        type=float,
        default=DEFAULT_DENSITY_RANGE[0],
        help=f"Minimum graph density (default: {DEFAULT_DENSITY_RANGE[0]})",
    )
    parser.add_argument(
        "--density-max",
        type=float,
        default=DEFAULT_DENSITY_RANGE[1],
        help=f"Maximum graph density (default: {DEFAULT_DENSITY_RANGE[1]})",
    )
    parser.add_argument(
        "--output-dir",
        default="single_case_n101",
        help="Directory to store matrices, summary, and viewer (default: single_case_n101)",
    )
    parser.add_argument(
        "--show-graphs",
        action="store_true",
        help="Show Graph A and Graph B in the generated matrix viewer",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    density_range = (args.density_min, args.density_max)
    if not (0.0 <= density_range[0] <= density_range[1] <= 1.0):
        raise ValueError(f"Invalid density range: {density_range}")

    out_dir = Path(args.output_dir)
    matrices_dir = out_dir / "matrices"
    viewer_path = out_dir / "matrix_viewer.html"
    summary_path = out_dir / "run_summary.json"

    if out_dir.exists():
        shutil.rmtree(out_dir)
    matrices_dir.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(args.seed)
    g1, g2 = make_isomorphic_pair(args.n, rng, density_range=density_range)
    exact_iso = nx.is_isomorphic(g1, g2)
    if not exact_iso:
        raise RuntimeError("Generator returned a pair that is not isomorphic.")

    print("=" * 60)
    print("  SINGLE ISOMORPHIC TEST CASE")
    print(f"  n           : {args.n}")
    print(f"  seed        : {args.seed}")
    print(f"  density     : [{density_range[0]:.2f}, {density_range[1]:.2f}]")
    print(f"  output dir  : {out_dir}")
    print("=" * 60)

    z_star, i_score, certified_iso = compute_isomorphism_index(
        g1,
        g2,
        base_dir=str(matrices_dir),
        comparison_type="single_isomorphic_case",
    )

    if z_star is None:
        raise RuntimeError("Solver returned no solution.")

    viewer_data = scan_matrices(str(matrices_dir))
    if not viewer_data:
        raise RuntimeError("No matrix JSON was produced.")
    generate_viewer(viewer_data, str(viewer_path), show_graphs=args.show_graphs)

    summary = {
        "n": args.n,
        "seed": args.seed,
        "density_range": [float(density_range[0]), float(density_range[1])],
        "exact_isomorphic": bool(exact_iso),
        "solver_certified_isomorphic": bool(certified_iso),
        "Z_star": float(z_star),
        "I": float(i_score),
        "matrix_viewer": str(viewer_path),
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"  Exact isomorphic       : {exact_iso}")
    print(f"  Solver certified       : {certified_iso}")
    print(f"  Z*                     : {z_star:.6g}")
    print(f"  I                      : {i_score:.6g}")
    print(f"  Summary                : {summary_path}")
    print(f"  Matrix viewer          : {viewer_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
