#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${ROOT_DIR}/.venv"

python3 -m venv "${VENV_DIR}"
source "${VENV_DIR}/bin/activate"

python -m pip install --upgrade pip
python -m pip install -r "${ROOT_DIR}/requirements.txt"

cat <<EOF

Setup complete.

Activate the environment with:
  source "${VENV_DIR}/bin/activate"

Then run the benchmark with:
  python big_benchmark.py

EOF
