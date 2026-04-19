import networkx as nx


def _non_identity_permutation(n, rng):
    perm = rng.permutation(n)
    if n > 1 and all(int(perm[i]) == i for i in range(n)):
        perm[[0, 1]] = perm[[1, 0]]
    return perm


def _sorted_adjacency_matrix(G):
    return nx.to_numpy_array(G, nodelist=sorted(G.nodes()))


def make_isomorphic_pair(n, rng):
    """Create an isomorphic pair whose solver-basis adjacency matrices are not identical."""
    p = min(0.3 + 10 / n, 0.7)
    if n <= 2:
        G1 = nx.erdos_renyi_graph(n, p, seed=int(rng.integers(1_000_000)))
        return G1, G1.copy()

    for _ in range(128):
        G1 = nx.erdos_renyi_graph(n, p, seed=int(rng.integers(1_000_000)))
        perm = _non_identity_permutation(n, rng)

        # Relabel onto a disjoint node set so the adjacency matrix basis is actually permuted.
        mapping = {i: int(n + perm[i]) for i in range(n)}
        G2 = nx.relabel_nodes(G1, mapping)

        if not (_sorted_adjacency_matrix(G1) == _sorted_adjacency_matrix(G2)).all():
            return G1, G2

    raise RuntimeError(f"Could not generate a non-identical isomorphic pair for n={n}")


def make_non_isomorphic_pair(n, rng):
    """Create two random graphs that are almost certainly non-isomorphic."""
    p1 = min(0.3 + 10 / n, 0.7)
    p2 = min(0.15 + 5 / n, 0.5)
    G1 = nx.erdos_renyi_graph(n, p1, seed=int(rng.integers(1_000_000)))
    G2 = nx.erdos_renyi_graph(n, p2, seed=int(rng.integers(1_000_000)))
    return G1, G2
