#!/usr/bin/env python3
"""Stress-test the current solver on generated isomorphic graph pairs.

Default run:
    python isomorphic_stress_test.py

This runs 300 generated isomorphic pairs for each n in {10, 11, 12}. Since all
generated pairs are isomorphic by construction, a run is counted correct only
if the solver certifies the rounded permutation with A P = P B.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

from generators import make_isomorphic_pair
from isomorphism import compute_isomorphism_index


def parse_sizes(raw: str) -> list[int]:
    sizes = [int(part.strip()) for part in raw.split(",") if part.strip()]
    if not sizes:
        raise argparse.ArgumentTypeError("at least one size is required")
    if any(n <= 0 for n in sizes):
        raise argparse.ArgumentTypeError("sizes must be positive")
    return sizes


def append_jsonl(path: Path, row: dict) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def summarize(results_path: Path, sizes: list[int], pairs_per_size: int) -> dict:
    rows = []
    if results_path.exists():
        with results_path.open(encoding="utf-8") as handle:
            rows = [json.loads(line) for line in handle if line.strip()]

    by_n = {}
    for n in sizes:
        current = [row for row in rows if int(row["n"]) == n]
        attempted = len(current)
        certified = sum(1 for row in current if row.get("certified") is True)
        failed = sum(1 for row in current if row.get("certified") is False)
        errors = sum(1 for row in current if row.get("error"))
        times = [float(row["elapsed_sec"]) for row in current if "elapsed_sec" in row]
        by_n[str(n)] = {
            "attempted": attempted,
            "target": pairs_per_size,
            "certified_correct": certified,
            "not_certified": failed,
            "errors": errors,
            "accuracy_on_attempted": certified / attempted if attempted else None,
            "mean_time_sec": float(np.mean(times)) if times else None,
            "max_time_sec": float(np.max(times)) if times else None,
        }

    total_attempted = sum(item["attempted"] for item in by_n.values())
    total_certified = sum(item["certified_correct"] for item in by_n.values())
    total_errors = sum(item["errors"] for item in by_n.values())
    return {
        "sizes": sizes,
        "pairs_per_size": pairs_per_size,
        "target_total": len(sizes) * pairs_per_size,
        "attempted_total": total_attempted,
        "certified_correct_total": total_certified,
        "not_certified_total": total_attempted - total_certified - total_errors,
        "errors_total": total_errors,
        "accuracy_on_attempted": total_certified / total_attempted if total_attempted else None,
        "by_n": by_n,
    }


def print_summary(summary: dict) -> None:
    print("\n" + "=" * 72)
    print("ISOMORPHIC STRESS TEST SUMMARY")
    print("=" * 72)
    print(f"Target total       : {summary['target_total']}")
    print(f"Attempted total    : {summary['attempted_total']}")
    print(f"Certified correct  : {summary['certified_correct_total']}")
    print(f"Not certified      : {summary['not_certified_total']}")
    print(f"Errors             : {summary['errors_total']}")
    acc = summary["accuracy_on_attempted"]
    print(f"Accuracy attempted : {acc:.4%}" if acc is not None else "Accuracy attempted : n/a")
    print("-" * 72)
    for n, row in summary["by_n"].items():
        acc_n = row["accuracy_on_attempted"]
        acc_text = f"{acc_n:.4%}" if acc_n is not None else "n/a"
        mean_time = row["mean_time_sec"]
        mean_text = f"{mean_time:.3f}s" if mean_time is not None else "n/a"
        print(
            f"n={int(n):>3} | attempted {row['attempted']:>4}/{row['target']:<4} | "
            f"certified {row['certified_correct']:>4} | "
            f"not certified {row['not_certified']:>4} | "
            f"errors {row['errors']:>3} | acc {acc_text:>9} | mean {mean_text}"
        )
    print("=" * 72)


def run(args: argparse.Namespace) -> int:
    output_dir = Path(args.output_dir)
    matrices_dir = output_dir / "matrices"
    results_path = output_dir / "results.jsonl"
    summary_path = output_dir / "summary.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    matrices_dir.mkdir(parents=True, exist_ok=True)
    results_path.unlink(missing_ok=True)
    summary_path.unlink(missing_ok=True)

    rng = np.random.default_rng(args.seed)
    total = len(args.sizes) * args.pairs

    print("=" * 72)
    print("ISOMORPHIC STRESS TEST")
    print(f"Sizes          : {args.sizes}")
    print(f"Pairs / size   : {args.pairs}")
    print(f"Target total   : {total}")
    print(f"Density        : [{args.density_min:.2f}, {args.density_max:.2f}]")
    print(f"Output dir     : {output_dir}")
    print("=" * 72)

    for n in args.sizes:
        for pair in range(args.pairs):
            started = time.perf_counter()
            row = {
                "n": n,
                "pair": pair,
                "seed": args.seed,
                "density_range": [args.density_min, args.density_max],
            }
            try:
                graph_a, graph_b = make_isomorphic_pair(
                    n,
                    rng,
                    density_range=(args.density_min, args.density_max),
                )
                z_star, i_score, certified = compute_isomorphism_index(
                    graph_a,
                    graph_b,
                    lambda_val=args.lambda_val,
                    base_dir=str(matrices_dir),
                    case_type="isomorphic_stress",
                )
                row.update(
                    {
                        "Z_star": None if z_star is None else float(z_star),
                        "I": None if i_score is None else float(i_score),
                        "certified": bool(certified),
                        "error": None,
                    }
                )
            except Exception as exc:  # Keep long runs alive and count failures.
                row.update(
                    {
                        "Z_star": None,
                        "I": None,
                        "certified": None,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )

            row["elapsed_sec"] = time.perf_counter() - started
            append_jsonl(results_path, row)

            attempted = summarize(results_path, args.sizes, args.pairs)["attempted_total"]
            status = "ok" if row.get("certified") is True else "miss"
            if row.get("error"):
                status = "error"
            print(
                f"[{attempted:>4}/{total}] n={n:>2} pair={pair:>3} "
                f"{status:<5} I={row.get('I')} t={row['elapsed_sec']:.3f}s",
                flush=True,
            )

    summary = summarize(results_path, args.sizes, args.pairs)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print_summary(summary)
    print(f"Wrote {results_path}")
    print(f"Wrote {summary_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the current solver on generated isomorphic pairs and count certificates."
    )
    parser.add_argument("--sizes", type=parse_sizes, default=[10, 11, 12], help="Comma-separated sizes")
    parser.add_argument("--pairs", type=int, default=300, help="Isomorphic pairs per size")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--density-min", type=float, default=0.80)
    parser.add_argument("--density-max", type=float, default=0.85)
    parser.add_argument("--lambda-val", type=float, default=0.1)
    parser.add_argument("--output-dir", default="isomorphic_stress_results")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.pairs <= 0:
        raise ValueError("--pairs must be positive")
    if not (0 <= args.density_min <= args.density_max <= 1):
        raise ValueError("density range must satisfy 0 <= min <= max <= 1")
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
