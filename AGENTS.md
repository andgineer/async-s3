# Repository Guidelines

## Project Structure & Modules
- `src/async_s3/`: Library code and CLI entry (`main.py`, `s3_bucket_objects.py`, `group_by_prefix.py`).
- `tests/`: Pytest suite, async tests, and Moto-backed S3 fixtures (`tests/resources`).
- `scripts/`: Automation helpers (version bump, docs, requirements).
- `docs/`: MkDocs config and content.

## Build, Test, and Dev Commands
- Setup env: `. ./activate.sh` (requires `uv`; creates/activates `.venv`).
- Run tests: `pytest -q` or with coverage `pytest --cov=src/async_s3 -q`.
- Lint/format: `invoke pre` (runs pre-commit: ruff, formatting, mypy).
- CLI quick check: `as3 --help`, e.g., `as3 ls s3://bucket/prefix`.
- Bump version: `invoke ver-release|ver-feature|ver-bug` and commit.
- Update reqs: `invoke reqs` (recompiles `requirements*.txt`).
- Docs preview: `invoke docs-en` (or other languages if configured).

## Coding Style & Naming
- Line length: 99–100 chars (`ruff` 100, `flake8` 99). Use black-compatible formatting via ruff.
- Linting: `ruff` (pyflakes/pycodestyle/pylint rules), `flake8` minimal ignores.
- Types: `mypy` with namespace packages; prefer typed signatures.
- Naming: snake_case for functions/modules, PascalCase for classes, UPPER_CASE for constants.
- Avoid broad exceptions; keep functions small and composable.

## Testing Guidelines
- Frameworks: `pytest`, `pytest-asyncio`, `pytest-cov`, `allure-pytest` optional.
- Structure: new tests in `tests/test_*.py`; mirror module names where possible.
- Async tests: mark with `@pytest.mark.asyncio`.
- Coverage: include tests for new code paths; don’t reduce coverage.
- Local S3: fixtures use Moto server; no real AWS calls required.

## Commit & Pull Requests
- Commits: clear, imperative subject; small, scoped changes. Example: `s3: honor delimiter in paginator`.
- Before PR: run `invoke pre` and `pytest --cov=src/async_s3`.
- PR description: problem, solution, trade-offs; link issues; include CLI examples (inputs/outputs) when relevant.
- Tests: required for new features/bugfixes; update docs if CLI flags change.

## Security & Configuration Tips
- Never commit credentials. Tests set fake AWS env vars automatically.
- For real S3 runs, rely on standard AWS env/config; tune concurrency via `parallelism`.
