# K8s MCP Server Development Guide

## Build & Test Commands

- Install dependencies: `uv pip install -e .` (or use `make install`)
- Install dev dependencies: `uv pip install -e ".[dev]"` (or use `make dev-install`)
- Run server: `python -m k8s_mcp_server`
- Run unit tests only (default): `pytest` (or use `make test`)
- Run all tests (including integration): `pytest -o addopts=""` (or use `make test-all`)
- Run unit tests explicitly: `pytest -m unit` (or use `make test-unit`)
- Run integration tests only: `pytest -m integration` (or use `make test-integration`)
- Run single test: `pytest tests/path/to/test_file.py::test_function_name -v`
- Run linter: `ruff check src/ tests/` (or use `make lint`)
- Format code: `ruff format src/ tests/` (or use `make format`)

## Technical Stack

- **Python version**: Python 3.13+
- **Package management**: `uv` for fast, reliable package management
- **Project config**: `pyproject.toml` for configuration and dependency management
- **Environment**: Use virtual environment in `.venv` for dependency isolation
- **Dependencies**: Separate production and dev dependencies in `pyproject.toml`
- **Linting**: `ruff` for style and error checking
- **Type checking**: Use VS Code with Pylance for static type checking
- **Project layout**: Organize code with `src/` layout

## Code Style Guidelines

- **Formatting**: Black-compatible formatting via `ruff format` with 120 char line length
- **Imports**: Sort imports with `ruff` (stdlib, third-party, local)
- **Type hints**: Use native Python type hints (e.g., `list[str]` not `List[str]`)
- **Documentation**: Google-style docstrings for all modules, classes, functions
- **Naming**: snake_case for variables/functions, PascalCase for classes
- **Function length**: Keep functions short (< 30 lines) and single-purpose
- **PEP 8**: Follow PEP 8 style guide (enforced via `ruff`)

## Python Best Practices

- **File handling**: Prefer `pathlib.Path` over `os.path`
- **Debugging**: Use `logging` module instead of `print`
- **Error handling**: Use specific exceptions with context messages and proper logging
- **Data structures**: Use list/dict comprehensions for concise, readable code
- **Function arguments**: Avoid mutable default arguments
- **Data containers**: Leverage `dataclasses` to reduce boilerplate
- **Configuration**: Use environment variables for configuration
- **K8s validation**: Validate all commands before execution (must start with allowed prefixes)
- **Security**: Never store/log credentials, set command timeouts

## Development Patterns & Best Practices

- **Favor simplicity**: Choose the simplest solution that meets requirements
- **DRY principle**: Avoid code duplication; reuse existing functionality
- **Configuration management**: Use environment variables for different environments
- **Focused changes**: Only implement explicitly requested or fully understood changes
- **Preserve patterns**: Follow existing code patterns when fixing bugs
- **File size**: Keep files under 300 lines; refactor when exceeding this limit
- **Test coverage**: Write comprehensive unit and integration tests with `pytest`; include fixtures
- **Modular design**: Create reusable, modular components
- **Logging**: Implement appropriate logging levels (debug, info, error)
- **Error handling**: Implement robust error handling for production reliability
- **Security best practices**: Follow input validation and data protection practices
- **Performance**: Optimize critical code sections when necessary
- **Dependency management**: Add libraries only when essential

## Development Workflow

- **Version control**: Commit frequently with clear messages
- **Impact assessment**: Evaluate how changes affect other codebase areas
- **Documentation**: Keep documentation up-to-date for complex logic and features