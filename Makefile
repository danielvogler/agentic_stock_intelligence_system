.PHONY: setup run run-web export-reqs test lint typecheck format check

setup:
	@echo "Setting up project environments using uv..."
	uv sync
	uv pip install pre-commit
	uv run pre-commit install
	@echo "Setup complete. Please ensure you have copied .env.example to .env and configured your variables."

export-reqs:
	@echo "Exporting pyproject.toml to requirements.txt..."
	chmod +x scripts/export_requirements.sh
	./scripts/export_requirements.sh

run:
	@echo "Running the Corporate Explainer Agent in terminal mode..."
	GRPC_VERBOSITY=ERROR uv run adk run corporation_consultant

run-web:
	@echo "Running agents in web UI mode..."
	GRPC_VERBOSITY=ERROR uv run adk web

lint:
	@echo "Running linter..."
	uv run pre-commit run ruff --all-files

typecheck:
	@echo "Running type checker..."
	uv run pre-commit run mypy --all-files

format:
	@echo "Running formatter..."
	uv run pre-commit run ruff-format --all-files

check: lint typecheck format
	@echo "Checking codebase..."
	uv run pre-commit run --all-files
