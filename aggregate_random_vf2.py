#!/usr/bin/env python3
"""Aggregate random-pair VF2-vs-ours comparison shards."""

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
        vf2_non_iso = sum(1 for row in current if row.get("vf2_isomorphic") is False)
        vf2_iso = sum(1 for row in current if row.get("vf2_isomorphic") is True)
        ours_not_certified = sum(1 for row in current if row.get("ours_certified_iso") is False)
        ours_certified_iso = sum(1 for row in current if row.get("ours_certified_iso") is True)
        both_non_iso = sum(
            1
            for row in current
            if row.get("vf2_isomorphic") is False and row.get("ours_certified_iso") is False
        )
        false_iso = sum(
            1
            for row in current
            if row.get("vf2_isomorphic") is False and row.get("ours_certified_iso") is True
        )
        missed_accidental_iso = sum(
            1
            for row in current
            if row.get("vf2_isomorphic") is True and row.get("ours_certified_iso") is False
        )
        errors = sum(1 for row in current if row.get("error"))
        times = [float(row["elapsed_sec"]) for row in current if "elapsed_sec" in row]
        by_n[str(n)] = {
            "attempted": attempted,
            "vf2_non_iso": vf2_non_iso,
            "vf2_iso": vf2_iso,
            "ours_not_certified": ours_not_certified,
            "ours_certified_iso": ours_certified_iso,
            "both_vf2_non_iso_and_ours_not_certified": both_non_iso,
            "ours_false_iso_vs_vf2": false_iso,
            "vf2_iso_but_ours_not_certified": missed_accidental_iso,
            "errors": errors,
            "vf2_non_iso_rate": vf2_non_iso / attempted if attempted else None,
            "ours_not_certified_rate": ours_not_certified / attempted if attempted else None,
            "agreement_on_non_iso_rate": both_non_iso / vf2_non_iso if vf2_non_iso else None,
            "mean_time_sec": float(np.mean(times)) if times else None,
            "max_time_sec": float(np.max(times)) if times else None,
        }

    total_attempted = len(rows)
    total_vf2_non_iso = sum(item["vf2_non_iso"] for item in by_n.values())
    total_ours_not_certified = sum(item["ours_not_certified"] for item in by_n.values())
    total_both_non_iso = sum(item["both_vf2_non_iso_and_ours_not_certified"] for item in by_n.values())
    total_false_iso = sum(item["ours_false_iso_vs_vf2"] for item in by_n.values())
    total_errors = sum(item["errors"] for item in by_n.values())
    return {
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
    print("=" * 88)
    print("AGGREGATED RANDOM VF2 VS OUR SOLVER SUMMARY")
    print("=" * 88)
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
            f"n={int(n):>3} | attempted {row['attempted']:>5} | "
            f"VF2 non-iso {row['vf2_non_iso']:>5} | "
            f"ours not-cert {row['ours_not_certified']:>5} | "
            f"both {row['both_vf2_non_iso_and_ours_not_certified']:>5} | "
            f"false-iso {row['ours_false_iso_vs_vf2']:>3} | "
            f"errors {row['errors']:>3} | mean {mean_text}"
        )
    print("=" * 88)


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate random VF2-vs-ours shard outputs.")
    parser.add_argument("--root", default="insane_random_vf2", help="Root directory containing shard subdirectories")
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
