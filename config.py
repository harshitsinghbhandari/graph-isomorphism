N_MIN = 5
N_MAX = 15
PAIRS = 5       # per type per n (5 iso + 5 non-iso)
LAMBDA_VAL = 0.1
REPORT_PATH = "isomorphism_report.html"

# Edge density range as a fraction of the maximum possible edges n*(n-1)/2.
# Each generated graph picks a density uniformly in [DENSITY_MIN, DENSITY_MAX].
DENSITY_MIN = 0.45
DENSITY_MAX = 0.85

SOLVER_WEIGHTS = {
    "degree_profile": {
        "degree": 1.0,
        "neighbor_degree": 0.35,
    },
}
