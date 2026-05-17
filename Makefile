.PHONY: setup run run-web export-reqs test lint typecheck format check

setup:
	@echo "Setting up project environments using uv..."
	uv sync
	uv pip install pre-commit
	uv run pre-commit install
	mkdir -p logs
	mkdir -p corporate_reports
	@echo "Setup complete. Please ensure you have copied .env.example to .env and configured your variables."

export-reqs:
	@echo "Exporting pyproject.toml to requirements.txt..."
	uv pip compile pyproject.toml -o stock_intelligence_agent/requirements.txt
	@echo "Successfully exported to stock_intelligence_agent/requirements.txt"

test:
	@echo "Running tests..."
	PYTHONPATH=. uv run pytest tests/

run:
	@echo "Running the Corporate Explainer Agent in terminal mode..."
	GRPC_VERBOSITY=ERROR uv run adk run stock_intelligence_agent

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

check:
	@echo "Checking codebase..."
	uv run pre-commit run ruff --all-files || true
	uv run pre-commit run mypy --all-files || true
	uv run pre-commit run ruff-format --all-files || true
