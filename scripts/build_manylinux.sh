#!/usr/bin/env bash
# Run inside quay.io/pypa/manylinux_2_28_x86_64 with the repo mounted at /io.
set -euo pipefail

ROOT="${ROOT:-/io}"
PYTHON_VERSION="${PYTHON_VERSION:?PYTHON_VERSION is required (e.g. 3.12)}"
PY_TAG="cp${PYTHON_VERSION//./}"
PYBIN="/opt/python/${PY_TAG}-${PY_TAG}/bin"

if [[ ! -x "${PYBIN}/python" ]]; then
  echo "CPython ${PYTHON_VERSION} (${PY_TAG}) is not in this manylinux image:" >&2
  ls /opt/python >&2
  exit 1
fi

export PATH="${PYBIN}:${PATH}"
export PYTHON="${PYBIN}/python"
export WHEELS_DIR="${ROOT}/wheels"
RAW_WHEELS="${ROOT}/raw-wheels"

# Runtime images already ship krb5/openssl; keep them out of the wheel so
# auditwheel can emit a manylinux tag instead of failing the repair.
AUDITWHEEL_EXCLUDES=(
  --exclude libkrb5.so.3
  --exclude libk5crypto.so.3
  --exclude libgssapi_krb5.so.2
  --exclude libkrb5support.so.0
  --exclude libcom_err.so.2
  --exclude libkeyutils.so.1
  --exclude libssl.so.1.1
  --exclude libssl.so.3
  --exclude libcrypto.so.1.1
  --exclude libcrypto.so.3
)

yum install -y \
  krb5-devel \
  openssl-devel \
  cmake \
  gcc-c++ \
  make \
  swig \
  libffi-devel \
  unzip

"${PYTHON}" -m pip install -U pip setuptools wheel build Cython auditwheel

rm -rf "${WHEELS_DIR}" "${RAW_WHEELS}"
mkdir -p "${WHEELS_DIR}" "${RAW_WHEELS}"
WHEELS_DIR="${RAW_WHEELS}" bash "${ROOT}/scripts/build_wheels.sh"

shopt -s nullglob
raw_wheels=( "${RAW_WHEELS}"/*.whl )
if (( ${#raw_wheels[@]} == 0 )); then
  echo "no raw wheels to repair" >&2
  exit 1
fi

for wheel in "${raw_wheels[@]}"; do
  echo "auditwheel repair ${wheel}"
  auditwheel repair "${wheel}" -w "${WHEELS_DIR}" --plat manylinux_2_28_x86_64 \
    "${AUDITWHEEL_EXCLUDES[@]}"
done

python3 "${ROOT}/scripts/validate_wheels.py" "${WHEELS_DIR}"
ls -l "${WHEELS_DIR}"
