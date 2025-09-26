#!/usr/bin/env python3
"""Download and extract IHME GHDx life expectancy data releases.

This helper pulls every ZIP archive linked on the specified dataset page and
unpacks the contents into a structured directory layout suitable for ad-hoc
analysis.  It is intentionally dependency free so that it can run in restricted
research environments.

Example
-------
python scripts/download_ghdx_dataset.py \
    --dataset-url https://ghdx.healthdata.org/record/ihme-data/united-states-causes-death-life-expectancy-by-county-race-ethnicity-2000-2019 \
    --output-dir data/ghdx

The script will mirror the ZIP files under ``data/ghdx/raw`` and extract their
contents into ``data/ghdx/extracted``.
"""
from __future__ import annotations

import argparse
import ssl
import sys
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable, Set
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen
import shutil
import zipfile

# Some GHDx endpoints block requests without a browser-like user agent.
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/123.0 Safari/537.36"
    )
}


def _ssl_context() -> ssl.SSLContext:
    """Build an SSL context that relies on system certificates."""
    ctx = ssl.create_default_context()
    return ctx


@dataclass(frozen=True)
class DownloadTarget:
    """Represents a downloadable resource discovered on the dataset page."""

    url: str
    filename: str


class ZipLinkParser(HTMLParser):
    """Collect all links that point at ZIP files within a page."""

    def __init__(self, base_url: str):
        super().__init__()
        self._base_url = base_url
        self._links: Set[str] = set()

    def handle_starttag(self, tag: str, attrs: Iterable[tuple[str, str]]) -> None:
        if tag.lower() != "a":
            return
        href = dict(attrs).get("href")
        if not href:
            return
        if ".zip" not in href.lower():
            return
        absolute = urljoin(self._base_url, href)
        self._links.add(absolute)

    @property
    def links(self) -> Set[str]:
        return self._links


def discover_zip_files(dataset_url: str) -> Set[DownloadTarget]:
    """Scrape the dataset page for ZIP file links."""
    req = Request(dataset_url, headers=DEFAULT_HEADERS)
    try:
        with urlopen(req, context=_ssl_context()) as response:
            body = response.read().decode("utf-8", errors="replace")
    except HTTPError as err:
        raise RuntimeError(
            f"Failed to load dataset page {dataset_url!r}: HTTP {err.code}"
        ) from err
    except URLError as err:
        raise RuntimeError(f"Failed to reach {dataset_url!r}: {err.reason}") from err

    parser = ZipLinkParser(dataset_url)
    parser.feed(body)

    targets = set()
    for link in parser.links:
        filename = link.rsplit("/", 1)[-1]
        targets.add(DownloadTarget(url=link, filename=filename))
    if not targets:
        raise RuntimeError(
            "No ZIP files were discovered on the dataset page. "
            "You may need to visit the URL in a browser and accept any terms "
            "before rerunning the downloader."
        )
    return targets


def download_file(target: DownloadTarget, destination: Path) -> None:
    """Stream a remote file onto disk, skipping if already present."""
    if destination.exists():
        print(f"Skipping existing archive: {destination}")
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    req = Request(target.url, headers=DEFAULT_HEADERS)
    print(f"Downloading {target.url} -> {destination}")
    try:
        with urlopen(req, context=_ssl_context()) as response, destination.open("wb") as fh:
            shutil.copyfileobj(response, fh)
    except HTTPError as err:
        raise RuntimeError(
            f"Failed to download {target.url!r}: HTTP {err.code}"
        ) from err
    except URLError as err:
        raise RuntimeError(f"Failed to download {target.url!r}: {err.reason}") from err


def extract_archive(archive_path: Path, destination_dir: Path) -> Path:
    """Extract ``archive_path`` underneath ``destination_dir``."""
    stem = archive_path.stem
    # ``stem`` strips only the last suffix; accommodate .zip.zip just in case.
    while stem.lower().endswith(".zip"):
        stem = stem[:-4]
    target_dir = destination_dir / stem
    if target_dir.exists():
        print(f"Skipping extraction (already exists): {target_dir}")
        return target_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    print(f"Extracting {archive_path} -> {target_dir}")
    with zipfile.ZipFile(archive_path, "r") as zf:
        zf.extractall(target_dir)
    return target_dir


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset-url",
        default="https://ghdx.healthdata.org/record/ihme-data/"
        "united-states-causes-death-life-expectancy-by-county-race-ethnicity-2000-2019",
        help="Dataset page to scrape for download links.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/ghdx"),
        help="Directory where archives and extracted files will be stored.",
    )
    parser.add_argument(
        "--raw-subdir",
        default="raw",
        help="Name of the subdirectory for downloaded ZIP archives.",
    )
    parser.add_argument(
        "--extracted-subdir",
        default="extracted",
        help="Name of the subdirectory for extracted contents.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(list(argv or sys.argv[1:]))
    output_dir: Path = args.output_dir
    raw_dir = output_dir / args.raw_subdir
    extracted_dir = output_dir / args.extracted_subdir

    try:
        targets = discover_zip_files(args.dataset_url)
    except RuntimeError as err:
        print(err, file=sys.stderr)
        return 1

    extracted_locations = []
    for target in sorted(targets, key=lambda t: t.filename.lower()):
        destination = raw_dir / target.filename
        try:
            download_file(target, destination)
        except RuntimeError as err:
            print(err, file=sys.stderr)
            continue
        try:
            extracted_locations.append(extract_archive(destination, extracted_dir))
        except zipfile.BadZipFile:
            print(
                f"Failed to extract {destination}: not a valid ZIP archive.",
                file=sys.stderr,
            )

    if not extracted_locations:
        print(
            "No archives were successfully extracted. Review the errors above "
            "and ensure you have access to the dataset URLs.",
            file=sys.stderr,
        )
        return 2

    print("Finished downloading data. Extracted directories:")
    for path in extracted_locations:
        print(f"  - {path}")
    return 0


if __name__ == "__main__":  # pragma: no cover - convenience entry point
    raise SystemExit(main())
