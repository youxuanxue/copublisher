# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

Copublisher is a multi-platform media content publishing CLI/GUI tool (Python 3.10+, managed with `uv` + `hatchling`). See `README.md` for full documentation.

### Running services

- **Gradio GUI**: `source .venv/bin/activate && python -m media_publisher` (serves on port 7860)
- **CLI entry point**: `copublisher --help` (installed via `pip install -e .`)
- The dbus errors from Chromium in headless/cloud environments are harmless and can be ignored.

### Tests

- Run all tests: `source .venv/bin/activate && python -m unittest discover -s tests -v`
- 4 test files using `unittest` (no pytest required): `test_security.py`, `test_atomic_io.py`, `test_job_cli.py`, `test_import_side_effects.py`

### Lint

- No dedicated linter configuration is present in the repo. Standard `pyright` or `mypy` can be used if needed.

### Key caveats

- Playwright Chromium must be installed separately after `pip install`: `uv run playwright install --with-deps chromium`. This is already handled by the update script.
- All platform credential files (`config/youtube_credentials.json`, `config/medium_token.txt`, etc.) are gitignored and not required for tests or GUI startup.
- The project uses lazy imports in `__init__.py` (`__getattr__`) to avoid module-level side effects — tests verify this.
- The virtual environment is at `/workspace/.venv`. Always activate it before running commands.
