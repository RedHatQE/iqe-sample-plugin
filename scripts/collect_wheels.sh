#!/usr/bin/env bash
# Flatten artifact trees and dedupe wheels by filename.
#
# gssapi >=1.11 builds cp311-abi3 manylinux wheels with the same filename from
# every Python matrix job. GitHub's merge-multiple artifact download corrupts
# those duplicates, so we download artifacts separately and merge here.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="${1:?artifact root directory}"
DEST="${2:?output directory}"

mkdir -p "${DEST}"
shopt -s nullglob

if ! find "${SRC}" -type f -name '*.whl' | grep -q .; then
  echo "no wheels found under ${SRC}" >&2
  exit 1
fi

while IFS= read -r wheel; do
  [[ -z "${wheel}" ]] && continue
  base="$(basename "${wheel}")"
  if python3 "${ROOT}/scripts/validate_wheels.py" "${wheel}" > /dev/null; then
    cp -a "${wheel}" "${DEST}/${base}"
    echo "collected ${base}"
  else
    echo "skipped invalid wheel: ${wheel}" >&2
  fi
done < <(find "${SRC}" -type f -name '*.whl' | sort)

if ! compgen -G "${DEST}/*.whl" > /dev/null; then
  echo "no valid wheels collected in ${DEST}" >&2
  exit 1
fi

python3 "${ROOT}/scripts/validate_wheels.py" "${DEST}"
echo "collected $(find "${DEST}" -maxdepth 1 -name '*.whl' | wc -l) unique wheel(s) into ${DEST}"
