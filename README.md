# Graph Isomorphism Benchmark

This repository contains a benchmarking suite for computing an "Isomorphism Index" between pairs of graphs. It generates varying sizes of both isomorphic and almost certainly non-isomorphic random graph pairs (using the Erdos-Renyi model) and formulates the graph isomorphism problem as a Quadratic Program (QP) that is then solved using the [Gurobi Optimizer](https://www.gurobi.com/).

The results of the benchmark are aggregated to produce a comprehensive HTML report with visualizations (using Chart.js) and a raw JSON file containing the timing and accuracy statistics.

## Project Structure

The project has been modularized into easy-to-maintain files:

- `main.py`: The entry point script that orchestrates the benchmarking process.
- `config.py`: Contains configurations such as minimum/maximum graph sizes, pairs to generate, and report paths.
- `isomorphism.py`: Contains the mathematical formulation of the isomorphism index and the Gurobi QP solver logic.
- `generators.py`: Contains functions to generate isomorphic and non-isomorphic graph pairs using `networkx`.
- `benchmark.py`: Runs the benchmark across the ranges defined in config and measures execution times and indices.
- `report.py`: Handles generating the rich HTML report and substituting benchmark data into it.
- `matrix_viewer.py`: Generates an interactive HTML viewer for visualizing the computed permutation matrices.

## Prerequisites

- Python 3.8+
- [Gurobi Optimizer](https://www.gurobi.com/downloads/gurobi-software/) and a valid license (academic or commercial)

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/harshitsinghbhandari/graph-isomorphism.git
   cd graph-isomorphism
   ```

2. Create a virtual environment (optional but recommended):
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
   ```

3. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```
   *(Ensure you have setup your Gurobi license prior to running the code. Refer to the [Gurobi documentation](https://support.gurobi.com/hc/en-us/articles/360040541131-How-do-I-set-up-a-Gurobi-license-) for more information).*

## Usage

You can adjust benchmarking parameters in `config.py`. By default, it benchmarks graph sizes from `N_MIN = 1` to `N_MAX = 25` with 5 isomorphic and 5 non-isomorphic pairs each.

Run the benchmark with:

```bash
python main.py
```

### Outputs

Upon completion, the script generates two files:
- `isomorphism_report.html`: A rich, interactive report displaying graphs of solve times, isomorphism indices, and objective values vs. graph node sizes.
- `comparison_report.html`: A detailed per-comparison diagnostics report showing graph `A`, graph `B`, `X*`, and ambiguity flags.
- `isomorphism_report.json`: The raw aggregated statistical data from the run.
- `data/matrices/{n}/*.json`: Individual matrix results for each graph pair, organized by node count.

Open the HTML report in your preferred web browser to view the benchmark results.

### Viewing Matrices

To visualize the computed permutation matrices, generate the matrix viewer:

```bash
python matrix_viewer.py
```

This creates `matrix_viewer.html`, a self-contained interactive viewer that lets you:
- Browse matrices organized by graph size (n)
- View graph `A`, graph `B`, and the final permutation matrix `X*` side by side
- See metadata including pair type, comparison result, isomorphism index `I`, and objective value `Z*`

Open `matrix_viewer.html` in your browser to explore the results.
