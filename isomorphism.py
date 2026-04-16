import gurobipy as gp
from gurobipy import GRB
import numpy as np
import networkx as nx

def compute_isomorphism_index(G1, G2, lambda_val=0.1):
    n = G1.number_of_nodes()
    if n != G2.number_of_nodes():
        raise ValueError("Both graphs must have the same number of nodes.")

    A = nx.to_numpy_array(G1)
    B = nx.to_numpy_array(G2)

    degA = np.sum(A, axis=1)
    degB = np.sum(B, axis=1)
    C = np.abs(degA[:, None] - degB[None, :])

    model = gp.Model("IsomorphismIndex")
    model.setParam('OutputFlag', 0)
    model.setParam('TimeLimit', 120)

    X = model.addVars(n, n, lb=0.0, ub=1.0, vtype=GRB.CONTINUOUS, name="X")

    for i in range(n):
        model.addConstr(gp.quicksum(X[i, j] for j in range(n)) == 1)
    for j in range(n):
        model.addConstr(gp.quicksum(X[i, j] for i in range(n)) == 1)

    linear_part = gp.quicksum(C[i, j] * X[i, j] for i in range(n) for j in range(n))

    quadratic_part = 0
    for p in range(n):
        for q in range(n):
            diff_expr = gp.quicksum(A[p, k] * X[k, q] - X[p, k] * B[k, q] for k in range(n))
            quadratic_part += diff_expr * diff_expr

    model.setObjective(linear_part + quadratic_part, GRB.MINIMIZE)
    model.optimize()

    if model.status not in (GRB.OPTIMAL, GRB.TIME_LIMIT):
        return None, None

    Z_star = model.objVal
    I = np.exp(-lambda_val * Z_star)
    return Z_star, I
