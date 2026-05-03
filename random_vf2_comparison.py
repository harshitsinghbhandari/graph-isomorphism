#!/usr/bin/env python3
"""Compare random graph-pair labels from NetworkX VF2 and the current solver.

For each generated random pair:
    1. NetworkX VF2 gives the reference label via nx.is_isomorphic.
    2. Our solver tries to certify isomorphism by rounding and checking A P = P B.

Important terminology:
    - "vf2_non_iso" means VF2 says the pair is not isomorphic.
    - "ours_not_certified" means our rounded permutation did not certify AP = PB.

The second statement is not a mathematical proof of non-isomorphism. It is the
current solver's negative output.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import networkx as nx
import numpy as np

from generators import make_non_isomorphic_pair
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


def read_rows(results_path: Path) -> list[dict]:
    if not results_path.exists():
        return []
    with results_path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def summarize(results_path: Path, sizes: list[int], pairs_per_size: int) -> dict:
    rows = read_rows(results_path)
    by_n = {}
    for n in sizes:
        current = [row for row in rows if int(row["n"]) == n]
        attempted = len(current)
        vf2_non_iso = sum(1 for row in current if row.get("vf2_isomorphic") is False)
        vf2_iso = sum(1 for row in current if row.get("vf2_isomorphic") is True)
        ours_certified_iso = sum(1 for row in current if row.get("ours_certified_iso") is True)
        ours_not_certified = sum(1 for row in current if row.get("ours_certified_iso") is False)
        errors = sum(1 for row in current if row.get("error"))
        both_non_iso = sum(
            1
            for row in current
            if row.get("vf2_isomorphic") is False and row.get("ours_certified_iso") is False
        )
        ours_false_iso = sum(
            1
            for row in current
            if row.get("vf2_isomorphic") is False and row.get("ours_certified_iso") is True
        )
        accidental_iso_missed = sum(
            1
            for row in current
            if row.get("vf2_isomorphic") is True and row.get("ours_certified_iso") is False
        )
        times = [float(row["elapsed_sec"]) for row in current if "elapsed_sec" in row]
        by_n[str(n)] = {
            "attempted": attempted,
            "target": pairs_per_size,
            "vf2_non_iso": vf2_non_iso,
            "vf2_iso": vf2_iso,
            "ours_not_certified": ours_not_certified,
            "ours_certified_iso": ours_certified_iso,
            "both_vf2_non_iso_and_ours_not_certified": both_non_iso,
            "ours_false_iso_vs_vf2": ours_false_iso,
            "vf2_iso_but_ours_not_certified": accidental_iso_missed,
            "errors": errors,
            "vf2_non_iso_rate": vf2_non_iso / attempted if attempted else None,
            "ours_not_certified_rate": ours_not_certified / attempted if attempted else None,
            "agreement_on_non_iso_rate": both_non_iso / vf2_non_iso if vf2_non_iso else None,
            "mean_time_sec": float(np.mean(times)) if times else None,
            "max_time_sec": float(np.max(times)) if times else None,
        }

    total_attempted = sum(item["attempted"] for item in by_n.values())
    total_vf2_non_iso = sum(item["vf2_non_iso"] for item in by_n.values())
    total_ours_not_certified = sum(item["ours_not_certified"] for item in by_n.values())
    total_both_non_iso = sum(item["both_vf2_non_iso_and_ours_not_certified"] for item in by_n.values())
    total_false_iso = sum(item["ours_false_iso_vs_vf2"] for item in by_n.values())
    total_errors = sum(item["errors"] for item in by_n.values())
    return {
        "sizes": sizes,
        "pairs_per_size": pairs_per_size,
        "target_total": len(sizes) * pairs_per_size,
        "attempted_total": total_attempted,
        "vf2_non_iso_total": total_vf2_non_iso,
        "ours_not_certified_total": total_ours_not_certified,
        "both_vf2_non_iso_and_ours_not_certified_total": total_both_non_iso,
        "ours_false_iso_vs_vf2_total": total_false_iso,
        "errors_total": total_errors,
        "vf2_non_iso_rate": total_vf2_non_iso / total_attempted if total_attempted else None,
        "ours_not_certified_rate": total_ours_not_certified / total_attempted if total_attempted else None,
        "agreement_on_non_iso_rate": total_both_non_iso / total_vf2_non_iso if total_vf2_non_iso else None,
        "by_n": by_n,
    }


def percent(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.4%}"


def print_summary(summary: dict) -> None:
    print("\n" + "=" * 88)
    print("RANDOM PAIR VF2 VS OUR SOLVER SUMMARY")
    print("=" * 88)
    print(f"Target total        : {summary['target_total']}")
    print(f"Attempted total     : {summary['attempted_total']}")
    print(f"VF2 non-iso         : {summary['vf2_non_iso_total']} ({percent(summary['vf2_non_iso_rate'])})")
    print(
        f"Ours not certified  : {summary['ours_not_certified_total']} "
        f"({percent(summary['ours_not_certified_rate'])})"
    )
    print(
        f"Both non-iso output : {summary['both_vf2_non_iso_and_ours_not_certified_total']} "
        f"({percent(summary['agreement_on_non_iso_rate'])} of VF2 non-iso)"
    )
    print(f"Ours false iso vs VF2 non-iso : {summary['ours_false_iso_vs_vf2_total']}")
    print(f"Errors              : {summary['errors_total']}")
    print("-" * 88)
    for n, row in summary["by_n"].items():
        mean = row["mean_time_sec"]
        mean_text = f"{mean:.3f}s" if mean is not None else "n/a"
        print(
            f"n={int(n):>3} | attempted {row['attempted']:>5}/{row['target']:<5} | "
            f"VF2 non-iso {row['vf2_non_iso']:>5} | "
            f"ours not-cert {row['ours_not_certified']:>5} | "
            f"both {row['both_vf2_non_iso_and_ours_not_certified']:>5} | "
            f"false-iso {row['ours_false_iso_vs_vf2']:>3} | "
            f"errors {row['errors']:>3} | mean {mean_text}"
        )
    print("=" * 88)


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

    print("=" * 88)
    print("RANDOM PAIR VF2 VS OUR SOLVER")
    print(f"Sizes        : {args.sizes}")
    print(f"Pairs / size : {args.pairs}")
    print(f"Target total : {total}")
    print(f"Density      : [{args.density_min:.2f}, {args.density_max:.2f}]")
    print(f"Output dir   : {output_dir}")
    print("=" * 88)

    attempted = 0
    for n in args.sizes:
        for pair in range(args.pairs):
            attempted += 1
            started = time.perf_counter()
            row = {
                "n": n,
                "pair": pair,
                "seed": args.seed,
                "density_range": [args.density_min, args.density_max],
            }
            try:
                graph_a, graph_b = make_non_isomorphic_pair(
                    n,
                    rng,
                    density_range=(args.density_min, args.density_max),
                )
                vf2_isomorphic = bool(nx.is_isomorphic(graph_a, graph_b))
                z_star, i_score, certified = compute_isomorphism_index(
                    graph_a,
                    graph_b,
                    lambda_val=args.lambda_val,
                    base_dir=str(matrices_dir),
                    case_type="random_vf2_compare",
                )
                row.update(
                    {
                        "vf2_isomorphic": vf2_isomorphic,
                        "vf2_non_iso": not vf2_isomorphic,
                        "ours_certified_iso": bool(certified),
                        "ours_not_certified": not bool(certified),
                        "Z_star": None if z_star is None else float(z_star),
                        "I": None if i_score is None else float(i_score),
                        "error": None,
                    }
                )
            except Exception as exc:
                row.update(
                    {
                        "vf2_isomorphic": None,
                        "vf2_non_iso": None,
                        "ours_certified_iso": None,
                        "ours_not_certified": None,
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
                f"[{attempted:>5}/{total}] n={n:>3} pair={pair:>4} "
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
        description="Compare NetworkX VF2 non-isomorphism labels with our solver's not-certified output."
    )
    parser.add_argument(
        "--sizes",
        type=parse_sizes,
        default=[8, 9, 10, 11, 12, 15, 20, 25, 30],
        help="Comma-separated sizes",
    )
    parser.add_argument("--pairs", type=int, default=250, help="Random pairs per size")
    parser.add_argument("--seed", type=int, default=84)
    parser.add_argument("--density-min", type=float, default=0.80)
    parser.add_argument("--density-max", type=float, default=0.85)
    parser.add_argument("--lambda-val", type=float, default=0.1)
    parser.add_argument("--output-dir", default="random_vf2_results")
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
