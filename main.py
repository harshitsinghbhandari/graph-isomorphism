#!/usr/bin/env python3
"""Project entry point for tests, demos, and small solver experiments."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from types import SimpleNamespace
from pathlib import Path

import networkx as nx
import numpy as np

DEFAULT_DENSITY_RANGE = (0.80, 0.85)


def _density_range(args: argparse.Namespace) -> tuple[float, float]:
    density_range = (args.density_min, args.density_max)
    if not (0.0 <= density_range[0] <= density_range[1] <= 1.0):
        raise ValueError(f"Invalid density range: {density_range}")
    return density_range


def _stats(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"mean": None, "min": None, "max": None, "std": None}
    arr = np.asarray(values, dtype=float)
    return {
        "mean": float(np.mean(arr)),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "std": float(np.std(arr)),
    }


def run_tests(args: argparse.Namespace) -> int:
    """Run the repository's Python tests."""
    cmd = [sys.executable, "-m", "unittest", "discover", "-v"]
    if args.pattern:
        cmd.extend(["-p", args.pattern])
    return subprocess.run(cmd, check=False).returncode


def run_single(args: argparse.Namespace) -> int:
    """Run one clearly isomorphic pair and generate a matrix viewer."""
    from generators import make_isomorphic_pair
    from isomorphism import compute_isomorphism_index
    from matrix_viewer import generate_viewer, scan_matrices

    density_range = _density_range(args)
    out_dir = Path(args.output_dir)
    matrices_dir = out_dir / "matrices"
    viewer_path = out_dir / "matrix_viewer.html"
    summary_path = out_dir / "run_summary.json"

    if out_dir.exists():
        shutil.rmtree(out_dir)
    matrices_dir.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(args.seed)
    graph_a, graph_b = make_isomorphic_pair(args.n, rng, density_range=density_range)
    exact_iso = nx.is_isomorphic(graph_a, graph_b)
    if not exact_iso:
        raise RuntimeError("Generator returned a pair that is not isomorphic.")

    print("=" * 64)
    print("  SINGLE ISOMORPHIC CASE")
    print(f"  n          : {args.n}")
    print(f"  seed       : {args.seed}")
    print(f"  density    : [{density_range[0]:.2f}, {density_range[1]:.2f}]")
    print(f"  output dir : {out_dir}")
    print("=" * 64)

    z_star, i_score, certified = compute_isomorphism_index(
        graph_a,
        graph_b,
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
        "solver_certified_isomorphic": bool(certified),
        "Z_star": float(z_star),
        "I": float(i_score),
        "matrix_viewer": str(viewer_path),
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"  Exact isomorphic : {exact_iso}")
    print(f"  Solver certified : {certified}")
    print(f"  Z*               : {z_star:.6g}")
    print(f"  I                : {i_score:.6g}")
    print(f"  Summary          : {summary_path}")
    print(f"  Matrix viewer    : {viewer_path}")
    print("=" * 64)
    return 0


def run_compare(args: argparse.Namespace) -> int:
    """Run a small configurable benchmark and generate report/viewer artifacts."""
    from generators import make_isomorphic_pair, make_non_isomorphic_pair
    from isomorphism import compute_isomorphism_index
    from matrix_viewer import generate_viewer, scan_matrices
    from report import generate_report

    density_range = _density_range(args)
    out_dir = Path(args.output_dir)
    matrices_dir = out_dir / "matrices"
    report_path = out_dir / "isomorphism_report.html"
    summary_path = out_dir / "isomorphism_report.json"
    viewer_path = out_dir / "matrix_viewer.html"

    if args.n_min > args.n_max:
        raise ValueError("--n-min must be <= --n-max")
    if out_dir.exists():
        shutil.rmtree(out_dir)
    matrices_dir.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(args.seed)
    results = []
    total_runs = (args.n_max - args.n_min + 1) * 2 * args.pairs
    run_idx = 0

    print("=" * 64)
    print("  CURRENT-SOLVER COMPARISON")
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
            graph_a, graph_b = make_isomorphic_pair(n, rng, density_range=density_range)
            start = time.perf_counter()
            z_star, i_score, certified = compute_isomorphism_index(
                graph_a,
                graph_b,
                lambda_val=args.lambda_val,
                base_dir=str(matrices_dir),
                comparison_type="isomorphic",
            )
            elapsed = time.perf_counter() - start
            if z_star is not None:
                iso_times.append(elapsed)
                iso_scores.append(float(i_score))
                iso_z.append(float(z_star))
                iso_cert.append(bool(certified))
            pct = 100 * run_idx / total_runs
            print(
                f"\r  Progress: {pct:5.1f}% | n={n:3d} | iso {pair_idx + 1}/{args.pairs}",
                end="",
                flush=True,
            )

        for pair_idx in range(args.pairs):
            run_idx += 1
            graph_a, graph_b = make_non_isomorphic_pair(n, rng, density_range=density_range)
            start = time.perf_counter()
            z_star, i_score, certified = compute_isomorphism_index(
                graph_a,
                graph_b,
                lambda_val=args.lambda_val,
                base_dir=str(matrices_dir),
                comparison_type="random",
            )
            elapsed = time.perf_counter() - start
            if z_star is not None:
                random_times.append(elapsed)
                random_scores.append(float(i_score))
                random_z.append(float(z_star))
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
    return 0


def run_viewer(args: argparse.Namespace) -> int:
    """Generate a matrix viewer from an existing matrices directory."""
    from matrix_viewer import generate_viewer, scan_matrices

    viewer_data = scan_matrices(args.base_dir)
    generate_viewer(viewer_data, args.output, show_graphs=not args.hide_graphs)
    return 0


def _interactive_dependencies():
    try:
        import questionary
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
    except ImportError as exc:
        raise RuntimeError(
            "Interactive mode requires questionary and rich. "
            "Run: pip install -r requirements.txt"
        ) from exc
    return questionary, Console, Panel, Table


def _ask_int(questionary, label: str, default: int) -> int:
    value = questionary.text(label, default=str(default)).ask()
    if value is None:
        raise KeyboardInterrupt
    return int(value)


def _ask_float(questionary, label: str, default: float) -> float:
    value = questionary.text(label, default=str(default)).ask()
    if value is None:
        raise KeyboardInterrupt
    return float(value)


def _ask_text(questionary, label: str, default: str) -> str:
    value = questionary.text(label, default=default).ask()
    if value is None:
        raise KeyboardInterrupt
    return value.strip() or default


def _common_interactive_args(questionary, default_output: str) -> dict[str, object]:
    return {
        "seed": _ask_int(questionary, "RNG seed", 42),
        "density_min": _ask_float(questionary, "Minimum density", DEFAULT_DENSITY_RANGE[0]),
        "density_max": _ask_float(questionary, "Maximum density", DEFAULT_DENSITY_RANGE[1]),
        "output_dir": _ask_text(questionary, "Output directory", default_output),
        "show_graphs": bool(questionary.confirm("Show graph panels in viewer?", default=False).ask()),
    }


def _print_command_table(console, Table) -> None:
    table = Table(title="Non-interactive commands")
    table.add_column("Task", style="bold")
    table.add_column("Command")
    table.add_row("Tests", "python main.py test")
    table.add_row("Single case", "python main.py single --n 101")
    table.add_row("Small comparison", "python main.py compare --n-min 5 --n-max 30 --pairs 5")
    table.add_row(
        "Viewer",
        "python main.py viewer --base-dir benchmark_data/matrices --output benchmark_matrix_viewer.html --hide-graphs",
    )
    table.add_row("Large benchmark", "python big_benchmark.py --sizes 50,60,70,80,90,100")
    console.print(table)


def run_interactive(args: argparse.Namespace) -> int:
    """Run an interactive terminal menu for common workflows."""
    questionary, Console, Panel, Table = _interactive_dependencies()
    console = Console()

    console.print(
        Panel.fit(
            "Graph Isomorphism CLI\n"
            "Relaxation -> hyperplane rounding -> exact AP = PB verification",
            title="final-presentation",
            border_style="blue",
        )
    )

    while True:
        choice = questionary.select(
            "Choose an action",
            choices=[
                "Run tests",
                "Run one isomorphic case",
                "Run small comparison",
                "Build matrix viewer",
                "Show command cheatsheet",
                "Exit",
            ],
        ).ask()

        if choice is None or choice == "Exit":
            return 0

        try:
            if choice == "Run tests":
                pattern = questionary.text(
                    "Test discovery pattern (blank = default)", default=""
                ).ask()
                code = run_tests(SimpleNamespace(pattern=pattern or None))
                console.print(f"[bold]Tests exited with code {code}[/bold]")

            elif choice == "Run one isomorphic case":
                n = _ask_int(questionary, "Number of nodes", 101)
                values = _common_interactive_args(questionary, f"single_case_n{n}")
                run_single(SimpleNamespace(n=n, **values))

            elif choice == "Run small comparison":
                n_min = _ask_int(questionary, "Minimum n", 5)
                n_max = _ask_int(questionary, "Maximum n", 25)
                pairs = _ask_int(questionary, "Pairs per type per n", 5)
                lambda_val = _ask_float(questionary, "Index lambda", 0.1)
                values = _common_interactive_args(questionary, f"compare_n{n_min}_{n_max}")
                run_compare(
                    SimpleNamespace(
                        n_min=n_min,
                        n_max=n_max,
                        pairs=pairs,
                        lambda_val=lambda_val,
                        **values,
                    )
                )

            elif choice == "Build matrix viewer":
                base_dir = _ask_text(questionary, "Matrices directory", "data/matrices")
                output = _ask_text(questionary, "Output HTML file", "matrix_viewer.html")
                hide_graphs = bool(questionary.confirm("Hide graph panels?", default=True).ask())
                run_viewer(
                    SimpleNamespace(
                        base_dir=base_dir,
                        output=output,
                        hide_graphs=hide_graphs,
                    )
                )

            elif choice == "Show command cheatsheet":
                _print_command_table(console, Table)

        except KeyboardInterrupt:
            console.print("\n[yellow]Cancelled.[/yellow]")
        except Exception as exc:
            console.print(f"[red]Error:[/red] {type(exc).__name__}: {exc}")


def add_density_args(parser: argparse.ArgumentParser) -> None:
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Clean entry point for graph-isomorphism experiments."
    )
    subparsers = parser.add_subparsers(dest="command")

    interactive_parser = subparsers.add_parser(
        "interactive", help="Open an interactive terminal menu"
    )
    interactive_parser.set_defaults(func=run_interactive)

    test_parser = subparsers.add_parser("test", help="Run unit tests")
    test_parser.add_argument("-p", "--pattern", help="unittest discovery pattern")
    test_parser.set_defaults(func=run_tests)

    single_parser = subparsers.add_parser(
        "single", help="Run one isomorphic case and build a matrix viewer"
    )
    single_parser.add_argument("--n", type=int, default=101, help="Number of nodes")
    single_parser.add_argument("--seed", type=int, default=42, help="RNG seed")
    single_parser.add_argument(
        "--output-dir", default="single_case_n101", help="Fresh output directory"
    )
    single_parser.add_argument("--show-graphs", action="store_true")
    add_density_args(single_parser)
    single_parser.set_defaults(func=run_single)

    compare_parser = subparsers.add_parser(
        "compare", help="Run a small n-range benchmark and build reports"
    )
    compare_parser.add_argument("--n-min", type=int, default=5)
    compare_parser.add_argument("--n-max", type=int, default=25)
    compare_parser.add_argument("--pairs", type=int, default=5, help="Pairs per type per n")
    compare_parser.add_argument("--seed", type=int, default=42)
    compare_parser.add_argument("--lambda-val", type=float, default=0.1)
    compare_parser.add_argument("--output-dir", default="compare_n5_25")
    compare_parser.add_argument("--show-graphs", action="store_true")
    add_density_args(compare_parser)
    compare_parser.set_defaults(func=run_compare)

    viewer_parser = subparsers.add_parser(
        "viewer", help="Build an HTML matrix viewer from saved matrix JSON files"
    )
    viewer_parser.add_argument("--base-dir", default="data/matrices")
    viewer_parser.add_argument("--output", default="matrix_viewer.html")
    viewer_parser.add_argument("--hide-graphs", action="store_true")
    viewer_parser.set_defaults(func=run_viewer)

    return parser


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if not argv:
        argv = ["interactive"]
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
