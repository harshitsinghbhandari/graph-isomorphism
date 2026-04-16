import networkx as nx

def make_isomorphic_pair(n, rng):
    """Create a random graph and a relabeled (isomorphic) copy."""
    p = min(0.3 + 10 / n, 0.7)
    G1 = nx.erdos_renyi_graph(n, p, seed=int(rng.integers(1_000_000)))
    perm = rng.permutation(n)
    mapping = {i: int(perm[i]) for i in range(n)}
    G2 = nx.relabel_nodes(G1, mapping)
    return G1, G2

def make_non_isomorphic_pair(n, rng):
    """Create two random graphs that are almost certainly non-isomorphic."""
    p1 = min(0.3 + 10 / n, 0.7)
    p2 = min(0.15 + 5 / n, 0.5)
    G1 = nx.erdos_renyi_graph(n, p1, seed=int(rng.integers(1_000_000)))
    G2 = nx.erdos_renyi_graph(n, p2, seed=int(rng.integers(1_000_000)))
    return G1, G2
