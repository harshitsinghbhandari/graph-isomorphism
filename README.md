# Graph Isomorphism via Continuous Relaxation and Hyperplane Rounding

This repository contains the code, report, figures, and experiment scripts for
the IE210 graph isomorphism project.

The implemented pipeline is:

1. Express graph isomorphism as the permutation condition `A P = P B`.
2. Relax the permutation matrix `P` to a doubly stochastic matrix `X` over the
   Birkhoff polytope.
3. Solve a convex quadratic program with a degree-profile cost and adjacency
   commutator term.
4. Round the relaxed matrix `X*` using SVD embeddings and random-hyperplane
   signatures.
5. Accept isomorphism only when the rounded permutation passes the exact
   integer check `A @ P == P @ B`.

The score `I = exp(-lambda * Z*)` is a similarity index. It is not a proof.
The only positive certificate is the exact `A @ P == P @ B` check.

## Repository Contents

- `report.tex`: final project report source.
- `theory.tex`: detailed theory note, especially the Max-Cut-inspired
  hyperplane rounding adaptation.
- `failure.tex`: limitations and failure modes.
- `figures/`: generated report figures used by `report.tex`.
- `isomorphism.py`: source-of-truth relaxed QP solver.
- `hyperplane_rounding.py`: SVD embedding and random-hyperplane rounding.
- `generators.py`: graph-pair generators.
- `main.py`: interactive CLI and small experiment entry point.
- `matrix_viewer.py`: HTML viewer for saved permutation matrices.
- `relaxed_matrix_viewer.py`: side-by-side HTML viewer for relaxed `X*` and
  rounded `P`.
- `relaxed_matrix_viewer.html`: generated standalone viewer artifact.
- `generate_report_figures.py`: regenerates the report figures from saved data.
- `isomorphic_stress_test.py`: certification-rate test on generated isomorphic
  pairs.
- `random_density_confusion.py`: VF2-vs-ours confusion matrix on random-density
  graph pairs.
- `random_vf2_comparison.py`: random-pair VF2 comparison helper.
- `run_insane_iso_stress.sh`: four-shard isomorphic stress-test launcher.
- `run_insane_random_vf2.sh`: four-shard random/VF2 comparison launcher.
- `aggregate_isomorphic_stress.py`: aggregates isomorphic stress-test shards.
- `aggregate_random_vf2.py`: aggregates random/VF2 comparison shards.

Generated experiment outputs such as `data/`, `large/`,
`isomorphic_stress_results/`, `insane_iso_stress/`,
`random_density_confusion_results/`, and matrix JSON directories are ignored by
git.

## Setup

Python 3.11+ is recommended. Gurobi must be installed with a valid license.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On the project server, `gurobipy==12.0.3` was used because the available license
rejected Gurobi 13.

## Quick Commands

Open the interactive CLI:

```bash
python main.py
```

Run unit tests:

```bash
python main.py test
```

Run one generated isomorphic case:

```bash
python main.py single --n 101
```

Run a small experiment:

```bash
python main.py experiment --n-min 5 --n-max 30 --pairs 5
```

Build the standard matrix viewer:

```bash
python main.py viewer --base-dir data/matrices --output matrix_viewer.html --hide-graphs
```

Build the relaxed-vs-rounded viewer:

```bash
python relaxed_matrix_viewer.py --base-dir data/matrices --output relaxed_matrix_viewer.html
```

Regenerate report figures:

```bash
python generate_report_figures.py
```

## Larger Experiments

Run isomorphic certification stress test:

```bash
python isomorphic_stress_test.py --sizes 10,11,12 --pairs 300
```

Run four parallel isomorphic stress shards:

```bash
bash run_insane_iso_stress.sh
```

Aggregate isomorphic stress results:

```bash
python aggregate_isomorphic_stress.py --root insane_iso_stress
```

Run random-density VF2-vs-ours confusion experiment:

```bash
python random_density_confusion.py
```

Run four parallel random/VF2 shards:

```bash
bash run_insane_random_vf2.sh
```

Aggregate random/VF2 shards:

```bash
python aggregate_random_vf2.py --root insane_random_vf2
```

## Report Notes

`report.tex` expects the generated `figures/` directory. It also references
`ahu.jpeg` and `planar.png`; those files were provided separately in Overleaf
for the final report compilation.

## Limitations

- A failed certificate means `not_certified`, not proof of non-isomorphism.
- Dense random graphs become easier at larger `n`; structured hard graph
  families are needed for deeper evaluation.
- Hyperplane rounding is heuristic and has no Max-Cut-style approximation
  guarantee for graph isomorphism.
- The QP model construction has `O(n^3)` expression-building work for the
  adjacency commutator, and solve time is solver-dependent.

