import os
import importlib
from unittest.mock import patch, MagicMock

from stock_intelligence_agent import agent
from stock_intelligence_agent.agent import (
    write_file,
    get_stock_history,
    corporate_biographer_team,
)
from google.adk.agents import LoopAgent, SequentialAgent


def test_write_file_path_traversal():
    """Tests that write_file prevents path traversal vulnerabilities."""
    tool_context = MagicMock()
    # Write a file using a malicious path
    directory = "/tmp/safe_dir"
    filename = "../../../evil.txt"
    content = "malicious content"

    with patch("os.makedirs"), patch("builtins.open") as mock_open:
        write_file(tool_context, directory, filename, content)

        called_args = mock_open.call_args[0]
        actual_path = called_args[0]

        assert actual_path.startswith(os.path.join(directory, "evil_"))
        assert actual_path.endswith(".md")

        mock_open.return_value.__enter__.return_value.write.assert_called_once_with(
            content
        )


def test_get_stock_history_data_format():
    """Tests that get_stock_history returns data in the correct format."""
    import re

    # Hit live API against yfinance to prove the 20-year history pipeline works
    history = get_stock_history("AAPL", interval="1mo", period="20y")
    assert isinstance(history, list)
    assert len(history) > 0
    date_pattern = re.compile(r"^\d{4}-\d{2}$")
    for record in history:
        assert isinstance(record, dict)
        assert set(record.keys()) == {"Date", "Close", "Pct_Change"}
        assert date_pattern.match(
            record["Date"]
        ), f"Date {record['Date']} does not match YYYY-MM format"


def test_agent_orchestration_structure():
    """Tests the structure of the corporate_biographer_team agent."""
    assert isinstance(corporate_biographer_team, SequentialAgent)
    assert len(corporate_biographer_team.sub_agents) == 3

    # 1. analysis_loop
    assert isinstance(corporate_biographer_team.sub_agents[0], LoopAgent)
    assert corporate_biographer_team.sub_agents[0].name == "analysis_loop"

    # 2. business_narrator
    assert corporate_biographer_team.sub_agents[1].name == "business_narrator"

    # 3. file_writer
    assert corporate_biographer_team.sub_agents[2].name == "report_writer"


def test_environment_fallback_logic():
    """Tests the environment fallback logic in the agent module."""
    with patch.dict(os.environ, {}, clear=True):
        mock_env = {
            "GOOGLE_CLOUD_PROJECT": "dummy-project",
            "GOOGLE_CLOUD_LOCATION": "europe-west1",
        }
        with patch.dict(os.environ, mock_env, clear=True):
            with patch("vertexai.init"):
                with patch("google.cloud.logging.Client"):
                    with patch("dotenv.load_dotenv"):
                        importlib.reload(agent)
                        assert agent.model_name == "gemini-2.5-flash"
