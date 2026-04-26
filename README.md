# Agentic Stock Intelligence System

[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)

An advanced, multi-agent intelligence platform powered by the **Google Agent Development Kit (ADK)** and Vertex AI. This system autonomously researches a corporation's history and cross-references major strategic milestones against 20-year stock market data to generate deep, correlative financial insights.

## Architecture

The system utilizes an orchestrator loop where sub-agents concurrently gather data:
1.  **Corporate Researcher**: Identifies major historical events and mergers using Wikipedia.
2.  **Stock Analyst**: Gathers historical market data using Yahoo Finance.
3.  **Business Narrator**: Synthesizes the data into a clear analytical narrative.
4.  **File Writer**: Formats the final research document and exports it locally.

```mermaid
flowchart TD
    User([User Input: Company & Ticker]) --> RootAgent["root_agent<br>(corporate_consultant)"]
    RootAgent --> Team

    subgraph Team ["corporate_biographer_team (SequentialAgent)"]
        direction TB
        Loop["analysis_loop<br>(LoopAgent: max 2 iterations)"] --> Narrator[business_narrator]
        Narrator --> Writer[file_writer]

        subgraph ParallelResearch ["Parallel Research"]
            direction LR
            Researcher[corp_researcher]
            Analyst[stock_analyst]
        end
        Loop -.-> ParallelResearch
    end

    Writer --> Output([corporate_reports/company_biography.md])
```

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package and environment manager)
- Google Cloud Project with Vertex AI enabled
- Python 3.12+

## Installation

This project uses a Makefile for straightforward environment provisioning.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-org/stock-intelligence-agent.git
    cd stock-intelligence-agent
    ```

2.  **Run the setup target:**
    This command will use `uv` to build the virtual environment, install dependencies, and configure the pre-commit hooks.
    ```bash
    make setup
    ```

3.  **Configure Environment Variables:**
    Copy the sample environment file and insert your specific Google Cloud configurations.
    ```bash
    cp .env.example .env
    ```

4.  **Export Requirements (Optional):**
    If you require a strict `requirements.txt` for deployment outside of `uv`:
    ```bash
    make export-reqs
    ```

## Usage

The system can be initiated through two distinct interfaces using the Google ADK runner.

### Terminal Interface

To run the agent in your local terminal:

```bash
make run
```

### Web User Interface

To launch a local, interactive web-based interface:

```bash
make run-web
```

## CI/CD and Linting

This repository enforces strict adherence to PEP-8 via `ruff` and `mypy`. All code must pass the GitHub Actions CI pipeline testing the pre-commit hooks prior to merging.

To manually trigger the linting and formatting pipeline locally:
```bash
make check
```

To manually trigger the test suite:
```bash
make test
```

## License

See the `LICENSE` file for details.
