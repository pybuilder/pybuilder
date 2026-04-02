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

# Debug verbose output (includes all debug logging)
pyb -vX

# Dump project configuration as JSON (no build, runs initializers only)
pyb -i
# JSON goes to stdout, log messages go to stderr
pyb -i 2>/dev/null | jq .project.name
pyb -i -E ci -P verbose=true 2>/dev/null | jq .
```

The build script (`build.py`) bootstraps by inserting `src/main/python` into
`sys.path` so PyBuilder can build itself.

## Virtual Environments

PyBuilder manages isolated venvs during builds:

- `.pybuilder/plugins/{version}/` — plugin dependencies (committed to `.gitignore`)
- `target/venv/build/{version}/` — build + runtime deps (unit tests run here)
- `target/venv/test/{version}/` — runtime deps only (integration tests run here)

Unit tests use subprocess remoting: a child process is spawned with the build
venv's Python, `sys.path` is remapped to use the build venv's site-packages,
and tests execute via RPC. Integration tests run each file as a standalone
subprocess with `PYTHONPATH` pointing to `target/dist/` (the built distribution).

## Logs and Reports

- `target/reports/unittest` — unit test console output
- `target/reports/unittest.json` — structured unit test results (JSON)
- `target/reports/integrationtests/{name}` — per-integration-test stdout
- `target/reports/integrationtests/{name}.err` — per-integration-test stderr
- `target/reports/*_coverage*` — coverage reports (JSON, XML, HTML)
- `target/logs/install_dependencies/` — pip install logs

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

## Releasing

The version in `build.py` is always `X.Y.Z.dev` on master. Do **not** change it
manually to cut a release. Instead, append `[release]` (or `[release X.Y.Z]` for
a specific version) to the **first line** of the commit message and PR title. The
CI detects this tag and handles version finalization, tagging, and PyPI upload
automatically. After the release, CI bumps the version to the next `.dev`.

Example commit message first line:
```
Release 0.13.19 [release]
```

## Git Workflow

This is a fork. PRs go from `origin` (arcivanov) to `upstream` (pybuilder).
Always pull from `upstream` before branching. Never push directly to `master`.

## Documentation Updates (pybuilder.github.io)

The project website is in the `pybuilder/pybuilder.github.io` GitHub repo
(branch `source`). Changes to PyBuilder code must be accompanied by
corresponding documentation updates.

### For new features (new CLI flag, new plugin, new API):

1. **Release notes** — add entry under the next version in
   `articles/_release-notes/v0.13.x.md` (section `### New Features`)
2. **Manual** — add or update the relevant section in `documentation/manual.md`
3. **Tutorial** — if the feature is user-facing and discoverable, add a brief
   section or example to `documentation/tutorial.md`
4. **Coding agents** — update `documentation/coding-agents.md` (both the
   "Quick Reference for Agents" section and the example CLAUDE.md) if the
   feature affects how agents interact with builds (e.g. new CLI flags,
   new build commands, new output formats)
5. **Dedicated page** (optional) — for substantial features, create a new page
   under `documentation/` and add it to `documentation/index.md`
6. **Blog post** — create `articles/_posts/YYYY-MM-DD-slug.md` with front matter
   `layout: post`, `author: arcivanov`, `categories: news`

### For bug fixes:

1. **Release notes** — add entry under `### Bugs Fixed` in
   `articles/_release-notes/v0.13.x.md`
2. **Manual/tutorial** — update only if the fix changes documented behavior or
   corrects a misleading example

### For parameter/property additions to existing plugins:

1. **Release notes** — add entry under `### New Features` (if user-visible) or
   `### Bugs Fixed` (if correcting behavior)
2. **Plugin reference** — update property tables in `documentation/plugins.md`
3. **Manual** — update if the property affects a workflow described there

### For dependency upgrades and vendorized bumps:

1. **Release notes** — add entry under `### Vendorized Dependency Upgrades`

### File reference:

| File | Purpose |
|------|---------|
| `articles/_release-notes/v0.13.x.md` | Release notes (add new version at top) |
| `articles/_posts/YYYY-MM-DD-*.md` | Blog posts / announcements |
| `documentation/manual.md` | Usage manual (CLI, properties, venvs, testing) |
| `documentation/tutorial.md` | Getting started tutorial |
| `documentation/plugins.md` | Plugin reference with property tables |
| `documentation/coding-agents.md` | Agent instruction guidance and examples |
| `documentation/index.md` | Documentation hub (add links for new pages) |
