# iqe-wheels

This project builds and publishes binary wheels for IQE dependencies that require compilation (`gssapi`, `netifaces`, `python-qpid-proton`).

By providing these wheels via a PEP 503 simple index, IQE execution images do not need to ship with `gcc` or other build tools.

| | |
|---|---|
| **Packages** | `gssapi`, `netifaces`, `python-qpid-proton` |
| **Python** | 3.12, 3.13, 3.14 (edit `packages.json`) |
| **Platforms** | `manylinux_2_28_x86_64`, macOS (`macos-latest`) |
| **Schedule** | Daily (06:00 UTC) plus `workflow_dispatch` |
| **Index** | `https://redhatqe.github.io/iqe-wheels/simple` |

## CI behaviour

| Trigger | Build | Validate | Publish Pages |
|---|---|---|---|
| Pull request | yes | yes (dry-run index) | no |
| Push to `main` | yes | yes | yes |
| Daily cron | yes | yes | yes |
| `workflow_dispatch` | yes | yes | yes |

Every built wheel is checked with `zipfile.testzip()` before upload. Artifact downloads are **not** merged with GitHub's `merge-multiple` (that corrupts duplicate filenames such as `gssapi-*-cp311-abi3-*.whl` produced by every Linux matrix job). Instead, `scripts/collect_wheels.sh` validates and dedupes by filename before publish.

## Consumption with uv

```toml
[tool.uv]
no-build-package = ["gssapi", "netifaces", "python-qpid-proton"]

[[tool.uv.index]]
name = "cqt-pypi"
url = "https://nexus.corp.redhat.com/repository/cqt-pypi/simple"
default = true

[[tool.uv.index]]
name = "iqe-wheels"
url = "https://redhatqe.github.io/iqe-wheels/simple"
explicit = true

[tool.uv.sources]
gssapi = { index = "iqe-wheels" }
netifaces = { index = "iqe-wheels" }
python-qpid-proton = { index = "iqe-wheels" }
```

`explicit = true` stops uv from searching this index for other packages. uv does not inherit index config from dependencies — each plugin repo needs this block.

## Adding packages or versions

Edit `packages.json`:

- **`packages`**: unversioned names; the daily cron builds whatever is latest on PyPI.
- **`pinned`**: explicit versions to keep on the index (n, n-1, n-2, …).

After changing `packages.json`, merge to `main` or run **Build and Publish IQE Wheels** manually.

## Local checks

```bash
# Validate wheels already on disk
python3 scripts/validate_wheels.py wheels/

# Build on macOS (example)
./scripts/build_wheels.sh

# Generate a local simple index preview
mkdir -p site/packages && cp wheels/*.whl site/packages/
python3 scripts/generate_index.py site --simple-url https://redhatqe.github.io/iqe-wheels/simple
```
