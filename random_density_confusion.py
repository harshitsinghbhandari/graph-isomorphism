#!/usr/bin/env python3
"""Overnight random-density VF2-vs-ours confusion-matrix experiment.

Default workload:
    n = 5, 10, 15, ..., 40
    250 random graph pairs per n
    density sampled independently per graph from [0.2, 0.8]

Labels:
    VF2 iso      := networkx.is_isomorphic(G_A, G_B)
    Ours iso     := rounded permutation certifies A P = P B

Confusion matrix is therefore:
    rows    = VF2 reference label
    columns = our certificate label
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import networkx as nx
import numpy as np

from isomorphism import compute_isomorphism_index


DEFAULT_SIZES = list(range(5, 41, 5))


def parse_sizes(raw: str) -> list[int]:
    sizes = [int(part.strip()) for part in raw.split(",") if part.strip()]
    if not sizes:
        raise argparse.ArgumentTypeError("at least one size is required")
    if any(n <= 0 for n in sizes):
        raise argparse.ArgumentTypeError("sizes must be positive")
    return sizes


def edge_count(n: int, density: float) -> int:
    max_edges = n * (n - 1) // 2
    return int(round(density * max_edges))


def random_graph(n: int, rng: np.random.Generator, density_min: float, density_max: float) -> tuple[nx.Graph, float]:
    density = float(rng.uniform(density_min, density_max))
    m = edge_count(n, density)
    graph = nx.gnm_random_graph(n, m, seed=int(rng.integers(1_000_000_000)))
    return graph, density


def append_jsonl(path: Path, row: dict) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def read_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def confusion_for(rows: list[dict]) -> dict:
    tp = sum(1 for row in rows if row.get("vf2_isomorphic") is True and row.get("ours_certified_iso") is True)
    tn = sum(1 for row in rows if row.get("vf2_isomorphic") is False and row.get("ours_certified_iso") is False)
    fp = sum(1 for row in rows if row.get("vf2_isomorphic") is False and row.get("ours_certified_iso") is True)
    fn = sum(1 for row in rows if row.get("vf2_isomorphic") is True and row.get("ours_certified_iso") is False)
    errors = sum(1 for row in rows if row.get("error"))
    attempted = len(rows)
    valid = attempted - errors
    return {
        "attempted": attempted,
        "valid": valid,
        "true_positive_vf2_iso_ours_iso": tp,
        "true_negative_vf2_non_iso_ours_non_iso": tn,
        "false_positive_vf2_non_iso_ours_iso": fp,
        "false_negative_vf2_iso_ours_non_iso": fn,
        "errors": errors,
        "accuracy": (tp + tn) / valid if valid else None,
        "precision_iso": tp / (tp + fp) if (tp + fp) else None,
        "recall_iso": tp / (tp + fn) if (tp + fn) else None,
        "specificity_non_iso": tn / (tn + fp) if (tn + fp) else None,
    }


def summarize(results_path: Path, sizes: list[int], pairs: int) -> dict:
    rows = read_rows(results_path)
    by_n = {}
    for n in sizes:
        current = [row for row in rows if int(row["n"]) == n]
        matrix = confusion_for(current)
        times = [float(row["elapsed_sec"]) for row in current if "elapsed_sec" in row]
        densities_a = [float(row["density_a"]) for row in current if "density_a" in row]
        densities_b = [float(row["density_b"]) for row in current if "density_b" in row]
        matrix.update(
            {
                "target": pairs,
                "mean_time_sec": float(np.mean(times)) if times else None,
                "max_time_sec": float(np.max(times)) if times else None,
                "mean_density_a": float(np.mean(densities_a)) if densities_a else None,
                "mean_density_b": float(np.mean(densities_b)) if densities_b else None,
            }
        )
        by_n[str(n)] = matrix

    total = confusion_for(rows)
    total.update(
        {
            "sizes": sizes,
            "pairs_per_size": pairs,
            "target_total": len(sizes) * pairs,
            "by_n": by_n,
        }
    )
    return total


def percent(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.4%}"


def print_summary(summary: dict) -> None:
    print("\n" + "=" * 96)
    print("RANDOM-DENSITY VF2 VS OUR METHOD CONFUSION MATRIX")
    print("=" * 96)
    print(f"Target total : {summary['target_total']}")
    print(f"Attempted    : {summary['attempted']}")
    print(f"Valid        : {summary['valid']}")
    print(f"Errors       : {summary['errors']}")
    print()
    print("Overall confusion matrix")
    print("Rows = VF2 reference, columns = our certificate output")
    print()
    print("                 ours iso      ours non-iso")
    print(
        f"VF2 iso      {summary['true_positive_vf2_iso_ours_iso']:>10}"
        f" {summary['false_negative_vf2_iso_ours_non_iso']:>15}"
    )
    print(
        f"VF2 non-iso  {summary['false_positive_vf2_non_iso_ours_iso']:>10}"
        f" {summary['true_negative_vf2_non_iso_ours_non_iso']:>15}"
    )
    print()
    print(f"Accuracy           : {percent(summary['accuracy'])}")
    print(f"Iso precision      : {percent(summary['precision_iso'])}")
    print(f"Iso recall         : {percent(summary['recall_iso'])}")
    print(f"Non-iso specificity: {percent(summary['specificity_non_iso'])}")
    print("-" * 96)
    for n, row in summary["by_n"].items():
        mean = row["mean_time_sec"]
        mean_text = f"{mean:.3f}s" if mean is not None else "n/a"
        print(
            f"n={int(n):>3} | {row['attempted']:>4}/{row['target']:<4} | "
            f"TP {row['true_positive_vf2_iso_ours_iso']:>3} | "
            f"TN {row['true_negative_vf2_non_iso_ours_non_iso']:>3} | "
            f"FP {row['false_positive_vf2_non_iso_ours_iso']:>3} | "
            f"FN {row['false_negative_vf2_iso_ours_non_iso']:>3} | "
            f"acc {percent(row['accuracy']):>9} | mean {mean_text}"
        )
    print("=" * 96)


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

    print("=" * 96)
    print("RANDOM-DENSITY CONFUSION EXPERIMENT")
    print(f"Sizes        : {args.sizes}")
    print(f"Pairs / size : {args.pairs}")
    print(f"Target total : {total}")
    print(f"Density      : random per graph in [{args.density_min:.2f}, {args.density_max:.2f}]")
    print(f"Output dir   : {output_dir}")
    print("=" * 96)

    run_idx = 0
    for n in args.sizes:
        for pair in range(args.pairs):
            run_idx += 1
            started = time.perf_counter()
            row = {
                "n": n,
                "pair": pair,
                "seed": args.seed,
            }
            try:
                graph_a, density_a = random_graph(n, rng, args.density_min, args.density_max)
                graph_b, density_b = random_graph(n, rng, args.density_min, args.density_max)
                vf2_isomorphic = bool(nx.is_isomorphic(graph_a, graph_b))
                z_star, i_score, certified = compute_isomorphism_index(
                    graph_a,
                    graph_b,
                    lambda_val=args.lambda_val,
                    base_dir=str(matrices_dir),
                    case_type="random_density_confusion",
                )
                row.update(
                    {
                        "density_a": density_a,
                        "density_b": density_b,
                        "vf2_isomorphic": vf2_isomorphic,
                        "ours_certified_iso": bool(certified),
                        "Z_star": None if z_star is None else float(z_star),
                        "I": None if i_score is None else float(i_score),
                        "error": None,
                    }
                )
            except Exception as exc:
                row.update(
                    {
                        "density_a": None,
                        "density_b": None,
                        "vf2_isomorphic": None,
                        "ours_certified_iso": None,
                        "Z_star": None,
                        "I": None,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )

            row["elapsed_sec"] = time.perf_counter() - started
            append_jsonl(results_path, row)

            vf2_text = "iso" if row.get("vf2_isomorphic") is True else "no"
            ours_text = "iso" if row.get("ours_certified_iso") is True else "no"
            if row.get("error"):
                vf2_text = "error"
                ours_text = "error"
            print(
                f"[{run_idx:>4}/{total}] n={n:>2} pair={pair:>3} "
                f"d=({row.get('density_a')}, {row.get('density_b')}) "
                f"vf2={vf2_text:<5} ours={ours_text:<5} "
                f"I={row.get('I')} t={row['elapsed_sec']:.3f}s",
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
        description="Run random-density graph pairs and build VF2-vs-ours confusion matrix."
    )
    parser.add_argument("--sizes", type=parse_sizes, default=DEFAULT_SIZES, help="Comma-separated sizes")
    parser.add_argument("--pairs", type=int, default=250, help="Random pairs per size")
    parser.add_argument("--seed", type=int, default=20260502)
    parser.add_argument("--density-min", type=float, default=0.20)
    parser.add_argument("--density-max", type=float, default=0.80)
    parser.add_argument("--lambda-val", type=float, default=0.1)
    parser.add_argument("--output-dir", default="random_density_confusion_results")
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
