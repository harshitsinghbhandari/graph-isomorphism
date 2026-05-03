#!/usr/bin/env python3
"""Aggregate one or more isomorphic stress-test shard directories."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def read_rows(root: Path) -> list[dict]:
    rows: list[dict] = []
    for path in sorted(root.glob("*/results.jsonl")):
        shard = path.parent.name
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                row["shard"] = shard
                rows.append(row)
    return rows


def summarize(rows: list[dict]) -> dict:
    sizes = sorted({int(row["n"]) for row in rows})
    by_n = {}
    for n in sizes:
        current = [row for row in rows if int(row["n"]) == n]
        attempted = len(current)
        certified = sum(1 for row in current if row.get("certified") is True)
        errors = sum(1 for row in current if row.get("error"))
        times = [float(row["elapsed_sec"]) for row in current if "elapsed_sec" in row]
        by_n[str(n)] = {
            "attempted": attempted,
            "certified_correct": certified,
            "not_certified": attempted - certified - errors,
            "errors": errors,
            "accuracy_on_attempted": certified / attempted if attempted else None,
            "mean_time_sec": float(np.mean(times)) if times else None,
            "max_time_sec": float(np.max(times)) if times else None,
        }

    total_attempted = len(rows)
    total_certified = sum(1 for row in rows if row.get("certified") is True)
    total_errors = sum(1 for row in rows if row.get("error"))
    return {
        "attempted_total": total_attempted,
        "certified_correct_total": total_certified,
        "not_certified_total": total_attempted - total_certified - total_errors,
        "errors_total": total_errors,
        "accuracy_on_attempted": total_certified / total_attempted if total_attempted else None,
        "by_n": by_n,
    }


def print_summary(summary: dict) -> None:
    print("=" * 72)
    print("AGGREGATED ISOMORPHIC STRESS SUMMARY")
    print("=" * 72)
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
        mean = row["mean_time_sec"]
        mean_text = f"{mean:.3f}s" if mean is not None else "n/a"
        print(
            f"n={int(n):>3} | attempted {row['attempted']:>5} | "
            f"certified {row['certified_correct']:>5} | "
            f"not certified {row['not_certified']:>5} | "
            f"errors {row['errors']:>4} | acc {acc_text:>9} | mean {mean_text}"
        )
    print("=" * 72)


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate isomorphic stress-test shard outputs.")
    parser.add_argument("--root", default="insane_iso_stress", help="Root directory containing shard subdirectories")
    parser.add_argument("--output", default=None, help="Summary JSON path")
    args = parser.parse_args()

    root = Path(args.root)
    rows = read_rows(root)
    summary = summarize(rows)
    print_summary(summary)

    output = Path(args.output) if args.output else root / "summary.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
