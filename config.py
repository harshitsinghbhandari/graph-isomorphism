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
}
