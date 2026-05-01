#!/usr/bin/env python3
"""Run an isolated n=5..25 comparison benchmark for the current solver."""

from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

import numpy as np

from generators import DEFAULT_DENSITY_RANGE, make_isomorphic_pair, make_non_isomorphic_pair
from isomorphism import compute_isomorphism_index
from matrix_viewer import generate_viewer, scan_matrices
from report import generate_report


def _stats(values):
    if not values:
        return {"mean": None, "min": None, "max": None, "std": None}
    arr = np.asarray(values, dtype=float)
    return {
        "mean": float(np.mean(arr)),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "std": float(np.std(arr)),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run an isolated n=5..25 benchmark and generate report/viewer artifacts."
    )
    parser.add_argument("--n-min", type=int, default=5, help="Minimum n (default: 5)")
    parser.add_argument("--n-max", type=int, default=25, help="Maximum n (default: 25)")
    parser.add_argument("--pairs", type=int, default=5, help="Pairs per type per n (default: 5)")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed (default: 42)")
    parser.add_argument("--lambda-val", type=float, default=0.1, help="Index lambda (default: 0.1)")
    parser.add_argument(
        "--density-min",
        type=float,
        default=DEFAULT_DENSITY_RANGE[0],
        help=f"Minimum density (default: {DEFAULT_DENSITY_RANGE[0]})",
    )
    parser.add_argument(
        "--density-max",
        type=float,
        default=DEFAULT_DENSITY_RANGE[1],
        help=f"Maximum density (default: {DEFAULT_DENSITY_RANGE[1]})",
    )
    parser.add_argument(
        "--output-dir",
        default="compare_n5_25",
        help="Fresh output directory (default: compare_n5_25)",
    )
    parser.add_argument(
        "--show-graphs",
        action="store_true",
        help="Show graph panels in the generated matrix viewer",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    density_range = (args.density_min, args.density_max)
    if not (0.0 <= density_range[0] <= density_range[1] <= 1.0):
        raise ValueError(f"Invalid density range: {density_range}")

    out_dir = Path(args.output_dir)
    matrices_dir = out_dir / "matrices"
    report_path = out_dir / "isomorphism_report.html"
    summary_path = out_dir / "isomorphism_report.json"
    viewer_path = out_dir / "matrix_viewer.html"

    if out_dir.exists():
        shutil.rmtree(out_dir)
    matrices_dir.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(args.seed)
    results = []
    total_runs = (args.n_max - args.n_min + 1) * 2 * args.pairs
    run_idx = 0

    print("=" * 64)
    print("  ISOLATED CURRENT-SOLVER COMPARISON")
    print(f"  n          : {args.n_min}..{args.n_max}")
    print(f"  pairs      : {args.pairs} iso + {args.pairs} random per n")
    print(f"  density    : [{density_range[0]:.2f}, {density_range[1]:.2f}]")
    print(f"  output dir : {out_dir}")
    print("=" * 64)

    for n in range(args.n_min, args.n_max + 1):
        iso_times, random_times = [], []
        iso_scores, random_scores = [], []
        iso_z, random_z = [], []
        iso_cert, random_cert = [], []

        for pair_idx in range(args.pairs):
            run_idx += 1
            g1, g2 = make_isomorphic_pair(n, rng, density_range=density_range)
            start = time.perf_counter()
            z_star, i_score, certified = compute_isomorphism_index(
                g1,
                g2,
                lambda_val=args.lambda_val,
                base_dir=str(matrices_dir),
                comparison_type="isomorphic",
            )
            elapsed = time.perf_counter() - start
            if z_star is not None:
                iso_times.append(elapsed)
                iso_scores.append(i_score)
                iso_z.append(z_star)
                iso_cert.append(bool(certified))
            pct = 100 * run_idx / total_runs
            print(
                f"\r  Progress: {pct:5.1f}% | n={n:3d} | iso {pair_idx + 1}/{args.pairs}",
                end="",
                flush=True,
            )

        for pair_idx in range(args.pairs):
            run_idx += 1
            g1, g2 = make_non_isomorphic_pair(n, rng, density_range=density_range)
            start = time.perf_counter()
            z_star, i_score, certified = compute_isomorphism_index(
                g1,
                g2,
                lambda_val=args.lambda_val,
                base_dir=str(matrices_dir),
                comparison_type="random",
            )
            elapsed = time.perf_counter() - start
            if z_star is not None:
                random_times.append(elapsed)
                random_scores.append(i_score)
                random_z.append(z_star)
                random_cert.append(bool(certified))
            pct = 100 * run_idx / total_runs
            print(
                f"\r  Progress: {pct:5.1f}% | n={n:3d} | random {pair_idx + 1}/{args.pairs}",
                end="",
                flush=True,
            )

        results.append(
            {
                "n": n,
                "iso_time": _stats(iso_times),
                "non_iso_time": _stats(random_times),
                "iso_score": _stats(iso_scores),
                "non_iso_score": _stats(random_scores),
                "iso_z": _stats(iso_z),
                "non_iso_z": _stats(random_z),
                "iso_cert_correct": sum(iso_cert),
                "iso_cert_total": len(iso_cert),
                "non_iso_cert_correct": sum(1 for value in random_cert if not value),
                "non_iso_cert_total": len(random_cert),
            }
        )

    print()
    summary_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    generate_report(results, args.n_max, args.pairs, args.lambda_val, str(report_path))

    viewer_data = scan_matrices(str(matrices_dir))
    generate_viewer(viewer_data, str(viewer_path), show_graphs=args.show_graphs)

    print("=" * 64)
    print(f"  Summary JSON  : {summary_path}")
    print(f"  HTML report   : {report_path}")
    print(f"  Matrix viewer : {viewer_path}")
    print("=" * 64)


if __name__ == "__main__":
    main()
