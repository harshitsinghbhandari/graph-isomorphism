"""Relaxed graph-isomorphism solver.

The implemented pipeline is intentionally small and code-grounded:

1. Build adjacency matrices ``A`` and ``B`` in sorted-node order.
2. Solve a convex quadratic program over the Birkhoff polytope.
3. Round the relaxed doubly stochastic matrix ``X_star`` into a permutation.
4. Certify only by the exact integer identity ``A @ P == P @ B``.

The scalar isomorphism index ``I = exp(-lambda * Z_star)`` is a similarity
score, not a decision rule.  The decision returned by this module comes from
the rounded permutation certificate.
"""

from __future__ import annotations

import json
import os
import uuid
from typing import Any

import gurobipy as gp
from gurobipy import GRB
import networkx as nx
import numpy as np

from hyperplane_rounding import hyperplane_round


DEFAULT_SOLVER_WEIGHTS = {
    "degree_profile": {
        "degree": 1.0,
        "neighbor_degree": 0.35,
    },
    "objective": {
        "degree_profile_scale": 1.0,
        "adjacency_scale": 1.0,
    },
}


def _merge_solver_weights(solver_weights: dict[str, Any] | None) -> dict[str, Any]:
    """Merge caller-supplied weight overrides with stable defaults."""
    merged = {
        "degree_profile": dict(DEFAULT_SOLVER_WEIGHTS["degree_profile"]),
        "objective": dict(DEFAULT_SOLVER_WEIGHTS["objective"]),
    }
    if not solver_weights:
        return merged

    if "degree_profile" in solver_weights:
        merged["degree_profile"].update(solver_weights["degree_profile"])
    if "objective" in solver_weights:
        merged["objective"].update(solver_weights["objective"])
    return merged


def _degree_cost_matrix(
    A: np.ndarray,
    B: np.ndarray,
    degree_weight: float,
    neighbor_degree_weight: float,
) -> np.ndarray:
    """Node-pair mismatch cost from degree and one-hop degree summaries."""
    degA = np.sum(A, axis=1)
    degB = np.sum(B, axis=1)
    neighbor_degA = A @ degA
    neighbor_degB = B @ degB
    return (
        degree_weight * np.abs(degA[:, None] - degB[None, :]) +
        neighbor_degree_weight * np.abs(neighbor_degA[:, None] - neighbor_degB[None, :])
    )


def _normalize_cost_matrix(C: np.ndarray) -> np.ndarray:
    """Scale ``C`` to [0, 1]-like magnitude so it competes with the QP term."""
    max_abs = float(np.max(np.abs(C))) if C.size else 0.0
    if max_abs <= 0.0:
        return C
    return C / max_abs


def _adjacency_residual_sq(A: np.ndarray, B: np.ndarray, X: np.ndarray) -> float:
    """Return ``||A X - X B||_F^2`` for diagnostics."""
    residual = A @ X - X @ B
    return float(np.sum(residual * residual))


def _adjacency_matrix_for_solver(G: nx.Graph) -> np.ndarray:
    """Use a deterministic node order for every graph-to-matrix conversion."""
    return nx.to_numpy_array(G, nodelist=sorted(G.nodes()))


def _serialize_graph(G: nx.Graph) -> dict[str, Any]:
    """Serialize graph data for the matrix viewer and debugging artifacts."""
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
    G1: nx.Graph,
    G2: nx.Graph,
    lambda_val: float = 0.1,
    base_dir: str = "data/matrices",
    solver_weights: dict[str, Any] | None = None,
    comparison_type: str | None = None,
) -> tuple[float | None, float | None, bool | None]:
    """Solve the relaxed GI objective and certify a rounded permutation.

    Objective
    ---------
    ``min_X degree_scale * <C, X> + adjacency_scale * ||A X - X B||_F^2``
    subject to ``X`` being doubly stochastic.

    ``C`` is a normalized degree-profile mismatch matrix.  The quadratic
    adjacency term is convex because it is the squared norm of a linear map in
    ``X``.

    Returns
    -------
    ``(Z_star, I, is_isomorphic)``.  ``is_isomorphic`` is true only when the
    rounded permutation satisfies ``A @ P_star == P_star @ B`` exactly.
    """
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
    C = _normalize_cost_matrix(C)
    objective_weights = weights["objective"]
    model = gp.Model("IsomorphismIndex")
    model.setParam("OutputFlag", 0)
    model.setParam("TimeLimit", 120)

    X = model.addVars(n, n, lb=0.0, ub=1.0, vtype=GRB.CONTINUOUS, name="X")

    for i in range(n):
        model.addConstr(gp.quicksum(X[i, j] for j in range(n)) == 1)
    for j in range(n):
        model.addConstr(gp.quicksum(X[i, j] for i in range(n)) == 1)

    linear_part = objective_weights["degree_profile_scale"] * gp.quicksum(
        C[i, j] * X[i, j] for i in range(n) for j in range(n)
    )

    adjacency_part = 0
    for p in range(n):
        for q in range(n):
            diff_expr = gp.quicksum(
                A[p, k] * X[k, q] - X[p, k] * B[k, q] for k in range(n)
            )
            adjacency_part += diff_expr * diff_expr
    adjacency_part *= objective_weights["adjacency_scale"]

    objective = linear_part + adjacency_part

    model.setObjective(objective, GRB.MINIMIZE)
    model.optimize()

    if model.status not in (GRB.OPTIMAL, GRB.TIME_LIMIT):
        return None, None, None

    # Keep full solver precision for rounding. Decimal rounding here changes
    # the geometry of X* and can break otherwise valid row/column sums.
    X_star = np.array([[X[i, j].X for j in range(n)] for i in range(n)])
    X_star = np.clip(X_star, 0.0, 1.0)
    Z_star = model.objVal
    I = np.exp(-lambda_val * Z_star)

    # Rounding is heuristic; the exact certificate is the AP = PB check below.
    P_star, rounding_stats = hyperplane_round(X_star, A, B, num_trials=200, seed=0)
    is_isomorphic = bool(np.array_equal(A @ P_star, P_star @ B))
    linear_value = objective_weights["degree_profile_scale"] * float(np.sum(C * X_star))
    adjacency_value = objective_weights["adjacency_scale"] * _adjacency_residual_sq(A, B, X_star)

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
        "objective_components": {
            "degree_profile": linear_value,
            "adjacency": adjacency_value,
        },
        "rounding": rounding_stats,
        "graph_a": _serialize_graph(G1),
        "graph_b": _serialize_graph(G2),
        "weights": weights,
    }
    if comparison_type:
        result_entry["comparison_type"] = comparison_type

    with open(file_path, "w") as f:
        json.dump(result_entry, f, indent=4)

    return Z_star, I, is_isomorphic
