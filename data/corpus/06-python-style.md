# Python Style Guide

Owner: Developer Experience (DevEx)

## Versions and tooling

Python services target Python 3.12. Dependencies are managed with `uv`;
`pip` and `poetry` are not used. Every repository pins the interpreter in
`.python-version` and commits `uv.lock`.

Formatting and linting use `ruff` with the organisation configuration in
`libs/python/larkspur-ruff`. The line length is 100 characters. CI runs
`ruff check` and `ruff format --check`; both must pass.

## Type hints

All new code MUST have type hints on function signatures. Services run
`pyright` in `standard` mode in CI. `Any` is allowed only at boundaries with
untyped third-party code and must carry a comment explaining why.

## Project layout

Python packages use the `src/` layout:

```
service-name/
  pyproject.toml
  src/service_name/
  tests/
```

Tests live outside the package and mirror its structure. Test files are named
`test_<module>.py` and use `pytest`; `unittest` style classes are discouraged.

## Data models

Use `pydantic` v2 models for anything that crosses a process boundary (HTTP
bodies, queue messages, configuration). Use `dataclasses` for in-process
value objects. Never pass raw dictionaries between modules.

## Configuration

Configuration is read exactly once, in `settings.py`, through
`pydantic-settings`. Modules import the settings object; they never read
`os.environ` directly.

## Logging

Use the standard `logging` module through `larkspur_logging.get_logger()`,
which emits JSON. Never use `print` in service code. Log lines include the
`trace_id` automatically when a request context is active.

## Error handling

Catch specific exceptions. A bare `except:` or `except Exception:` is allowed
only at the top of a worker loop or request handler, and it MUST log the
exception with `logger.exception`. Do not use exceptions for control flow.

## Async

Web services use FastAPI and `asyncio`. Blocking calls (CPU-heavy work,
synchronous database drivers) run in a thread pool via
`asyncio.to_thread`. Mixing synchronous and asynchronous database clients in
one service is not allowed.

## Dependencies

Adding a dependency requires a short justification in the pull request. Prefer
the standard library. Dependencies are updated weekly by Renovate; security
patches are merged within two business days.
