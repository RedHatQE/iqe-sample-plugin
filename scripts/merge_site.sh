#!/usr/bin/env bash
# Merge validated wheels into a GitHub Pages site directory.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PREVIOUS_SITE="${1:?previous site directory}"
NEW_WHEELS="${2:?new wheels directory}"
SITE_DIR="${3:?output site directory}"
SIMPLE_URL="${4:?simple index URL}"

mkdir -p "${SITE_DIR}/packages"
shopt -s nullglob

copy_valid_wheels() {
  local source_dir="$1"
  local label="$2"
  for wheel in "${source_dir}"/*.whl; do
    if python3 "${ROOT}/scripts/validate_wheels.py" "${wheel}" > /dev/null; then
      cp -a "${wheel}" "${SITE_DIR}/packages/"
      echo "kept ${label}: $(basename "${wheel}")"
    else
      echo "skipped corrupt ${label}: $(basename "${wheel}")" >&2
    fi
  done
}

if [[ -d "${PREVIOUS_SITE}/packages" ]]; then
  copy_valid_wheels "${PREVIOUS_SITE}/packages" "existing"
fi
copy_valid_wheels "${NEW_WHEELS}" "new"

python3 "${ROOT}/scripts/validate_wheels.py" "${SITE_DIR}/packages"
python3 "${ROOT}/scripts/generate_index.py" "${SITE_DIR}" --simple-url "${SIMPLE_URL}"
