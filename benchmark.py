"""
Benchmark for AHU Tree Isomorphism Algorithm.
Generates isomorphic and non-isomorphic tree pairs, checks correctness,
times execution (parallelised over 12 workers), and plots empirical vs O(n).
"""
import time
import random
import numpy as np
import matplotlib.pyplot as plt
import networkx as nx
from multiprocessing import Pool

from ahu_isomorphism import are_isomorphic

SIZES = [(i+1)*100 for i in range(100)]
PAIRS_PER_SIZE = 10
ISO_PAIRS = 5
NON_ISO_PAIRS = 5
SEED = 42
NUM_WORKERS = 12

random.seed(SEED)
np.random.seed(SEED)


# --------------------------------------------------------------------------
# Top-level worker functions (must be picklable for multiprocessing)
# --------------------------------------------------------------------------

def _time_pair(args):
    """Worker: time a single are_isomorphic call. Returns elapsed seconds."""
    T1, T2, _ = args
    t0 = time.perf_counter()
    are_isomorphic(T1, T2)
    return time.perf_counter() - t0


def _check_pair(args):
    """Worker: run are_isomorphic and return (expected, result)."""
    T1, T2, expected = args
    return expected, are_isomorphic(T1, T2)


def make_iso_pair(n, rng):
    """Generate an isomorphic pair by relabeling a random tree."""
    T1 = nx.random_labeled_tree(n, seed=rng)
    perm = list(range(n))
    rng.shuffle(perm)
    mapping = {i: perm[i] for i in range(n)}
    T2 = nx.relabel_nodes(T1, mapping)
    return T1, T2


def make_non_iso_pair(n, rng):
    """Generate two independent random trees (likely non-isomorphic)."""
    T1 = nx.random_labeled_tree(n, seed=rng)
    T2 = nx.random_labeled_tree(n, seed=rng)
    return T1, T2


def generate_pairs(n, rng):
    """Generate 100 pairs (50 iso, 50 non-iso) for a given size n."""
    pairs = []
    for _ in range(ISO_PAIRS):
        T1, T2 = make_iso_pair(n, rng)
        pairs.append((T1, T2, True))
    for _ in range(NON_ISO_PAIRS):
        T1, T2 = make_non_iso_pair(n, rng)
        pairs.append((T1, T2, False))
    return pairs


def correctness_check(pairs, n, pool):
    """
    Verify are_isomorphic on all pairs using the shared pool.
    Tolerates up to 5 false positives on non-iso pairs (chance collisions).
    """
    iso_failures = 0
    non_iso_false_positives = 0

    results = pool.map(_check_pair, pairs)
    for expected, result in results:
        if expected and not result:
            iso_failures += 1
        elif not expected and result:
            non_iso_false_positives += 1

    if iso_failures > 0:
        print(f"  [ERROR] n={n}: {iso_failures} isomorphic pairs returned False!")
    else:
        print(f"  [OK] n={n}: All {ISO_PAIRS} isomorphic pairs correctly identified.")

    if non_iso_false_positives > 5:
        print(f"  [WARN] n={n}: {non_iso_false_positives} non-iso pairs returned True "
              f"(possible chance isomorphisms or algorithm bug).")
    elif non_iso_false_positives > 0:
        print(f"  [OK] n={n}: {non_iso_false_positives} non-iso pair(s) returned True "
              f"(likely chance isomorphisms, within tolerance).")
    else:
        print(f"  [OK] n={n}: All {NON_ISO_PAIRS} non-isomorphic pairs correctly identified.")


def benchmark_pairs(pairs, pool):
    """
    Time each pair check in parallel across NUM_WORKERS workers.
    Returns list of individual times in seconds.
    """
    return pool.map(_time_pair, pairs)


def save_results(results, all_raw_times):
    """
    Save summary stats and all raw per-pair times to a CSV file.
    Columns: n, pair_index, time_ms, mean_ms, std_ms, min_ms, max_ms, median_ms
    """
    import csv
    with open('ahu_benchmark_times.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['n', 'pair_index', 'time_ms',
                         'mean_ms', 'std_ms', 'min_ms', 'max_ms', 'median_ms'])
        for (n, mean_t, std_t), raw in zip(results, all_raw_times):
            raw_ms = np.array(raw) * 1000
            mean_ms   = raw_ms.mean()
            std_ms    = raw_ms.std()
            min_ms    = raw_ms.min()
            max_ms    = raw_ms.max()
            median_ms = np.median(raw_ms)
            for i, t in enumerate(raw_ms):
                writer.writerow([n, i, f'{t:.6f}',
                                 f'{mean_ms:.6f}', f'{std_ms:.6f}',
                                 f'{min_ms:.6f}', f'{max_ms:.6f}',
                                 f'{median_ms:.6f}'])
    print("Timing data saved to ahu_benchmark_times.csv")


def plot_results(results):
    """
    Plot empirical mean ± std vs best-fit O(n) reference on linear axes.
    The O(n) slope is found via least-squares fit (c·n through origin)
    across all data points, avoiding distortion from small-n overhead.
    Saves to ahu_benchmark.png.
    """
    ns = np.array([r[0] for r in results])
    means = np.array([r[1] for r in results]) * 1000   # convert to ms
    stds = np.array([r[2] for r in results]) * 1000

    # Least-squares fit of y = c·n through origin: c = Σ(n·y) / Σ(n²)
    c = np.dot(ns, means) / np.dot(ns, ns)
    ref = c * ns

    fig, ax = plt.subplots(figsize=(9, 6))

    # Shaded ±1 std band
    ax.fill_between(ns, np.maximum(means - stds, 0), means + stds,
                    alpha=0.25, color='steelblue', label='±1 std dev')

    # Empirical line
    ax.plot(ns, means, 'o-', color='steelblue', linewidth=2,
            markersize=6, label='AHU empirical')

    # O(n) reference (best-fit slope)
    ax.plot(ns, ref, '--', color='tomato', linewidth=1.8,
            label=f'O(n) reference  (c={c:.4f} ms/node)')

    ax.set_xlabel('Tree size n', fontsize=13)
    ax.set_ylabel('Mean time (ms)', fontsize=13)
    ax.set_title('AHU Tree Isomorphism — Empirical vs O(n)', fontsize=14)
    ax.legend(fontsize=11)
    ax.grid(True, linestyle=':', alpha=0.5)

    plt.tight_layout()
    plt.savefig('ahu_benchmark.png', dpi=150)
    print("\nPlot saved to ahu_benchmark.png")
    plt.close()


def main():
    rng = random.Random(SEED)

    print("=" * 55)
    print("AHU Tree Isomorphism Benchmark")
    print(f"Workers: {NUM_WORKERS}")
    print("=" * 55)

    with Pool(processes=NUM_WORKERS) as pool:

        # --- Correctness check (small sizes only, generated fresh) ---
        print("\nCorrectness check (n=10 and n=20):")
        for n in [10, 20]:
            pairs = generate_pairs(n, rng)
            correctness_check(pairs, n, pool)

        # Reset rng so benchmark seeds are consistent regardless of
        # whether correctness sizes overlap with benchmark sizes.
        rng = random.Random(SEED + 1)

        # --- Benchmark one size at a time to keep memory bounded ---
        print("\nBenchmarking...")
        results = []
        all_raw_times = []
        for n in SIZES:
            pairs = generate_pairs(n, rng)
            times = benchmark_pairs(pairs, pool)
            mean_t = np.mean(times)
            std_t = np.std(times)
            results.append((n, mean_t, std_t))
            all_raw_times.append(times)
            print(f"  n={n:>6}: mean={mean_t*1000:8.3f} ms  std={std_t*1000:8.3f} ms")
            del pairs  # free memory before next size

    # --- Save raw times ---
    print("\nSaving timing data...")
    save_results(results, all_raw_times)

    # --- Plot ---
    print("\nPlotting results...")
    plot_results(results)

    print("\nDone.")


if __name__ == "__main__":
    main()
