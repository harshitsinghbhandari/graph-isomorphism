"""Goemans-Williamson style hyperplane rounding for graph isomorphism.

Background
----------
Goemans & Williamson (1995) solved Max-Cut by lifting each vertex to a unit
vector v_i on the sphere via SDP, then sampling a random hyperplane (a random
vector r) and partitioning vertices by sign(r . v_i).  The randomness gives a
(0.878..)-approximation in expectation.

In our setting the relaxed solution lives in the Birkhoff polytope rather than
on a sphere: X* is an n-by-n doubly-stochastic matrix produced by the QP in
``isomorphism.py``.  We want to extract a permutation matrix P out of it.  The
direct analog of GW hyperplane rounding is:

    1. Spectrally embed each "row vertex" (i in graph A) and each "column
       vertex" (j in graph B) into R^r via the SVD of X*.  Setting
       X* = U * Sigma * V^T and U_emb = U[:, :r] * sqrt(Sigma[:r]),
       V_emb = V[:, :r] * sqrt(Sigma[:r]) gives  X*[i,j] ~= <U_emb[i], V_emb[j]>.

    2. Sample k random hyperplanes through the origin in R^r as columns of a
       Gaussian matrix G in R^{r x k}.  The "signature" of node i in A is the
       vector of signs sign(U_emb[i] . G_t) over hyperplanes t = 1..k.  Same
       for B.

    3. The Hamming distance between signatures is
       d(i,j) = (k - <s_i, s'_j>) / 2.
       Pairs of nodes with similar X* embeddings get similar signatures, which
       Hamming distance picks up.  Solving a linear assignment over the
       Hamming-distance matrix produces a permutation P.

    4. Repeat T trials with fresh random hyperplanes, keep the P that minimises
       the integer residual ||A P - P B||_F^2.  Stop early on a zero residual
       (exact isomorphism witness).

This module is self-contained and does not require Gurobi.  It only needs
numpy + scipy and an X* matrix produced elsewhere.
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import linear_sum_assignment


def _embed_via_svd(X_star: np.ndarray, rank: int | None = None):
    """SVD-based row/column embedding of a (doubly-stochastic) matrix.

    Returns (U_emb, V_emb), each of shape (n, r), with the property that
    U_emb @ V_emb.T reconstructs X* up to the truncation rank.
    """
    U, sigma, Vt = np.linalg.svd(X_star, full_matrices=False)
    n_sv = len(sigma)
    if rank is None:
        rank = n_sv
    rank = max(1, min(rank, n_sv))
    sqrt_sigma = np.sqrt(np.clip(sigma[:rank], 0.0, None))
    U_emb = U[:, :rank] * sqrt_sigma[None, :]
    V_emb = Vt[:rank, :].T * sqrt_sigma[None, :]
    return U_emb, V_emb


def _frobenius_residual_sq(A: np.ndarray, B: np.ndarray, P: np.ndarray) -> int:
    """||A P - P B||_F^2 in integer arithmetic."""
    A_int = A.astype(np.int64)
    B_int = B.astype(np.int64)
    P_int = P.astype(np.int64)
    diff = A_int @ P_int - P_int @ B_int
    return int(np.sum(diff * diff))


def _integer_verify(A: np.ndarray, B: np.ndarray, P: np.ndarray) -> bool:
    return _frobenius_residual_sq(A, B, P) == 0


def hyperplane_round(
    X_star: np.ndarray,
    A: np.ndarray,
    B: np.ndarray,
    num_trials: int = 200,
    rank: int | None = None,
    num_hyperplanes: int | None = None,
    seed: int | None = None,
):
    """Round a doubly-stochastic X* to a permutation P via hyperplane rounding.

    Parameters
    ----------
    X_star : (n, n) ndarray
        Relaxed solution from the Birkhoff-polytope QP.
    A, B : (n, n) ndarray
        Adjacency matrices of the two graphs.  Used only for trial scoring.
    num_trials : int
        Independent random-hyperplane samples to draw.  More trials => better
        chance of finding an exact isomorphism witness when one exists.
    rank : int, optional
        Truncation rank of the X* SVD embedding.  Defaults to the full numerical
        rank (min(n, number of nonzero singular values)).
    num_hyperplanes : int, optional
        Number of hyperplanes per trial (the "k" in the docstring).  Defaults to
        ceil(4 * log2(n + 2)).  In GW-style analyses, accuracy of the Hamming
        signature scales like O(log n / k^{1/2}).
    seed : int, optional
        Seed for ``numpy.random.default_rng``.  Pass for reproducibility.

    Returns
    -------
    P_best : (n, n) int ndarray
        Permutation matrix minimising ||A P - P B||_F^2 across trials.
    stats : dict
        Diagnostics:
            trials_run, best_trial, best_residual, is_isomorphic,
            embedding_rank, num_hyperplanes
    """
    n = X_star.shape[0]
    if X_star.shape != (n, n):
        raise ValueError("X_star must be square.")
    if A.shape != (n, n) or B.shape != (n, n):
        raise ValueError("A, B must be n x n with the same n as X_star.")

    rng = np.random.default_rng(seed)
    U_emb, V_emb = _embed_via_svd(X_star, rank=rank)
    r = U_emb.shape[1]
    k = (
        num_hyperplanes
        if num_hyperplanes is not None
        else max(2, int(np.ceil(4 * np.log2(n + 2))))
    )

    P_best: np.ndarray | None = None
    best_residual = np.inf
    best_trial = -1
    trials_run = 0

    for t in range(num_trials):
        trials_run = t + 1
        G = rng.standard_normal(size=(r, k))
        S_A = np.sign(U_emb @ G)
        S_B = np.sign(V_emb @ G)
        # Treat exact zeros (rare; happens only on the hyperplane itself) as +1
        # to keep signatures in {-1, +1}.
        S_A[S_A == 0] = 1.0
        S_B[S_B == 0] = 1.0

        # Hamming distance matrix:  d(i, j) = (k - <s_i, s'_j>) / 2.
        cost = (k - S_A @ S_B.T) * 0.5

        row_ind, col_ind = linear_sum_assignment(cost)
        P_t = np.zeros((n, n), dtype=int)
        P_t[row_ind, col_ind] = 1

        residual = _frobenius_residual_sq(A, B, P_t)
        if residual < best_residual:
            best_residual = residual
            P_best = P_t
            best_trial = t
            if residual == 0:
                break  # exact witness; no point in further trials.

    stats = {
        "trials_run": trials_run,
        "best_trial": best_trial,
        "best_residual": int(best_residual) if best_residual != np.inf else None,
        "is_isomorphic": bool(best_residual == 0),
        "embedding_rank": r,
        "num_hyperplanes": k,
    }
    return P_best, stats


# --------------------------------------------------------------------------- #
# Demo / smoke-test entry point.                                              #
#                                                                             #
#   python hyperplane_rounding.py                                             #
#                                                                             #
# Tries (in order):                                                           #
#   1. Round every X* under data/matrices/, comparing to the Hungarian        #
#      result already saved in those JSON files.                              #
#   2. If no saved matrices exist, run a synthetic sanity check:              #
#      generate an isomorphic graph pair, hand-craft a noisy doubly-          #
#      stochastic X*, and verify that hyperplane rounding recovers the        #
#      ground-truth permutation.                                              #
# --------------------------------------------------------------------------- #
def _demo_on_saved_matrices(data_dir: str = "data/matrices") -> bool:
    import glob
    import json
    import os

    if not os.path.isdir(data_dir):
        return False
    paths = sorted(glob.glob(os.path.join(data_dir, "*", "*.json")))
    if not paths:
        return False

    print(f"Found {len(paths)} saved X* matrices under {data_dir}/.")
    print("Comparing hyperplane rounding to the saved Hungarian-rounded result.\n")

    hungarian_iso = 0
    hyperplane_iso = 0
    hyperplane_only = 0
    hungarian_only = 0
    by_n: dict[int, dict[str, int]] = {}

    for path in paths:
        with open(path) as f:
            entry = json.load(f)
        X_star = np.asarray(entry["matrix"], dtype=float)
        A = np.asarray(entry["graph_a"]["adjacency"], dtype=int)
        B = np.asarray(entry["graph_b"]["adjacency"], dtype=int)
        n = A.shape[0]

        was_iso = bool(entry.get("is_isomorphic", False))
        _, stats = hyperplane_round(X_star, A, B, num_trials=200, seed=0)
        is_iso = stats["is_isomorphic"]

        hungarian_iso += int(was_iso)
        hyperplane_iso += int(is_iso)
        hyperplane_only += int(is_iso and not was_iso)
        hungarian_only += int(was_iso and not is_iso)

        bucket = by_n.setdefault(n, {"total": 0, "hungarian": 0, "hyperplane": 0})
        bucket["total"] += 1
        bucket["hungarian"] += int(was_iso)
        bucket["hyperplane"] += int(is_iso)

    print(f"  Hungarian rounding:  {hungarian_iso}/{len(paths)} pairs verified isomorphic")
    print(f"  Hyperplane rounding: {hyperplane_iso}/{len(paths)} pairs verified isomorphic")
    print(f"  Hyperplane-only wins: {hyperplane_only}")
    print(f"  Hungarian-only wins:  {hungarian_only}")
    print()
    print("Per-n breakdown:")
    for n in sorted(by_n):
        b = by_n[n]
        print(f"  n={n:3d}  total={b['total']:3d}  "
              f"hungarian={b['hungarian']:3d}  hyperplane={b['hyperplane']:3d}")
    return True


def _demo_synthetic() -> None:
    print("No saved matrices found - running a synthetic sanity check.\n")
    rng = np.random.default_rng(42)
    n = 8

    # Random graph A and a known permutation P_true; B = P_true^T A P_true.
    A = (rng.random((n, n)) < 0.4).astype(int)
    A = ((A + A.T) > 0).astype(int)
    np.fill_diagonal(A, 0)

    perm = rng.permutation(n)
    P_true = np.zeros((n, n), dtype=int)
    P_true[np.arange(n), perm] = 1
    B = P_true.T @ A @ P_true

    # Build a noisy doubly-stochastic X* close to P_true using Sinkhorn
    # normalisation of (P_true + uniform_noise).
    noise = rng.random((n, n)) * 0.1
    X = P_true.astype(float) + noise
    for _ in range(50):
        X = X / X.sum(axis=1, keepdims=True)
        X = X / X.sum(axis=0, keepdims=True)

    P_hat, stats = hyperplane_round(X, A, B, num_trials=200, seed=0)
    print(f"  Embedding rank   : {stats['embedding_rank']}")
    print(f"  # hyperplanes    : {stats['num_hyperplanes']}")
    print(f"  Trials run       : {stats['trials_run']} (best at trial {stats['best_trial']})")
    print(f"  Best residual    : {stats['best_residual']}  (0 == exact isomorphism)")
    print(f"  Is isomorphic    : {stats['is_isomorphic']}")
    print(f"  Recovered P_true : {bool(np.array_equal(P_hat, P_true))}")


if __name__ == "__main__":
    if not _demo_on_saved_matrices():
        _demo_synthetic()
