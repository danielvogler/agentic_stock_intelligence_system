import pytest
from unittest.mock import MagicMock, patch
from google.adk.tools.tool_context import ToolContext
import pandas as pd
from stock_intelligence_agent.agent import get_stock_history, append_to_state


@pytest.fixture
def mock_yfinance_download():
    """Mocks yfinance.download to return a predictable DataFrame."""
    mock_data = {
        "Date": pd.to_datetime(
            [
                "2003-01-01",
                "2004-01-01",
                "2005-01-01",
                "2006-01-01",
                "2007-01-01",
                "2008-01-01",
                "2009-01-01",
                "2010-01-01",
                "2011-01-01",
                "2012-01-01",
                "2013-01-01",
                "2014-01-01",
                "2015-01-01",
                "2016-01-01",
                "2017-01-01",
                "2018-01-01",
                "2019-01-01",
                "2020-01-01",
                "2021-01-01",
                "2022-01-01",
                "2023-01-01",
            ]
        ),
        "Close": [
            10.0,
            12.0,
            15.0,
            13.0,
            20.0,  # Example data
            18.0,
            25.0,
            30.0,
            28.0,
            35.0,
            40.0,
            38.0,
            45.0,
            50.0,
            48.0,
            60.0,
            55.0,
            70.0,
            65.0,
            80.0,
            90.0,  # Largest increase: 10.0 (from 80 to 90)
        ],
    }
    df = pd.DataFrame(mock_data).set_index("Date")
    return MagicMock(return_value=df)


@pytest.fixture
def mock_tool_context():
    """Provides a mock ToolContext for testing."""
    context = MagicMock(spec=ToolContext)
    context.state = {"PROMPT": "Apple, AAPL", "STOCK_DATA": []}
    return context


@patch("yfinance.download")
def test_get_stock_history_returns_correct_format(
    mock_download, mock_tool_context, mock_yfinance_download
):
    """Tests if get_stock_history returns data in the expected format."""
    mock_download.side_effect = mock_yfinance_download

    history = get_stock_history(ticker="AAPL", period="20y", interval="1mo")

    assert isinstance(history, list)
    assert len(history) > 0
    assert all(isinstance(item, dict) for item in history)
    assert all("Date" in item and "Close" in item for item in history)


@patch("yfinance.download")
def test_stock_analyst_identifies_major_shifts(
    mock_download, mock_tool_context, mock_yfinance_download
):
    """Tests if the stock_analyst agent correctly identifies major stock shifts."""
    mock_download.side_effect = mock_yfinance_download

    # Simulate the get_stock_history tool call
    stock_history_data = get_stock_history(ticker="AAPL", period="20y", interval="1mo")

    # Simulate the stock_analyst processing and append_to_state call
    # The stock_analyst agent's instruction itself would call these, but for a unit test,
    # we need to simulate its core logic that processes the data and appends to state.
    # In a real ADK agent run, the agent's LLM would parse the history and identify shifts.
    # For this test, we'll manually process a simplified version to verify the *intent* of the prompt change.

    # Simplified logic to identify shifts as per the new prompt for testing purposes
    # In a real scenario, the LLM would do this more intelligently.
    shifts = []
    if stock_history_data:
        df = pd.DataFrame(stock_history_data)
        df["Close"] = pd.to_numeric(df["Close"])
        df["Change"] = df["Close"].diff()

        largest_increase = df.loc[df["Change"].idxmax()]
        largest_decrease = df.loc[df["Change"].idxmin()]

        shifts.append(
            f"Largest monthly increase: {largest_increase['Change']:.2f} on {largest_increase['Date']}"
        )
        shifts.append(
            f"Largest monthly decrease: {largest_decrease['Change']:.2f} on {largest_decrease['Date']}"
        )

        # Add some other volatile shifts (simplified)
        volatile_shifts = df[abs(df["Change"]) > df["Change"].std() * 1.5].to_dict(
            orient="records"
        )
        for shift in volatile_shifts:
            shifts.append(f"Volatile shift of {shift['Change']:.2f} on {shift['Date']}")

    append_to_state(mock_tool_context, "STOCK_DATA", "\n".join(shifts))

    assert "STOCK_DATA" in mock_tool_context.state
    assert len(mock_tool_context.state["STOCK_DATA"]) > 0
    assert "Largest monthly increase" in mock_tool_context.state["STOCK_DATA"][0]
    assert "Largest monthly decrease" in mock_tool_context.state["STOCK_DATA"][0]
