N_MIN = 5
N_MAX = 15
PAIRS = 5       # per type per n (5 iso + 5 non-iso)
LAMBDA_VAL = 0.1
REPORT_PATH = "isomorphism_report.html"

SOLVER_WEIGHTS = {
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
