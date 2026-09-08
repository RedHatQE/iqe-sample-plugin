# iqe-sample-plugin

Sample plugin for the IQE tests framework.

This repository also builds the compiled wheels IQE needs (`gssapi`,
`netifaces`, `python-qpid-proton`) so images do not ship `gcc`. GitHub Actions
publishes them as an accumulating [PEP 503](https://peps.python.org/pep-0503/)

| | |
|---|---|
| Packages | `gssapi`, `netifaces`, `python-qpid-proton` |
| Python | 3.12, 3.13, 3.14 (edit `packages.json`) |
| Platforms | `manylinux_2_28_x86_64`, macOS (`macos-latest`) |
| Schedule | Daily (06:00 UTC) plus `workflow_dispatch` |

New package versions, Python versions, or OS tags are **added**. Existing
wheels stay on the index unless the same filename is rebuilt.


## Consume with uv

Keep Nexus as the default index. Point only these three packages at Pages:

```toml
[[tool.uv.index]]
name = "iqe-wheels"
url = "https://redhatqe.github.io/iqe-sample-plugin/simple"
explicit = true

[tool.uv.sources]
gssapi = { index = "iqe-wheels" }
netifaces = { index = "iqe-wheels" }
python-qpid-proton = { index = "iqe-wheels" }
```

`explicit = true` stops uv from searching this index for every other package.
uv does not inherit indexes from `iqe-core`, so plugins that lock these
packages need the same block.

## How the workflow works

- **Linux** builds inside `quay.io/pypa/manylinux_2_28_x86_64` so the wheels
  load on UBI9. Plain `ubuntu-latest` wheels would link a newer glibc.
- **macOS** uses `actions/setup-python` plus Homebrew `krb5` / `openssl`.
- Pull requests **build only**. Pages is updated from default branch.
- Publish copies the previous `gh-pages` tree, overlays new `*.whl` files,
  regenerates `/simple/`, and force-pushes an orphan `gh-pages` commit.

To rebuild specific versions instead of “whatever PyPI currently ships”:

```
workflow_dispatch → package_spec: gssapi==1.11.1 netifaces==0.11.0 python-qpid-proton==0.40.0
```
