# Graph Isomorphism Research Plan

This branch is for the next research cycle beyond the submission branch.
The goal is to turn the current relaxation-and-rounding prototype into a
serious experimental research codebase.

## Ground Rules

- A positive decision must always mean an exact certificate: `A @ P == P @ B`.
- A failed certificate is `not_certified`, not proof of non-isomorphism.
- VF2 is allowed as a reference label for experiments, not as part of our
method.
- Every claim must come from a reproducible script and saved JSON output.
- Separate model construction time, solver time, rounding time, and
verification time wherever possible.
- Dense random graphs are not enough. We need structured and adversarial graph
families.

## Phase 0: Experimental Infrastructure

Build one consistent experiment schema across all runners.

Required row fields:

- `experiment`
- `graph_family`
- `n`
- `density_a`
- `density_b`
- `seed`
- `pair`
- `vf2_isomorphic`
- `ours_certified_iso`
- `Z_star`
- `I`
- `objective_components`
- `rounding`
- `build_time_sec`
- `solve_time_sec`
- `rounding_time_sec`
- `total_time_sec`
- `error`

Artifacts:

- `results.jsonl` for raw runs.
- `summary.json` for aggregate metrics.
- `failures/` directory for failed isomorphic cases.
- `matrices/` for saved `X*`, `P`, `C`, residuals, and graph snapshots.
- plots generated from raw JSON, not manual spreadsheet edits.

Immediate scripts:

- keep `isomorphic_stress_test.py`;
- keep `random_density_confusion.py`;
- add a unified aggregator for all experiment outputs;
- add a plot generator for certification rate, confusion matrix, score
  separation, and runtime.

## Phase 1: Rounding War

The solver gives `X*`; the question is whether the rounding layer extracts the
right permutation.

Rounding methods to compare on the exact same saved `X*`:

- direct Hungarian on `1 - X*`;
- hyperplane rounding;
- multi-start hyperplane rounding with different seeds;
- noisy Hungarian: add small random perturbations to `1 - X*`, repeat, score by
  `||AP - PB||_F^2`;
- local repair after rounding: pairwise swaps that reduce integer residual.

Metrics:

- certificate rate on isomorphic pairs;
- false-positive count against VF2 on random pairs;
- best residual distribution;
- number of trials needed before first certificate;
- cases where Hungarian succeeds and hyperplane fails;
- cases where hyperplane succeeds and Hungarian fails;
- cases where local repair fixes either one.

Key question:

Does hyperplane rounding actually help, or is direct Hungarian enough for the
current objective?

Expected output:

- `rounding_comparison.py`
- `rounding_comparison_summary.json`
- plots for certificate rate by rounding method and `n`
- failure examples for each rounding method

## Phase 2: Objective Upgrades

The current objective is:

```text
<C, X> + ||AX - XB||_F^2
```

The next algorithmic improvements should attack weak identifiability.

### 2.1 WL Feature Cost

Add Weisfeiler-Lehman color-refinement features to `C`.

Plan:

- compute initial labels from degree;
- iteratively update labels using sorted neighbor-label multisets;
- compare label histories between vertices;
- define `C_wl[i,j]` as mismatch across WL rounds;
- normalize and combine with degree profile.

Ablations:

- adjacency only;
- degree cost + adjacency;
- WL cost + adjacency;
- degree + WL + adjacency.

Expected effect:

- better separation on regular and near-regular graph families;
- sharper `X*`;
- improved rounding success.

### 2.2 Higher-Order Walk Terms

Add:

```text
||A^2 X - X B^2||_F^2
||A^3 X - X B^3||_F^2
```

Start with `k=2` only.

Risks:

- higher-order powers become dense;
- term magnitudes scale differently;
- solve time may increase sharply.

Need normalization before claiming improvement.

### 2.3 Term Scaling

Normalize each objective component so that graph size does not decide the
relative importance of terms.

Track raw and normalized component values separately.

Candidate scaling:

- `C` divided by max absolute entry;
- adjacency residual divided by `max(1, ||A||_F^2 + ||B||_F^2)`;
- higher-order residual divided by corresponding matrix norms.

## Phase 3: Hard Graph Families

Dense random graphs often become easier as `n` grows because vertices become
more locally distinguishable. We need hard families.

Families to implement:

- cycles;
- paths;
- complete graphs;
- empty graphs;
- grids;
- random trees;
- random regular graphs;
- strongly regular graphs if available;
- disjoint unions of repeated components;
- cospectral or near-cospectral constructions;
- planted isomorphic versions of every family.

For each family:

- generate isomorphic pairs;
- generate non-isomorphic pairs;
- run VF2 reference;
- run our solver;
- save failure matrices.

Metrics:

- isomorphic certification rate;
- VF2-vs-ours confusion matrix;
- average entropy of `X*`;
- max row confidence of `X*`;
- objective component distributions;
- runtime.

## Phase 4: Failure Taxonomy

Every failed isomorphic case should be classified.

Failure categories:

- `diffuse_X`: rows/columns have no sharp assignment;
- `wrong_rounding`: `X*` is sharp-ish but rounding selects wrong permutation;
- `weak_features`: many vertices have same degree/WL profile;
- `symmetry`: automorphisms or repeated components;
- `timeout`: solver stopped before useful solution;
- `numerical`: row/column sums or precision issues.

Diagnostics to compute:

- row entropy of `X*`;
- column entropy of `X*`;
- max entry per row;
- gap between largest and second-largest row entry;
- residual of relaxed `X*`;
- residual of rounded `P`;
- objective components;
- automorphism hints from VF2/self-isomorphism for small cases.

Expected output:

- `failure_analysis.py`
- `failure_report.html`
- failure matrix viewer with `C`, `X*`, `P`, `AX-XB`, and graph snapshots.

## Phase 5: Solver Scaling

The current code has defensible `O(n^3)` expression construction for the
adjacency residual:

```text
(AX - XB)_{pq} = sum_k A_pk X_kq - X_pk B_kq
```

There are `n^2` residual entries and each has `n` terms.

Needed measurements:

- graph generation time;
- cost-matrix construction time;
- QP model construction time;
- Gurobi optimize time;
- rounding time;
- verification time;
- memory usage where possible.

Experiments:

- fixed density sweep over `n`;
- fixed `n` sweep over density;
- sparse vs dense;
- structured vs random.

Goal:

Identify whether the main bottleneck is Python expression construction, Gurobi
solve time, or rounding.

## Phase 6: Exactness on Graph Classes

This is the professor-driven question:

- Which graph classes make our formulation exact, or at least make false
  positives disappear?
- Can we prove that some families never certify non-isomorphic pairs?
- If a polynomial-time GI algorithm exists for a class, can our pipeline be
  made fully correct on that class by construction?

This phase is about exactness, not just better empirical performance.

### 6.1 Candidate Classes

Start with classes that have known exact GI algorithms or strong canonical
labeling structure:

- trees;
- rooted trees;
- paths and cycles;
- cographs;
- interval graphs;
- chordal graphs;
- complete graphs;
- empty graphs;
- planar 3-connected graphs;
- bounded-treewidth families;
- random regular graphs as a stress case, not an exactness candidate.

Also include the paper-driven class notion from Aflalo et al.:

- friendly graphs;
- graphs made friendly by extra seeds;
- graphs made friendly by extra vertex attributes.

### 6.2 What To Test

For each class, run:

- `vf2_isomorphic` label;
- our current QP + rounding pipeline;
- direct Hungarian baseline;
- hyperplane rounding;
- WL-augmented variants once implemented.

Measure:

- false positives on non-isomorphic pairs;
- false negatives on isomorphic pairs;
- whether `X*` becomes integral or nearly integral;
- whether rounding becomes deterministic or unstable;
- whether the score `I` becomes separated enough to prove anything useful.

Add two extra knobs inspired by the paper:

- a pseudostochastic relaxation variant with only linear equality constraints;
- seeded and attributed versions of the solver, where the extra information may
  break symmetries that currently confuse rounding.

### 6.3 Exactness Criteria

We need to distinguish three possibilities:

- `heuristic only`: the class still has false positives;
- `tight relaxation`: the class has a proof that the relaxation is exact;
- `certifiable via wrapper`: the generic solver is not exact alone, but a
  class-specific certification layer makes the full pipeline exact.

The most likely outcome is that we will need a wrapper or a class-specific
canonicalization layer.

Paper hypothesis to verify:

- if a graph class is friendly, the convex relaxation may become exact;
- if the class is not friendly, seeds or attributes may restore exactness;
- the simpler pseudostochastic relaxation may be enough on some families.

### 6.4 Research Questions

- For which classes does the objective landscape force `X*` close to a
  permutation?
- On which classes do false positives vanish even without extra features?
- Can we characterize a “friendly graph” subset that is large enough to be
  interesting and small enough to be provable?
- Can WL features or higher-order terms turn the generic relaxation into an
  exact method on some smaller class?

### 6.5 Deliverables

- `exactness_classes.py`
- `exactness_classes_summary.json`
- proof-oriented notes for candidate classes
- a table of classes versus:
  - false positives;
  - false negatives;
  - certification rate;
  - whether the relaxation appears tight;
  - whether a wrapper is required.

## Phase 7: Paper Translation Experiment

The Aflalo-Bronstein-Kimmel paper suggests three concrete research directions
that map directly to our code:

1. Friendly-graph detection.
   - Compute the spectral property used in the paper.
   - Test whether our current objective is exact on that subset.
   - Measure whether `X*` becomes integral or nearly integral.

2. Pseudostochastic relaxation.
   - Replace the doubly stochastic constraints with the paper's affine
     pseudostochastic variant.
   - Compare exactness, runtime, and ease of optimization.
   - Determine whether the simpler feasible set improves or hurts false
     positives.

3. Seeded / attributed matching.
   - Add known correspondences or vertex attributes.
   - Check whether extra information restores exactness on otherwise unfriendly
     graphs.
   - Measure how many seeds are needed before the solver becomes reliable.

## Phase 8: Proof-Driven Narrative

The next writeup should not just say “we tested more.”
It should answer the professor’s questions:

1. Where does the current formulation fail?
2. On which classes can we eliminate those failures?
3. Can a polynomial-time GI class be handled exactly by our framework?

The final story should be one of these:

- the generic relaxation is useful but not exact;
- exactness is recoverable on some classes with wrappers;
- WL/higher-order features push the exactness boundary further;
- or a proof emerges for a meaningful class where the relaxation is tight.

## Immediate Next Actions

1. Extract the friendly-graph condition from the paper into a testable helper.
2. Build the exactness-class experiment runner.
3. Implement tree, cograph, and interval-graph generators first.
4. Compare generic pipeline vs class-specific exact baseline.
5. Add a pseudostochastic relaxation branch.
6. Add seeded and attributed graph experiments.
7. Measure false positives and false negatives by class.
8. Add a notebook/report section summarizing which classes look promising for
   proofs.

## Immediate Next Actions

1. Run `random_density_confusion.py` overnight.
2. Run the isomorphic stress test to completion for small and medium sizes.
3. Implement direct Hungarian vs hyperplane comparison on saved `X*`.
4. Add WL feature cost behind a config flag.
5. Run ablation: adjacency-only vs degree vs WL vs degree+WL.
6. Add hard graph family generators.
7. Build the failure taxonomy report.
