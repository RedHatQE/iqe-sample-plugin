#!/usr/bin/env python3
"""Download IQE wheels from GitHub Pages and upload missing ones to Nexus."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
import zipfile

NEXUS_READ_URL = os.environ.get(
    "NEXUS_READ_URL", "https://nexus.corp.redhat.com/repository/cqt-pypi"
)
NEXUS_RELEASE_URL = os.environ.get(
    "NEXUS_RELEASE_URL", "https://nexus.corp.redhat.com/repository/cqt-pypi-release"
)
TWINE_REPOSITORY_URL = os.environ.get(
    "TWINE_REPOSITORY_URL", "https://nexus.corp.redhat.com/repository/cqt-pypi-release/"
)
DEFAULT_DOWNLOAD_URL = "https://redhatqe.github.io/iqe-wheels/simple/"
DEFAULT_WHEEL_DIR = "/tmp/wheels"
USER_AGENT = "iqe-wheels-wheel-manager/1.0"


def ca_bundle_args() -> list[str]:
    args: list[str] = []
    ca = os.environ.get("REQUESTS_CA_BUNDLE")
    if ca and os.path.isfile(ca):
        args.extend(["--cacert", ca])
    elif os.path.isfile("/etc/pki/tls/certs/ca-bundle.crt"):
        args.extend(["--cacert", "/etc/pki/tls/certs/ca-bundle.crt"])
    elif os.path.isfile("/etc/ssl/certs/ca-certificates.crt"):
        args.extend(["--capath", "/etc/ssl/certs"])
    return args


def normalize_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name.lower())


def read_wheel_metadata(wheel_path: str) -> tuple[str | None, str | None]:
    try:
        with zipfile.ZipFile(wheel_path) as zf:
            for member in zf.namelist():
                if not member.endswith(".dist-info/METADATA"):
                    continue
                content = zf.read(member).decode("utf-8")
                pkg_name = re.search(r"^Name: (.+)$", content, re.MULTILINE)
                pkg_version = re.search(r"^Version: (.+)$", content, re.MULTILINE)
                if pkg_name and pkg_version:
                    return pkg_name.group(1), pkg_version.group(1)
    except (OSError, zipfile.BadZipFile, UnicodeDecodeError) as exc:
        print(f"Error reading metadata from {wheel_path}: {exc}", file=sys.stderr)
    return None, None


def http_status(url: str, *, head_only: bool = False, verbose: bool = False) -> str:
    cmd = [
        "curl",
        "-sS",
        "--connect-timeout",
        "10",
        "--max-time",
        "60",
        *ca_bundle_args(),
        "-o",
        "/dev/null",
        "-w",
        "%{http_code}",
    ]
    if head_only:
        cmd.append("-I")
    cmd.append(url)

    if verbose:
        print(f"DEBUG: {' '.join(cmd)}", file=sys.stderr)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except OSError as exc:
        if verbose:
            print(f"DEBUG: curl failed: {exc}", file=sys.stderr)
        return "000"

    code = result.stdout.strip()
    if verbose and result.stderr:
        print(f"DEBUG: curl stderr: {result.stderr}", file=sys.stderr)
    return code if code.isdigit() else "000"


def wheel_on_simple_index(
    base_url: str, normalized_name: str, filename: str, *, verbose: bool = False
) -> bool:
    simple_index_url = f"{base_url.rstrip('/')}/simple/{normalized_name}/"
    cmd = ["curl", "-sS", *ca_bundle_args(), simple_index_url]
    if verbose:
        print(f"DEBUG: {' '.join(cmd)}", file=sys.stderr)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except OSError as exc:
        if verbose:
            print(f"DEBUG: curl failed: {exc}", file=sys.stderr)
        return False

    if verbose and result.stderr:
        print(f"DEBUG: curl stderr: {result.stderr}", file=sys.stderr)
    return filename in result.stdout


def wheel_exists_on_nexus(wheel_path: str, *, verbose: bool = False) -> tuple[bool, str | None]:
    package_name, package_version = read_wheel_metadata(wheel_path)
    if not package_name or not package_version:
        return False, None

    normalized_name = normalize_name(package_name)
    filename = os.path.basename(wheel_path)
    check_urls = [
        f"{NEXUS_READ_URL.rstrip('/')}/packages/{normalized_name}/{package_version}/{filename}",
        f"{NEXUS_RELEASE_URL.rstrip('/')}/packages/{normalized_name}/{package_version}/{filename}",
    ]

    for url in check_urls:
        status_code = http_status(url, head_only=True, verbose=verbose)
        if verbose:
            print(f"CHECK {status_code} {url}", file=sys.stderr)
        if status_code == "200":
            return True, url

    for base_url in (NEXUS_READ_URL, NEXUS_RELEASE_URL):
        if wheel_on_simple_index(base_url, normalized_name, filename, verbose=verbose):
            index_url = f"{base_url.rstrip('/')}/simple/{normalized_name}/ ({filename})"
            if verbose:
                print(f"CHECK index-hit {index_url}", file=sys.stderr)
            return True, index_url

    return False, None


def upload_wheel(wheel_path: str, *, dry_run: bool = False, verbose: bool = False) -> int:
    if dry_run:
        print(f"DRY-RUN: would upload {os.path.basename(wheel_path)}")
        return 0

    cmd = ["twine", "upload", "--repository-url", TWINE_REPOSITORY_URL, wheel_path]
    if verbose:
        cmd.append("--verbose")

    print(f"Uploading {os.path.basename(wheel_path)}...")
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="")

    output = result.stdout + result.stderr
    if result.returncode == 0:
        return 0
    if "already exists" in output.lower() or "redeploy is not allowed" in output.lower():
        return 2
    return 1


def collect_wheel_urls(base_url: str, *, verbose: bool = False) -> list[str]:
    headers = {"User-Agent": USER_AGENT}
    req = urllib.request.Request(base_url, headers=headers)
    main_html = urllib.request.urlopen(req).read().decode("utf-8")
    pkg_paths = re.findall(r'href=["\']([^"\']+)["\']', main_html)

    wheel_urls: list[str] = []
    for path in pkg_paths:
        if path.startswith("#") or path.startswith("?"):
            continue

        pkg_url = urllib.parse.urljoin(base_url, path)
        if not pkg_url.endswith("/"):
            pkg_url += "/"

        if verbose:
            print(f"  --> Scanning package directory: {pkg_url}")
        try:
            pkg_req = urllib.request.Request(pkg_url, headers=headers)
            pkg_html = urllib.request.urlopen(pkg_req).read().decode("utf-8")
        except OSError as exc:
            print(f"ERROR: Failed to read {pkg_url}: {exc}", file=sys.stderr)
            continue

        for link in re.findall(r'href=["\']([^"\']+\.whl(?:#[^"\']*)?)["\']', pkg_html):
            full_whl_url = urllib.parse.urljoin(pkg_url, link.split("#", 1)[0])
            wheel_urls.append(full_whl_url)

    return sorted(set(wheel_urls))


def download_wheels(base_url: str, output_dir: str, *, verbose: bool = False) -> bool:
    os.makedirs(output_dir, exist_ok=True)
    if verbose:
        print(f"Fetching package list from {base_url}...")

    wheel_urls = collect_wheel_urls(base_url, verbose=verbose)
    if verbose:
        print(f"Found {len(wheel_urls)} total wheel files across all packages.\n")

    downloaded = skipped = failed = 0
    for url in wheel_urls:
        filename = os.path.basename(url)
        dest_path = os.path.join(output_dir, filename)
        if os.path.exists(dest_path):
            if verbose:
                print(f"  [Skip] {filename}")
            skipped += 1
            continue

        print(f"  [Downloading] {filename}...")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req) as resp, open(dest_path, "wb") as out_file:
                out_file.write(resp.read())
            downloaded += 1
        except OSError as exc:
            print(f"ERROR: Failed to download {filename}: {exc}", file=sys.stderr)
            failed += 1

    print(
        f"\nDownload summary: downloaded={downloaded} skipped={skipped} failed={failed}"
    )
    return failed == 0 and (downloaded + skipped) > 0


def collect_local_wheels(wheel_dir: str) -> list[str]:
    if os.path.isfile(wheel_dir) and wheel_dir.endswith(".whl"):
        return [wheel_dir]
    if not os.path.isdir(wheel_dir):
        return []
    return sorted(
        os.path.join(wheel_dir, name)
        for name in os.listdir(wheel_dir)
        if name.endswith(".whl")
    )


def upload_wheels(
    wheel_dir: str, *, dry_run: bool = False, verbose: bool = False
) -> int:
    wheels = collect_local_wheels(wheel_dir)
    if not wheels:
        print(f"No wheel files found in {wheel_dir} for upload.", file=sys.stderr)
        return 1

    uploaded = skipped = failed = 0
    for wheel_path in wheels:
        print(f"\n=== {os.path.basename(wheel_path)} ===")
        exists, existing_url = wheel_exists_on_nexus(wheel_path, verbose=verbose)
        if exists:
            print("SKIP: already on Nexus")
            print(f"      {existing_url}")
            skipped += 1
            continue

        print("UPLOAD: not found on Nexus (checked cqt-pypi and cqt-pypi-release)")
        upload_rc = upload_wheel(wheel_path, dry_run=dry_run, verbose=verbose)
        if upload_rc == 0:
            uploaded += 1
        elif upload_rc == 2:
            print("SKIP: upload rejected because asset already exists on cqt-pypi-release")
            skipped += 1
        else:
            failed += 1

    print(f"\nUpload summary: uploaded={uploaded} skipped={skipped} failed={failed}")
    return 1 if failed else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download IQE wheels from GitHub Pages and sync them to Nexus."
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download wheels from the GitHub Pages index.",
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        help="Upload wheels from --wheel-dir to Nexus (skip existing).",
    )
    parser.add_argument(
        "--sync",
        action="store_true",
        help="Download wheels, then upload missing wheels to Nexus.",
    )
    parser.add_argument(
        "--wheel-dir",
        default=DEFAULT_WHEEL_DIR,
        help=f"Directory for downloaded wheels (default: {DEFAULT_WHEEL_DIR}).",
    )
    parser.add_argument(
        "--download-url",
        default=DEFAULT_DOWNLOAD_URL,
        help=f"Simple index URL to download from (default: {DEFAULT_DOWNLOAD_URL}).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show upload actions without calling twine.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print existence-check details.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if not (args.download or args.upload or args.sync):
        parser.error("One of --download, --upload, or --sync is required.")

    if args.upload or args.sync:
        if not args.dry_run and not shutil.which("twine"):
            print("twine is required for upload/sync", file=sys.stderr)
            return 1

    if args.download or args.sync:
        print("\n--- Downloading wheels ---")
        if not download_wheels(args.download_url, args.wheel_dir, verbose=args.verbose):
            if args.sync:
                print("Skipping upload because download found no usable wheels.")
                return 1

    if args.upload or args.sync:
        print("\n--- Uploading wheels to Nexus ---")
        return upload_wheels(args.wheel_dir, dry_run=args.dry_run, verbose=args.verbose)

    return 0


if __name__ == "__main__":
    sys.exit(main())
