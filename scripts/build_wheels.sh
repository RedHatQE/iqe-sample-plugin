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
  # Extract both 'packages' and 'pinned' keys and remove duplicates
  while IFS= read -r line; do
    [[ -n "${line}" ]] && packages+=("${line}")
  done <<< "$("${PYTHON}" -c "import json; d=json.load(open('packages.json')); pkgs = d.get('packages', []) + d.get('pinned', []); print('\n'.join(pkgs))" | sort -u)"
fi

echo "Building with $("${PYTHON}" --version): ${packages[*]}"

for package in "${packages[@]}"; do
  [[ -z "${package}" ]] && continue
  echo "=== ${package} ==="
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
done

ls -l "${WHEELS_DIR}"
