import networkx as nx

DENSE_RATIO_MIN = 0.80
DENSE_RATIO_MAX = 0.85


def _non_identity_permutation(n, rng):
    perm = rng.permutation(n)
    if n > 1 and all(int(perm[i]) == i for i in range(n)):
        perm[[0, 1]] = perm[[1, 0]]
    return perm


def _sorted_adjacency_matrix(G):
    return nx.to_numpy_array(G, nodelist=sorted(G.nodes()))


def _dense_edge_count(n, rng):
    max_edges = n * (n - 1) // 2
    min_edges = int(round(DENSE_RATIO_MIN * max_edges))
    max_dense_edges = int(round(DENSE_RATIO_MAX * max_edges))
    return int(rng.integers(min_edges, max_dense_edges + 1))


def make_isomorphic_pair(n, rng):
    """Create an isomorphic pair whose solver-basis adjacency matrices are not identical."""
    if n <= 2:
        m = _dense_edge_count(n, rng)
        G1 = nx.gnm_random_graph(n, m, seed=int(rng.integers(1_000_000)))
        return G1, G1.copy()

    for _ in range(128):
        m = _dense_edge_count(n, rng)
        G1 = nx.gnm_random_graph(n, m, seed=int(rng.integers(1_000_000)))
        perm = _non_identity_permutation(n, rng)

        # Relabel onto a disjoint node set so the adjacency matrix basis is actually permuted.
        mapping = {i: int(n + perm[i]) for i in range(n)}
        G2 = nx.relabel_nodes(G1, mapping)

        if not (_sorted_adjacency_matrix(G1) == _sorted_adjacency_matrix(G2)).all():
            return G1, G2

    raise RuntimeError(f"Could not generate a non-identical isomorphic pair for n={n}")


def make_non_isomorphic_pair(n, rng):
    """Create two random graphs that are almost certainly non-isomorphic."""
    m1 = _dense_edge_count(n, rng)
    m2 = _dense_edge_count(n, rng)
    G1 = nx.gnm_random_graph(n, m1, seed=int(rng.integers(1_000_000)))
    G2 = nx.gnm_random_graph(n, m2, seed=int(rng.integers(1_000_000)))
    return G1, G2
