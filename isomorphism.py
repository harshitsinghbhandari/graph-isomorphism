import gurobipy as gp
from gurobipy import GRB
import numpy as np
import networkx as nx
from scipy.optimize import linear_sum_assignment
import json
import uuid
import os

DEFAULT_SOLVER_WEIGHTS = {
    "degree_profile": {
        "degree": 1.0,
        "neighbor_degree": 0.35,
    },
    "commutator_powers": {
        2: 0.20,
        3: 0.10,
        4: 0.05,
        5: 0.025,
        6: 0.012,
    },
    "spectral": 0.15,
}


def _merge_solver_weights(solver_weights):
    merged = {
        "degree_profile": dict(DEFAULT_SOLVER_WEIGHTS["degree_profile"]),
        "commutator_powers": dict(DEFAULT_SOLVER_WEIGHTS["commutator_powers"]),
        "spectral": DEFAULT_SOLVER_WEIGHTS["spectral"],
    }
    if not solver_weights:
        return merged

    if "degree_profile" in solver_weights:
        merged["degree_profile"].update(solver_weights["degree_profile"])
    if "commutator_powers" in solver_weights:
        merged["commutator_powers"].update(solver_weights["commutator_powers"])
    # backward compat: old "two_hop" key maps to commutator_powers[2]
    if "two_hop" in solver_weights and "commutator_powers" not in solver_weights:
        merged["commutator_powers"] = {2: solver_weights["two_hop"]}
    if "spectral" in solver_weights:
        merged["spectral"] = solver_weights["spectral"]
    return merged


def _eigenspace_projectors(adj, degeneracy_tol=1e-6):
    """Compute eigenspace projection operators for the graph Laplacian.

    Returns a list of (projector, weight) tuples, one per eigenvalue cluster.
    This is invariant to rotations within degenerate eigenspaces, fixing the
    eigenvector sign/basis ambiguity problem.
    """
    degrees = np.sum(adj, axis=1)
    laplacian = np.diag(degrees) - adj
    eigenvalues, eigenvectors = np.linalg.eigh(laplacian)

    projectors = []
    i = 0
    n = len(eigenvalues)
    while i < n:
        j = i + 1
        while j < n and abs(eigenvalues[j] - eigenvalues[i]) < degeneracy_tol:
            j += 1
        U_cluster = eigenvectors[:, i:j]
        Pi = U_cluster @ U_cluster.T
        weight = abs(np.mean(eigenvalues[i:j]))
        if weight > 1e-10:  # skip trivial zero-eigenvalue eigenspace
            projectors.append((Pi, weight))
        i = j

    return projectors


def _degree_cost_matrix(A, B, degree_weight, neighbor_degree_weight):
    degA = np.sum(A, axis=1)
    degB = np.sum(B, axis=1)
    neighbor_degA = A @ degA
    neighbor_degB = B @ degB
    return (
        degree_weight * np.abs(degA[:, None] - degB[None, :]) +
        neighbor_degree_weight * np.abs(neighbor_degA[:, None] - neighbor_degB[None, :])
    )


def _hungarian_round(X_star):
    """Round a doubly-stochastic matrix to the nearest permutation matrix."""
    row_ind, col_ind = linear_sum_assignment(1.0 - X_star)
    n = X_star.shape[0]
    P = np.zeros((n, n), dtype=int)
    P[row_ind, col_ind] = 1
    return P


def _integer_verify(A, B, P):
    """Check AP == PB exactly in integer arithmetic."""
    A_int = A.astype(np.int64)
    B_int = B.astype(np.int64)
    P_int = P.astype(np.int64)
    residual = A_int @ P_int - P_int @ B_int
    return bool(np.all(residual == 0))


def _adjacency_matrix_for_solver(G):
    return nx.to_numpy_array(G, nodelist=sorted(G.nodes()))


def _serialize_graph(G):
    node_order = sorted(G.nodes())
    layout = nx.circular_layout(node_order)

    return {
        "nodes": [
            {
                "id": int(node),
                "x": float(layout[node][0]),
                "y": float(layout[node][1]),
            }
            for node in node_order
        ],
        "edges": [
            {"source": int(u), "target": int(v)}
            for u, v in sorted(G.edges())
        ],
        "adjacency": _adjacency_matrix_for_solver(G).astype(int).tolist(),
    }


def compute_isomorphism_index(
    G1,
    G2,
    lambda_val=0.1,
    base_dir="data/matrices",
    solver_weights=None,
    comparison_type=None,
):
    n = G1.number_of_nodes()
    if n != G2.number_of_nodes():
        raise ValueError("Both graphs must have the same number of nodes.")

    A = _adjacency_matrix_for_solver(G1)
    B = _adjacency_matrix_for_solver(G2)
    weights = _merge_solver_weights(solver_weights)
    degree_weights = weights["degree_profile"]
    C = _degree_cost_matrix(
        A,
        B,
        degree_weights["degree"],
        degree_weights["neighbor_degree"],
    )
    # Precompute matrix powers for commutator terms
    commutator_powers = weights["commutator_powers"]
    max_k = max(commutator_powers.keys()) if commutator_powers else 1
    A_powers = {1: A}
    B_powers = {1: B}
    for k in range(2, max_k + 1):
        A_powers[k] = A_powers[k - 1] @ A
        B_powers[k] = B_powers[k - 1] @ B

    # Grassmannian eigenspace projectors (rotation-invariant spectral term)
    projectors_A = _eigenspace_projectors(A)
    projectors_B = _eigenspace_projectors(B)

    model = gp.Model("IsomorphismIndex")
    model.setParam('OutputFlag', 0)
    model.setParam('TimeLimit', 120)

    X = model.addVars(n, n, lb=0.0, ub=1.0, vtype=GRB.CONTINUOUS, name="X")

    for i in range(n):
        model.addConstr(gp.quicksum(X[i, j] for j in range(n)) == 1)
    for j in range(n):
        model.addConstr(gp.quicksum(X[i, j] for i in range(n)) == 1)

    linear_part = gp.quicksum(C[i, j] * X[i, j] for i in range(n) for j in range(n))

    adjacency_part = 0
    for p in range(n):
        for q in range(n):
            diff_expr = gp.quicksum(A[p, k] * X[k, q] - X[p, k] * B[k, q] for k in range(n))
            adjacency_part += diff_expr * diff_expr

    # Higher-order commutator terms: ||A^k X - X B^k||_F^2 for k=2..K
    commutator_part = 0
    for k, w_k in commutator_powers.items():
        if w_k:
            Ak = A_powers[k]
            Bk = B_powers[k]
            for p in range(n):
                for q in range(n):
                    diff_expr = gp.quicksum(Ak[p, m] * X[m, q] - X[p, m] * Bk[m, q] for m in range(n))
                    commutator_part += w_k * diff_expr * diff_expr

    # Grassmannian eigenspace alignment: ||Pi_A X - X Pi_B||_F^2
    grassmannian_part = 0
    if weights["spectral"]:
        n_clusters = min(len(projectors_A), len(projectors_B))
        for l in range(n_clusters):
            Pi_A, w_A = projectors_A[l]
            Pi_B, w_B = projectors_B[l]
            w_l = (w_A + w_B) / 2.0
            for p in range(n):
                for q in range(n):
                    diff_expr = gp.quicksum(
                        Pi_A[p, m] * X[m, q] - X[p, m] * Pi_B[m, q]
                        for m in range(n)
                    )
                    grassmannian_part += w_l * diff_expr * diff_expr

    objective = linear_part + adjacency_part
    objective += commutator_part
    objective += weights["spectral"] * grassmannian_part

    model.setObjective(objective, GRB.MINIMIZE)
    model.optimize()

    if model.status not in (GRB.OPTIMAL, GRB.TIME_LIMIT):
        return None, None, None

    # Extract solution
    X_star = np.array([[round(X[i, j].X, 4) for j in range(n)] for i in range(n)])
    Z_star = model.objVal
    I = np.exp(-lambda_val * Z_star)

    # Hungarian rounding + integer verification (Fix 1 from failure.tex)
    P_star = _hungarian_round(X_star)
    is_isomorphic = _integer_verify(A, B, P_star)

    # --- Save to structured path ---
    entry_id = str(uuid.uuid4())
    dir_path = os.path.join(base_dir, str(n))
    os.makedirs(dir_path, exist_ok=True)

    file_path = os.path.join(dir_path, f"{entry_id}.json")

    result_entry = {
        "Z_star": Z_star,
        "I": I,
        "is_isomorphic": is_isomorphic,
        "matrix": X_star.tolist(),
        "permutation": P_star.tolist(),
        "graph_a": _serialize_graph(G1),
        "graph_b": _serialize_graph(G2),
        "weights": weights,
    }
    if comparison_type:
        result_entry["comparison_type"] = comparison_type

    with open(file_path, "w") as f:
        json.dump(result_entry, f, indent=4)

    return Z_star, I, is_isomorphic
