# iqe-wheels

This project builds and publishes binary wheels for IQE dependencies that require compilation (like `gssapi`, `netifaces`, and `python-qpid-proton`).

By providing these wheels via a PEP 503 simple index, IQE execution images do not need to ship with `gcc` or other build tools, resulting in smaller and more secure images.

| | |
|---|---|
| **Packages** | `gssapi`, `netifaces`, `python-qpid-proton` |
| **Python** | 3.12, 3.13, 3.14 (configurable in `packages.json`) |
| **Platforms** | `manylinux_2_28_x86_64`, macOS (`macos-latest`) |
| **Schedule** | Daily (06:00 UTC) plus `workflow_dispatch` |

## Consumption with uv

To use these wheels, add the following to your plugin's `pyproject.toml`. This configuration ensures that `uv` pulls the pre-built wheels from this repository instead of trying to compile them.

```toml
[tool.uv]
no-build-package = ["gssapi", "netifaces", "python-qpid-proton"]

[[tool.uv.index]]
name = "iqe-wheels"
url = "https://redhatqe.github.io/iqe-wheels/simple"
explicit = true

[tool.uv.sources]
gssapi = { index = "iqe-wheels" }
netifaces = { index = "iqe-wheels" }
python-qpid-proton = { index = "iqe-wheels" }
```

**Note:** `explicit = true` is used to prevent `uv` from searching this index for other packages, which helps avoid dependency confusion.

## How it works

1.  **Build**: A GitHub Action matrix builds wheels for each supported Python version and platform.
    *   **Linux**: Built inside `quay.io/pypa/manylinux_2_28_x86_64` to ensure compatibility with UBI9-based images.
    *   **macOS**: Built on `macos-latest` with necessary system headers installed via Homebrew.
2.  **Accumulate**: The workflow fetches the existing `gh-pages` branch and merges the new wheels into the existing set. This allows the index to grow over time and support multiple versions of the same package.
3.  **Index**: A custom script generates a PEP 503 compliant `simple` index from the accumulated wheels.
4.  **Publish**: The updated index and wheels are force-pushed to the `gh-pages` branch, making them available via GitHub Pages.

## Adding new packages or versions

-   To add a new package or Python version, update `packages.json`.
-   To pin specific older versions for building, add them to the `pinned` array in `packages.json`.
-   The daily cron job will automatically pick up and build the latest versions available on PyPI.
