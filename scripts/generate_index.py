#!/usr/bin/env python3
"""Generate a PEP 503 simple repository from a directory of wheels."""

from __future__ import annotations

import argparse
import hashlib
import html
import re
from collections import defaultdict
from pathlib import Path

SIMPLE_INDEX_TEMPLATE = """\
<!DOCTYPE html>
<html>
  <head>
    <meta name="pypi:repository-version" content="1.1">
    <title>Simple index</title>
  </head>
  <body>
{links}
  </body>
</html>
"""

PACKAGE_INDEX_TEMPLATE = """\
<!DOCTYPE html>
<html>
  <head>
    <meta name="pypi:repository-version" content="1.1">
    <title>Links for {name}</title>
  </head>
  <body>
    <h1>Links for {name}</h1>
{links}
  </body>
</html>
"""

HOME_TEMPLATE = """\
<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8">
    <title>IQE binary wheels</title>
  </head>
  <body>
    <h1>IQE binary wheels</h1>
    <p>
      PEP 503 simple index:
      <a href="simple/"><code>simple/</code></a>
    </p>
    <p>
      Point uv/pip at <code>{simple_url}</code>.
      Wheels stay on this site across builds; new Python/OS/package versions
      are added, existing files are replaced only when rebuilt.
    </p>
    <h2>Packages</h2>
{sections}
  </body>
</html>
"""


def normalize(name: str) -> str:
    """Normalize a distribution name per PEP 503."""
    return re.sub(r"[-_.]+", "-", name).lower()


def distribution_from_wheel(filename: str) -> str:
    """Return the un-normalized distribution name from a wheel filename."""
    stem = filename[: -len(".whl")]
    return stem.split("-", 1)[0]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def generate(site_dir: Path, simple_url: str) -> int:
    packages_dir = site_dir / "packages"
    wheels = sorted(packages_dir.glob("*.whl"))
    if not wheels:
        raise SystemExit(f"no wheels found in {packages_dir}")

    by_package: dict[str, list[Path]] = defaultdict(list)
    for wheel in wheels:
        by_package[normalize(distribution_from_wheel(wheel.name))].append(wheel)

    simple_dir = site_dir / "simple"
    package_links = []
    home_sections = []
    for name in sorted(by_package):
        package_links.append(f'    <a href="{html.escape(name)}/">{html.escape(name)}</a><br/>')
        wheel_links = []
        home_items = []
        for wheel in sorted(by_package[name], key=lambda path: path.name):
            digest = sha256_file(wheel)
            href = f"../../packages/{wheel.name}#sha256={digest}"
            escaped_name = html.escape(wheel.name)
            wheel_links.append(
                f'    <a href="{html.escape(href)}">{escaped_name}</a><br/>'
            )
            home_items.append(f"      <li><code>{escaped_name}</code></li>")
        write_text(
            simple_dir / name / "index.html",
            PACKAGE_INDEX_TEMPLATE.format(name=html.escape(name), links="\n".join(wheel_links)),
        )
        home_sections.append(
            f"    <h3>{html.escape(name)}</h3>\n    <ul>\n"
            + "\n".join(home_items)
            + "\n    </ul>"
        )

    write_text(simple_dir / "index.html", SIMPLE_INDEX_TEMPLATE.format(links="\n".join(package_links)))
    write_text(
        site_dir / "index.html",
        HOME_TEMPLATE.format(simple_url=html.escape(simple_url), sections="\n".join(home_sections)),
    )
    write_text(site_dir / ".nojekyll", "")
    return len(wheels)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("site_dir", type=Path, help="Site root (contains packages/*.whl)")
    parser.add_argument(
        "--simple-url",
        default="https://<owner>.github.io/<repo>/simple",
        help="URL shown on the human-readable homepage",
    )
    args = parser.parse_args()
    count = generate(args.site_dir, args.simple_url)
    print(f"indexed {count} wheels under {args.site_dir / 'simple'}")


if __name__ == "__main__":
    main()
