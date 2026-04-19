import time
import numpy as np
from isomorphism import compute_isomorphism_index
from generators import make_isomorphic_pair, make_non_isomorphic_pair

def run_benchmark(n_min=1, n_max=50, pairs_per_type=5, lambda_val=0.1, solver_weights=None):
    rng = np.random.default_rng(42)
    results = []

    total_runs = (n_max - n_min + 1) * 2 * pairs_per_type
    run_idx = 0

    for n in range(n_min, n_max + 1):
        iso_times, non_iso_times = [], []
        iso_scores, non_iso_scores = [], []
        iso_z, non_iso_z = [], []

        for _ in range(pairs_per_type):
            # --- Isomorphic pair ---
            run_idx += 1
            G1, G2 = make_isomorphic_pair(n, rng)
            t0 = time.perf_counter()
            Z, I = compute_isomorphism_index(G1, G2, lambda_val, solver_weights=solver_weights)
            elapsed = time.perf_counter() - t0
            if Z is not None:
                iso_times.append(elapsed)
                iso_scores.append(I)
                iso_z.append(Z)
            pct = 100 * run_idx / total_runs
            print(f"\r  Progress: {pct:5.1f}%  |  n={n:3d}  |  iso pair {_+1}/{pairs_per_type}   ", end="", flush=True)

        for _ in range(pairs_per_type):
            # --- Non-isomorphic pair ---
            run_idx += 1
            G1, G2 = make_non_isomorphic_pair(n, rng)
            t0 = time.perf_counter()
            Z, I = compute_isomorphism_index(G1, G2, lambda_val, solver_weights=solver_weights)
            elapsed = time.perf_counter() - t0
            if Z is not None:
                non_iso_times.append(elapsed)
                non_iso_scores.append(I)
                non_iso_z.append(Z)
            pct = 100 * run_idx / total_runs
            print(f"\r  Progress: {pct:5.1f}%  |  n={n:3d}  |  non-iso pair {_+1}/{pairs_per_type}  ", end="", flush=True)

        def safe_stats(lst):
            if not lst:
                return {"mean": None, "min": None, "max": None, "std": None}
            a = np.array(lst)
            return {"mean": float(np.mean(a)), "min": float(np.min(a)),
                    "max": float(np.max(a)), "std": float(np.std(a))}

        results.append({
            "n": n,
            "iso_time": safe_stats(iso_times),
            "non_iso_time": safe_stats(non_iso_times),
            "iso_score": safe_stats(iso_scores),
            "non_iso_score": safe_stats(non_iso_scores),
            "iso_z": safe_stats(iso_z),
            "non_iso_z": safe_stats(non_iso_z),
        })

    print()  # newline after progress
    return results
