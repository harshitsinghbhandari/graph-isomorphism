import json
import shutil
from pathlib import Path
from comparison_report import generate_comparison_report
import config
from benchmark import run_benchmark
from matrix_viewer import generate_viewer, scan_matrices
from report import generate_report

if __name__ == "__main__":
    print("="*60)
    print("  ISOMORPHISM INDEX — BENCHMARK")
    print(f"  n = {config.N_MIN} to {config.N_MAX} | {config.PAIRS} iso + {config.PAIRS} non-iso pairs per n")
    print(f"  Total QP solves: {(config.N_MAX - config.N_MIN + 1) * 2 * config.PAIRS}")
    print("="*60)

    data_dir = Path("data")
    if data_dir.exists():
        print("\n  Clearing existing data directory...")
        shutil.rmtree(data_dir)

    results = run_benchmark(
        config.N_MIN,
        config.N_MAX,
        config.PAIRS,
        config.LAMBDA_VAL,
    )

    print("\n  Generating HTML report...")
    generate_report(results, config.N_MAX, config.PAIRS, config.LAMBDA_VAL, config.REPORT_PATH)

    # Also save raw JSON for further analysis
    json_path = config.REPORT_PATH.replace(".html", ".json")
    Path(json_path).write_text(json.dumps(results, indent=2))
    print(f"  Raw data saved → {json_path}")

    print("\n  Generating matrix viewer...")
    matrix_data = scan_matrices()
    generate_viewer(matrix_data)

    print("\n  Generating detailed comparison report...")
    generate_comparison_report()

    print("\n" + "="*60)
    print("  DONE. Open the HTML report in any browser.")
    print("="*60)
