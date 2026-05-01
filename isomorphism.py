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
}


def _merge_solver_weights(solver_weights):
    merged = {
        "degree_profile": dict(DEFAULT_SOLVER_WEIGHTS["degree_profile"]),
    }
    if not solver_weights:
        return merged

    if "degree_profile" in solver_weights:
        merged["degree_profile"].update(solver_weights["degree_profile"])
    return merged


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

    objective = linear_part + adjacency_part

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
