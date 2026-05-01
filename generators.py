"""Graph-pair generators used by solver demos and experiments."""

from __future__ import annotations

import networkx as nx

DEFAULT_DENSITY_RANGE = (0.80, 0.85)


def _non_identity_permutation(n, rng):
    """Return a random permutation that changes at least one label when possible."""
    perm = rng.permutation(n)
    if n > 1 and all(int(perm[i]) == i for i in range(n)):
        perm[[0, 1]] = perm[[1, 0]]
    return perm


def _sorted_adjacency_matrix(G):
    """Adjacency matrix in the same sorted-node basis used by the solver."""
    return nx.to_numpy_array(G, nodelist=sorted(G.nodes()))


def _edge_count(n, rng, density_range):
    """Sample an edge count from an inclusive density interval."""
    d_min, d_max = density_range
    if not (0.0 <= d_min <= d_max <= 1.0):
        raise ValueError(f"density_range must satisfy 0 <= min <= max <= 1, got {density_range}")
    max_edges = n * (n - 1) // 2
    min_edges = int(round(d_min * max_edges))
    max_dense_edges = int(round(d_max * max_edges))
    if max_dense_edges < min_edges:
        max_dense_edges = min_edges
    return int(rng.integers(min_edges, max_dense_edges + 1))


def make_isomorphic_pair(n, rng, density_range=DEFAULT_DENSITY_RANGE):
    """Create an isomorphic graph pair.

    For ``n > 2`` the second graph is relabeled onto a disjoint node set, then
    both graphs are later converted through sorted-node adjacency matrices.
    This avoids the trivial case where the two solver-basis matrices are
    already identical.
    """
    if n <= 2:
        m = _edge_count(n, rng, density_range)
        G1 = nx.gnm_random_graph(n, m, seed=int(rng.integers(1_000_000)))
        return G1, G1.copy()

    for _ in range(128):
        m = _edge_count(n, rng, density_range)
        G1 = nx.gnm_random_graph(n, m, seed=int(rng.integers(1_000_000)))
        perm = _non_identity_permutation(n, rng)

        # Relabel onto a disjoint node set so the adjacency matrix basis is actually permuted.
        mapping = {i: int(n + perm[i]) for i in range(n)}
        G2 = nx.relabel_nodes(G1, mapping)

        if not (_sorted_adjacency_matrix(G1) == _sorted_adjacency_matrix(G2)).all():
            return G1, G2

    raise RuntimeError(f"Could not generate a non-identical isomorphic pair for n={n}")


def make_non_isomorphic_pair(n, rng, density_range=DEFAULT_DENSITY_RANGE):
    """Create two independently sampled graphs.

    The result is probabilistically, not constructively, non-isomorphic. Treat
    the label as an experiment label unless an independent certificate is added.
    """
    m1 = _edge_count(n, rng, density_range)
    m2 = _edge_count(n, rng, density_range)
    G1 = nx.gnm_random_graph(n, m1, seed=int(rng.integers(1_000_000)))
    G2 = nx.gnm_random_graph(n, m2, seed=int(rng.integers(1_000_000)))
    return G1, G2
