# iqe-wheels

Builds and publishes binary wheels for IQE dependencies that require compilation
(`gssapi`, `netifaces`, `python-qpid-proton`).

IQE images and plugin repos consume these wheels from **Nexus** (`cqt-pypi`).
This repository provides two complementary pieces:

1. **GitHub Pages PEP 503 index** — built and updated by CI
2. **`scripts/wheel_manager.py`** — downloads from that index and uploads missing
   wheels to Nexus

## Architecture

```text
packages.json + CI build
        |
        v
GitHub Pages simple index  ----wheel_manager.py---->  Nexus cqt-pypi-release
(redhatqe.github.io/...)         (--sync)                 (default IQE index)
```

IQE repos only need the default `cqt-pypi` index plus `no-build-package`.
They do **not** need a separate `iqe-wheels` uv index after wheels are synced to
Nexus.

| | |
|---|---|
| **Packages** | `gssapi`, `netifaces`, `python-qpid-proton` |
| **Python** | 3.12, 3.13, 3.14, 3.15 (`packages.json`) |
| **Linux** | `manylinux_2_28_x86_64` (auditwheel repaired) |
| **macOS** | `macos-latest` |
| **Pages index** | `https://redhatqe.github.io/iqe-wheels/simple` |
| **Nexus read** | `https://nexus.corp.redhat.com/repository/cqt-pypi/simple` |
| **Nexus upload** | `https://nexus.corp.redhat.com/repository/cqt-pypi-release/` |

## CI behaviour

| Trigger | Build | Validate | Publish Pages |
|---|---|---|---|
| Pull request | yes | yes (dry-run index) | no |
| Push to `main` | yes | yes | yes |
| Daily cron (06:00 UTC) | yes | yes | yes |
| `workflow_dispatch` | yes | yes | yes |

Every wheel is checked with `zipfile.testzip()` before publish. Artifact
downloads are deduped by filename in `scripts/collect_wheels.sh` (GitHub
`merge-multiple` corrupts duplicate `cp311-abi3` Linux wheels).

## Sync wheels to Nexus

Use `wheel_manager.py` after CI has published to GitHub Pages:

```bash
export TWINE_USERNAME=...
export TWINE_PASSWORD=...
# Optional on RHEL/Fedora when curl needs the system trust store:
export REQUESTS_CA_BUNDLE=/etc/pki/tls/certs/ca-bundle.crt

# Download from Pages into /tmp/wheels, upload only missing wheels to Nexus
python3 scripts/wheel_manager.py --sync

# Or step by step
python3 scripts/wheel_manager.py --download
python3 scripts/wheel_manager.py --upload

# Preview upload decisions
python3 scripts/wheel_manager.py --sync --dry-run --verbose
```

Options:

| Flag | Purpose |
|---|---|
| `--download` | Download wheels from GitHub Pages |
| `--upload` | Upload local wheels to Nexus (skip existing) |
| `--sync` | Download, then upload missing wheels |
| `--wheel-dir` | Local directory (default: `/tmp/wheels`) |
| `--download-url` | Override Pages simple index URL |
| `--dry-run` | Do not call `twine upload` |
| `--verbose` | Show Nexus existence checks |

Nexus rejects duplicate filenames (`redeploy is not allowed`). The script checks
`cqt-pypi` and `cqt-pypi-release` before uploading and treats duplicate upload
errors as skips.

## Consumption in IQE repos

After syncing wheels to Nexus, use the standard IQE index configuration:

```toml
[tool.uv]
no-build-package = ["gssapi", "netifaces", "python-qpid-proton"]
system-certs = true

[[tool.uv.index]]
name = "cqt-pypi"
url = "https://nexus.corp.redhat.com/repository/cqt-pypi/simple"
default = true
```

`iqe-core` pins wheel versions via `build_constraints` (`gssapi`,
`python-qpid-proton`). Plugin cookiecutter templates use
`iqe-core[imposed_constraints]` so transitive consumers stay on those pins.

## Adding packages or versions

Edit `packages.json`:

- **`packages`**: unversioned names; daily cron builds latest from PyPI
- **`pinned`**: explicit versions to keep on the index (n, n-1, n-2, …)

Merge to `main` or run **Build and Publish IQE Wheels** manually, then run
`wheel_manager.py --sync` to push new Linux wheels to Nexus.

## Repository scripts

| Script | Used by | Purpose |
|---|---|---|
| `scripts/build_wheels.sh` | CI, local macOS | Build wheels from sdists |
| `scripts/build_manylinux.sh` | CI Linux job | manylinux build + auditwheel |
| `scripts/collect_wheels.sh` | CI validate/publish | Validate and dedupe artifacts |
| `scripts/merge_site.sh` | CI publish | Merge wheels onto gh-pages tree |
| `scripts/generate_index.py` | CI publish | Generate PEP 503 index |
| `scripts/validate_wheels.py` | CI, local | `zipfile.testzip()` validation |
| `scripts/wheel_manager.py` | operators | Download from Pages, upload to Nexus |

## Local checks

```bash
# Validate wheels on disk
python3 scripts/validate_wheels.py wheels/

# Build on macOS
./scripts/build_wheels.sh

# Preview the Pages index locally
mkdir -p site/packages && cp wheels/*.whl site/packages/
python3 scripts/generate_index.py site \
  --simple-url https://redhatqe.github.io/iqe-wheels/simple
```
