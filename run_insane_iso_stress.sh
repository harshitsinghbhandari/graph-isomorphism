#!/usr/bin/env bash
set -euo pipefail

# Launch four fresh isomorphic-pair stress-test shards in parallel.
#
# Default workload:
#   shard_08_12 : n = 8,9,10,11,12   with 2500 pairs per n
#   shard_15_20 : n = 15,20          with 2500 pairs per n
#   shard_25    : n = 25             with 2500 pairs
#   shard_30    : n = 30             with 2500 pairs
#
# Usage:
#   bash run_insane_iso_stress.sh
#   PAIRS=100 bash run_insane_iso_stress.sh smoke_iso_stress

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${ROOT_DIR}"

OUT_DIR="${1:-insane_iso_stress}"
PAIRS="${PAIRS:-2500}"
DENSITY_MIN="${DENSITY_MIN:-0.80}"
DENSITY_MAX="${DENSITY_MAX:-0.85}"

if [[ -x "venv/bin/python" ]]; then
  PYTHON_BIN="${PYTHON_BIN:-venv/bin/python}"
elif [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"
else
  PYTHON_BIN="${PYTHON_BIN:-python3}"
fi

mkdir -p "${OUT_DIR}/logs"

start_shard() {
  local name="$1"
  local sizes="$2"
  local seed="$3"
  local shard_dir="${OUT_DIR}/${name}"
  local log_path="${OUT_DIR}/logs/${name}.log"

  rm -rf "${shard_dir}"
  mkdir -p "${shard_dir}"
  nohup "${PYTHON_BIN}" isomorphic_stress_test.py \
    --sizes "${sizes}" \
    --pairs "${PAIRS}" \
    --seed "${seed}" \
    --density-min "${DENSITY_MIN}" \
    --density-max "${DENSITY_MAX}" \
    --output-dir "${shard_dir}" \
    > "${log_path}" 2>&1 &

  local pid="$!"
  echo "${pid}" > "${OUT_DIR}/logs/${name}.pid"
  printf '%-12s pid=%-8s sizes=%-14s log=%s\n' "${name}" "${pid}" "${sizes}" "${log_path}"
}

echo "Launching insane isomorphic stress test"
echo "Output dir : ${OUT_DIR}"
echo "Python     : ${PYTHON_BIN}"
echo "Pairs/n    : ${PAIRS}"
echo "Density    : [${DENSITY_MIN}, ${DENSITY_MAX}]"
echo

start_shard "shard_08_12" "8,9,10,11,12" "81012"
start_shard "shard_15_20" "15,20" "1520"
start_shard "shard_25" "25" "25"
start_shard "shard_30" "30" "30"

cat <<EOF

Started 4 parallel shards.

Monitor:
  tail -f ${OUT_DIR}/logs/shard_08_12.log
  tail -f ${OUT_DIR}/logs/shard_15_20.log
  tail -f ${OUT_DIR}/logs/shard_25.log
  tail -f ${OUT_DIR}/logs/shard_30.log

Count completed rows:
  find ${OUT_DIR} -name results.jsonl -exec wc -l {} +

Aggregate after/during run:
  ${PYTHON_BIN} aggregate_isomorphic_stress.py --root ${OUT_DIR}

Stop all four:
  kill \$(cat ${OUT_DIR}/logs/*.pid)

Rerunning this script starts fresh and overwrites each shard directory.
EOF
