#!/usr/bin/env bash
# script/export_requirements.sh
# Uses uv to compile pyproject.toml dependencies into a requirements.txt file within the agent folder.

set -e

echo "Compiling requirements using uv..."
uv pip compile pyproject.toml -o corporation_consultant/requirements.txt
echo "Successfully exported to corporation_consultant/requirements.txt"
