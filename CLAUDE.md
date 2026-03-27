# PyBuilder — Project Instructions

## Overview

PyBuilder is a build automation tool for Python, written in pure Python. It uses
dependency-based programming with a plugin mechanism for build lifecycles similar
to Maven and Gradle. This is a **fork** (`origin` = `arcivanov/pybuilder`,
`upstream` = `pybuilder/pybuilder`).

## Project Layout

- `build.py` — PyBuilder build descriptor (like `pom.xml` or `build.gradle`)
- `src/main/python/pybuilder/` — main source code
- `src/unittest/python/` — unit tests (`*_tests.py`)
- `src/integrationtest/python/` — integration tests (`*_tests.py`)
- `setup.py` — pip install bootstrap (runs PyBuilder internally, **do not run manually**)
- `pyproject.toml` — PEP 517 build backend pointing to `pybuilder.pep517`
- `target/` — build output directory (gitignored)

## Building & Testing

PyBuilder builds itself (bootstrap). All build commands use `pyb`:

```bash
# Full build (analyze + publish)
pyb

# Run unit tests only
pyb run_unit_tests

# Run integration tests only
pyb run_integration_tests

# Clean build
pyb clean package

# Verbose output
pyb -v
```

The build script (`build.py`) bootstraps by inserting `src/main/python` into
`sys.path` so PyBuilder can build itself.

## Python Version Support

- Required: Python >= 3.10
- Supported: CPython 3.10, 3.11, 3.12, 3.13, 3.14
- Experimental: CPython 3.15-dev, free-threaded 3.14t/3.13t, PyPy 3.10/3.11

## CI

GitHub Actions workflow at `.github/workflows/pybuilder.yml`:
- `build-primary`: Ubuntu, all supported Python versions, with/without venv
- `build-secondary`: Windows + macOS, all supported Python versions
- `build-experimental`: dev/free-threaded/PyPy builds (allowed to fail)
- Deployment happens from `master` branch on Python 3.13 Linux only

## Vendored Dependencies

PyBuilder vendors its dependencies into `src/main/python/pybuilder/_vendor/`
via the `python.vendorize` plugin. Do not modify vendored code directly.

## Code Style

- Max line length: 130 characters (flake8)
- flake8 is enforced and breaks the build
- Extend ignore: E303, F401, F824
- Apache License 2.0 header on source files

## Git Workflow

This is a fork. PRs go from `origin` (arcivanov) to `upstream` (pybuilder).
Always pull from `upstream` before branching. Never push directly to `master`.
