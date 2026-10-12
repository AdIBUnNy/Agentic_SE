"""
Dependency verifier for AI-generated requirements files.

AI coding agents sometimes "hallucinate" package names that don't exist on
PyPI (one study found ~19.7% of recommended packages were fake). Anyone can
register an invented name on PyPI and wait for someone to install it, so
before running `pip install` we verify every pinned dependency.

For each line "name == version" we ask the PyPI JSON API:
  1. https://pypi.org/pypi/<name>/json          -> 404 means the package
                                                    does not exist at all
  2. https://pypi.org/pypi/<name>/<version>/json -> 404 means the package
                                                    exists but that pinned
                                                    version does not

We then report:
  * Dependencies checked   : number of lines in the file
  * Packages not on PyPI    : name doesn't exist
  * Versions not on PyPI    : name exists but pinned version doesn't
  * Oldest pinned release   : among lines where BOTH name and version exist,
                              the release whose first uploaded file is oldest
                              (compared by urls[0].upload_time), printed as
                              name == version (year)

Only the standard library is used: urllib + json.

Usage:
    python check_deps.py <requirements_file>
    python check_deps.py            # defaults to requirements.txt
"""

import json
import re
import sys
import urllib.error
import urllib.request

API = "https://pypi.org/pypi"
TIMEOUT = 15  # seconds per request

# Matches "name==version" / "name = version" with any spacing, ignoring
# inline comments. Group 1 = package name, group 2 = pinned version.
LINE_RE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*={1,2}\s*([^\s#]+)")


def get_json(url):
    """GET a URL and return parsed JSON, or None if the server returns 404."""
    req = urllib.request.Request(url, headers={"User-Agent": "dep-checker/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise  # any other HTTP error (500, etc.) is a real problem


def parse_line(line):
    """Return (name, version) from a requirements line, or None to skip it."""
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    m = LINE_RE.match(line)
    if not m:
        return None
    return m.group(1), m.group(2)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "requirements.txt"

    with open(path, encoding="utf-8") as f:
        raw_lines = f.readlines()

    # "Dependencies checked" = number of (non-empty, non-comment) dependency
    # lines in the file.
    deps = [p for p in (parse_line(ln) for ln in raw_lines) if p is not None]

    missing_pkgs = 0      # name not on PyPI at all
    missing_versions = 0  # name exists, pinned version does not

    oldest = None         # (upload_time_str, name, version)

    for name, version in deps:
        pkg = get_json(f"{API}/{name}/json")
        if pkg is None:
            missing_pkgs += 1
            continue

        release = get_json(f"{API}/{name}/{version}/json")
        if release is None:
            missing_versions += 1
            continue

        # Both name and version exist. Use the upload_time of the FIRST file
        # listed under "urls" as this release's timestamp.
        files = release.get("urls", [])
        if not files:
            continue
        upload_time = files[0].get("upload_time") or files[0].get(
            "upload_time_iso_8601"
        )
        if not upload_time:
            continue

        if oldest is None or upload_time < oldest[0]:
            oldest = (upload_time, name, version)

    print(f"Dependencies checked = {len(deps)}")
    print(f"Packages not on PyPI : {missing_pkgs}")
    print(f"Versions not on PyPI : {missing_versions}")
    if oldest is not None:
        year = oldest[0][:4]
        print(f"Oldest pinned release : {oldest[1]} == {oldest[2]} ({year})")
    else:
        print("Oldest pinned release : none")


if __name__ == "__main__":
    main()
