# PyPI Dependency Verifier

A small tool that checks an AI-generated requirements file against PyPI before
you run `pip install`.

AI coding agents sometimes **hallucinate package names** that don't exist (one
study found ~19.7% of recommended packages were fake). Since anyone can register
an invented name on PyPI, blindly installing an AI-generated requirements file
is a supply-chain risk. This script verifies every pinned line against the
official PyPI JSON API.

## What it checks

For each line `name == version`, it queries the PyPI JSON API:

1. `https://pypi.org/pypi/<name>/json` → `404` means the package doesn't exist.
2. `https://pypi.org/pypi/<name>/<version>/json` → `404` means the package
   exists but that pinned version doesn't.

It then reports:

- **Dependencies checked** — number of dependency lines in the file
- **Packages not on PyPI** — the name doesn't exist at all
- **Versions not on PyPI** — the name exists but the pinned version doesn't
- **Oldest pinned release** — among lines where both name and version exist,
  the release whose first uploaded file is oldest (compared by
  `urls[0].upload_time`), printed as `name == version (year)`

Standard library only (`urllib` + `json`) — no third-party dependencies.

## Usage

```bash
python3 check_deps.py <requirements_file>
```

## Examples

```bash
python3 check_deps.py sample1.txt
```

```
Dependencies checked = 5
Packages not on PyPI : 1
Versions not on PyPI : 1
Oldest pinned release : numpy == 1.16.0 (2019)
```

```bash
python3 check_deps.py sample2.txt
```

```
Dependencies checked = 8
Packages not on PyPI : 2
Versions not on PyPI : 2
Oldest pinned release : python-dateutil == 2.2 (2013)
```

## Requirements

- Python 3.11+
- Internet access (queries the live PyPI API)
