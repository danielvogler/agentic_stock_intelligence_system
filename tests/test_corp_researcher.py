import pytest
import json
from unittest.mock import MagicMock, patch
from google.adk.tools.tool_context import ToolContext
from langchain_community.utilities import WikipediaAPIWrapper
from stock_intelligence_agent.tools import append_structured_state


@pytest.fixture
def mock_wikipedia_api_wrapper():
    """Mocks the WikipediaAPIWrapper to return static content."""
    mock_wrapper = MagicMock(spec=WikipediaAPIWrapper)
    mock_wrapper.run.return_value = """
    Apple Inc. (AAPL) is an American multinational technology company headquartered in Cupertino, California.
    Key milestones include:
    - 2007: Introduction of the iPhone.
    - 2010: Launch of the iPad.
    - 2015: Release of the Apple Watch.
    - 2020: Transition to Apple Silicon for Mac computers.
    - 2023: Introduction of Apple Vision Pro.
    """
    return mock_wrapper


@pytest.fixture
def mock_tool_context():
    """Provides a mock ToolContext for testing."""
    context = MagicMock(spec=ToolContext)
    context.state = {"PROMPT": "Apple, AAPL", "CORP_HISTORY": []}
    return context


@patch("stock_intelligence_agent.tools.wikipedia")
def test_corp_researcher_gathers_milestones(
    mock_wikipedia_module, mock_tool_context, mock_wikipedia_api_wrapper
):
    """Tests if the corp_researcher agent correctly gathers milestones from Wikipedia."""
    mock_page = MagicMock()
    mock_page.content = (
        "\n== History ==\n"
        + mock_wikipedia_api_wrapper.run.return_value
        + "\n== Next ==\n"
    )
    mock_wikipedia_module.page.return_value = mock_page
    mock_wikipedia_module.search.return_value = ["Apple"]

    from stock_intelligence_agent.agent import get_wikipedia_section

    get_wikipedia_section(
        mock_tool_context.state["PROMPT"].split(",")[0].strip(), section_title="History"
    )

    json_output = json.dumps(
        [
            {
                "date": "2007-01",
                "event_summary": "Introduction of the iPhone.",
                "sec_filing": None,
            },
            {
                "date": "2023-06",
                "event_summary": "Introduction of Apple Vision Pro.",
                "sec_filing": None,
            },
        ]
    )

    append_structured_state(mock_tool_context, "CORP_HISTORY", json_output)

    assert "CORP_HISTORY" in mock_tool_context.state
    assert len(mock_tool_context.state["CORP_HISTORY"]) > 0
    assert "iPhone" in mock_tool_context.state["CORP_HISTORY"][0]["event_summary"]
    assert (
        "Apple Vision Pro"
        in mock_tool_context.state["CORP_HISTORY"][1]["event_summary"]
    )
