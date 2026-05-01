# Graph Isomorphism via Relaxation and Rounding

This repository contains the code and report material for a Phase 1 graph
isomorphism experiment.

The implemented method is:

1. Formulate graph isomorphism as the permutation condition `A P = P B`.
2. Relax the permutation matrix `P` to a doubly stochastic matrix `X`.
3. Solve a convex quadratic program over the Birkhoff polytope.
4. Round `X*` to a permutation candidate using hyperplane rounding.
5. Certify only by the exact integer check `A @ P == P @ B`.

The score `I = exp(-lambda * Z*)` is a similarity index. It is not used as a
proof. The only proof of isomorphism is a rounded permutation whose residual is
exactly zero.

## Core Files

- `isomorphism.py`: current source-of-truth solver.
- `hyperplane_rounding.py`: SVD embedding plus random-hyperplane rounding.
- `generators.py`: graph-pair generators used by experiments.
- `main.py`: clean entry point for tests, single-case runs, small comparisons,
  and matrix-viewer generation.
- `big_benchmark.py`: benchmark against VF2, nauty, and bliss.
- `matrix_viewer.py`: generates an HTML viewer from saved solver matrices.
- `report.tex`: final dense report draft for presentation.
- `theory.tex`: compact mathematical formulation.
- `failure.tex`: failure modes and limitations appendix.

Generated outputs such as `benchmark_data/`, `data/`, `compare_*`, HTML reports,
and matrix JSON files are intentionally ignored by git.

## Setup

Python 3.11+ is recommended. Gurobi must be installed with a valid license.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On the server used for these experiments, `gurobipy==12.0.3` is required because
the available license rejects Gurobi 13.

## Quick Runs

Open the interactive CLI:

```bash
python main.py
```

The same menu is available explicitly:

```bash
python main.py interactive
```

Run tests:

```bash
python main.py test
```

Run a single isomorphic test case and generate a matrix viewer:

```bash
python main.py single --n 101
```

Run a small comparison range:

```bash
python main.py compare --n-min 5 --n-max 30 --pairs 5
```

Run the larger benchmark:

```bash
python big_benchmark.py --sizes 50,60,70,80,90,100
```

Regenerate plots from existing run files:

```bash
python big_benchmark.py --plots-only
```

Generate a matrix viewer for an output directory:

```bash
python main.py viewer --base-dir benchmark_data/matrices --output benchmark_matrix_viewer.html --hide-graphs
```

Use `--hide-graphs` for large `n`; the graph drawings are not useful at 80+
nodes, while the permutation matrix remains readable.

## Current Limitations

- Non-isomorphic random pairs are sampled independently, so exact ground truth
  should be verified with VF2/nauty/bliss.
- The relaxation can return diffuse matrices on symmetric or weakly identifiable
  cases.
- Hyperplane rounding is heuristic. A failed certificate means "not certified",
  not a mathematical proof of non-isomorphism.
- The current Gurobi model builds the adjacency residual with nested loops and
  becomes expensive near 100+ nodes.
