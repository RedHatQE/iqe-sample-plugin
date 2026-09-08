#!/usr/bin/env bash
# Build wheels for packages.json (or PACKAGE_SPEC) using the current Python.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WHEELS_DIR="${WHEELS_DIR:-${ROOT}/wheels}"
TARBALLS_DIR="${ROOT}/tarballs"
mkdir -p "${WHEELS_DIR}" "${TARBALLS_DIR}"
cd "${ROOT}"

PYTHON="${PYTHON:-python3}"

if [[ -n "${PACKAGE_SPEC:-}" ]]; then
  # shellcheck disable=SC2206
  packages=(${PACKAGE_SPEC})
else
  packages=()
  while IFS= read -r line; do
    [[ -n "${line}" ]] && packages+=("${line}")
  done <<< "$("${PYTHON}" -c "
import json
from pathlib import Path

data = json.loads(Path('packages.json').read_text())
seen = set()
for spec in data.get('packages', []) + data.get('pinned', []):
    if spec and spec not in seen:
        seen.add(spec)
        print(spec)
")"
fi

if [[ ${#packages[@]} -eq 0 ]]; then
  echo "no packages configured" >&2
  exit 1
fi

echo "Building with $("${PYTHON}" --version): ${packages[*]}"

failed=0
for package in "${packages[@]}"; do
  [[ -z "${package}" ]] && continue
  echo "=== ${package} ==="
  if ! (
    rm -rf "${TARBALLS_DIR}"
    mkdir -p "${TARBALLS_DIR}"
    "${PYTHON}" -m pip download --no-deps --no-binary :all: "${package}" -d "${TARBALLS_DIR}"

    archive="$(find "${TARBALLS_DIR}" -maxdepth 1 -type f \( -name '*.tar.gz' -o -name '*.zip' \) | head -n 1)"
    if [[ -z "${archive}" ]]; then
      echo "no sdist downloaded for ${package}" >&2
      exit 1
    fi

    src_dir="${TARBALLS_DIR}/src"
    mkdir -p "${src_dir}"
    if [[ "${archive}" == *.zip ]]; then
      unzip -q "${archive}" -d "${src_dir}"
    else
      tar -xf "${archive}" -C "${src_dir}"
    fi
    unpacked="$(find "${src_dir}" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
    (
      cd "${unpacked}"
      "${PYTHON}" -m build -w --outdir "${WHEELS_DIR}"
    )
  ); then
    echo "FAILED: ${package}" >&2
    failed=1
  fi
done

if ! compgen -G "${WHEELS_DIR}/*.whl" > /dev/null; then
  echo "no wheels produced in ${WHEELS_DIR}" >&2
  exit 1
fi

python3 "${ROOT}/scripts/validate_wheels.py" "${WHEELS_DIR}"

ls -l "${WHEELS_DIR}"
exit "${failed}"
