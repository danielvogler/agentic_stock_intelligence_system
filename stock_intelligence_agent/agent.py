"""
Corporate Explainer Agent Module.

This module provides a multi-agent system utilizing Google Cloud and Vertex AI to
research a given corporation's history and correlate it with historical stock performance.
It orchestrates research, analysis, narrative generation, and document formatting.
"""

import logging
import os
from typing import Any, Dict, List, Optional

import google.cloud.logging
import pandas as pd
import vertexai
import yfinance as yf
from dotenv import load_dotenv
from google.adk import Agent
from google.adk.agents import LoopAgent, SequentialAgent
from google.adk.tools.langchain_tool import LangchainTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types
from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper

# Initialize environment variables
load_dotenv()

# Configure module-level logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Configuration and setup
project: Optional[str] = os.getenv("GOOGLE_CLOUD_PROJECT")
location: str = os.getenv("GOOGLE_CLOUD_LOCATION", "europe-west1")

# Initialize Google Cloud Logging if in Google Cloud environment
if project:
    try:
        cloud_logging_client = google.cloud.logging.Client(project=project)
        cloud_logging_client.setup_logging()
    except Exception as e:
        logger.warning(f"Failed to initialize Google Cloud Logging: {e}")

# Initialize Vertex AI
if project:
    vertexai.init(project=project, location=location)

os.environ["ADK_TRACE_ENABLED"] = "true"

model_name: Optional[str] = os.getenv("MODEL")
logger.info(f"Model initialized for: {model_name}")
logger.info(f"SDK initialized for project: {project} in location: {location}")


def append_to_state(
    tool_context: ToolContext, field: str, response: str
) -> Dict[str, str]:
    """
    Append new output to an existing state key within the tool context.

    Args:
        tool_context (ToolContext): The execution context containing the state.
        field (str): The state field name to append data to.
        response (str): The string response to append.

    Returns:
        Dict[str, str]: A dictionary indicating the success status of the operation.
    """
    existing_state: List[str] = tool_context.state.get(field, [])
    tool_context.state[field] = existing_state + [response]
    logger.info(f"Appended new record to state field '{field}'.")
    logger.debug(f"Record content for '{field}': {response}")
    return {"status": "success"}


def write_file(
    tool_context: ToolContext, directory: str, filename: str, content: str
) -> Dict[str, str]:
    """
    Write the provided content to a specified file directory and filename.

    Args:
        tool_context (ToolContext): The execution context.
        directory (str): The directory where the file will be saved.
        filename (str): The name of the file to create.
        content (str): The text content to write into the file.

    Returns:
        Dict[str, str]: A dictionary indicating the success status of the operation.
    """
    logger.info(
        f"Initiating file write operation to directory: {directory}, filename: {filename}"
    )
    target_path: str = os.path.join(directory, filename)
    os.makedirs(os.path.dirname(target_path), exist_ok=True)

    with open(target_path, "w", encoding="utf-8") as f:
        f.write(content)

    logger.info(f"Successfully wrote file to {target_path}")
    return {"status": "success"}


def get_stock_history(
    ticker: str, period: str = "20y", interval: str = "1mo"
) -> List[Dict[str, Any]]:
    """
    Fetch historical stock price data for a specified ticker symbol via Yahoo Finance.

    Args:
        ticker (str): The stock symbol (e.g., 'AAPL', 'TSLA').
        period (str): The time range to retrieve. Defaults to '10y'.
            Options include: '1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max'.
        interval (str): The frequency of data points. Defaults to '1mo'.
            Options include: '1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h',
            '1d', '5d', '1wk', '1mo', '3mo'.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries containing 'Date' and 'Close' price records.
    """
    logger.info(
        f"Fetching stock history for ticker: {ticker}, "
        f"period: {period}, interval: {interval}"
    )

    data: pd.DataFrame = yf.download(
        ticker, period=period, interval=interval, progress=False
    )

    if data.empty:
        logger.warning(f"No stock data found for ticker: {ticker}")
        return []

    # Format the dataframe
    history: pd.DataFrame = data[["Close"]].reset_index()
    history.columns = ["Date", "Close"]

    # Standardize date formats based on the reporting interval
    if interval in ["1mo", "3mo"]:
        history["Date"] = history["Date"].dt.strftime("%Y-%m")
    else:
        history["Date"] = history["Date"].dt.strftime("%Y-%m-%d")

    logger.info(
        f"Successfully retrieved {len(history)} data points for ticker {ticker}."
    )
    return history.to_dict(orient="records")


# ---------------------------------------------------------------------------
# Agent Definitions
# ---------------------------------------------------------------------------

# Formats the final research output and writes it to a file.
file_writer: Agent = Agent(
    name="report_writer",
    model=model_name,
    description="Formats the final corporate biography and saves it as a text file.",
    instruction="""
    INSTRUCTIONS:
    - Create a professional title for the report based on the company name in the PROMPT.
    - Use your 'write_file' tool to create a new .md file with the following arguments:
        - filename: Use a slugified version of the company name (e.g., 'apple_biography.md').
        - directory: Write to the 'corporate_reports' directory.
        - content: Construct a formal report including:
            1. EXECUTIVE SUMMARY (from FINAL_STORY)
            2. HISTORICAL MILESTONES (from CORP_HISTORY)
            3. FINANCIAL DATA POINTS (from STOCK_DATA)

    PROMPT:
    { PROMPT? }

    FINAL_STORY:
    { FINAL_STORY? }

    CORP_HISTORY:
    { CORP_HISTORY? }

    STOCK_DATA:
    { STOCK_DATA? }

    NEVER use a tool named 'transfer_to_orchestrator'.
    """,
    generate_content_config=types.GenerateContentConfig(
        temperature=0.0,
    ),
    tools=[write_file],
)

# Researches company milestones using Wikipedia.
corp_researcher: Agent = Agent(
    name="corp_researcher",
    model=model_name,
    description="Researches company history and major news events.",
    instruction="""
    Use Wikipedia to find a *large and comprehensive list* of major milestones for the company in { PROMPT } from the *last 20 years*. Identify all significant milestones, including but not limited to, mergers, acquisitions, leadership changes, major product launches, significant legal events, and major financial announcements. Prioritize quantity and detail to ensure a comprehensive list is gathered, not limited to a specific number or a few key events.
    Do NOT attempt to correlate events with stock performance; that is handled by another agent.
    Use 'append_to_state' to add findings to the 'CORP_HISTORY' field.
    NEVER use a tool named 'transfer_to_orchestrator'.
    """,
    tools=[
        LangchainTool(tool=WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper())),
        append_to_state,
    ],
)

# Retrieves and processes stock market data for analysis.
stock_analyst: Agent = Agent(
    name="stock_analyst",
    model=model_name,
    description="Pulls and interprets monthly stock data.",
    instruction="""
    Use 'get_stock_history' for the ticker in { PROMPT }.
    Analyze the historical stock data over the 20-year period to identify ALL major volatile stock shifts, both upward and downward. For each shift, provide the date and the percentage change. Crucially, explicitly identify and highlight the single absolute largest monthly increase and the single absolute largest monthly decrease in the entire dataset, including their dates and magnitudes. Do NOT predict future price movements.
    Use 'append_to_state' to add these findings to the 'STOCK_DATA' field.
    Do NOT attempt to transfer control to another agent; that is handled by the orchestrating agents.
    NEVER use a tool named 'transfer_to_orchestrator'.
    """,
    tools=[get_stock_history, append_to_state],
)

# Analyzes research data to compose a narrative linking events to market performance.
business_narrator: Agent = Agent(
    name="business_narrator",
    model=model_name,
    description="Combines history and stock data into a cohesive analytical narrative.",
    instruction="""
    Synthesize the information from CORP_HISTORY (company milestones) and STOCK_DATA (significant stock price shifts) into a comprehensive and professional narrative.
    The narrative must explicitly explain how *specific corporate milestones* (e.g., product launches, acquisitions, leadership changes, major financial announcements) directly influenced the stock price movements *around their respective dates*, rather than just discussing generic multi-year trends. Provide detailed explanations for these correlations.
    Pay special attention to correlating corporate milestones specifically to the absolute largest single monthly stock increase and the absolute largest single monthly stock decrease identified in STOCK_DATA, providing in-depth, detailed explanations for these extreme shifts.
    Store this final, synthesized narrative in the 'FINAL_STORY' field.
    NEVER use a tool named 'transfer_to_orchestrator'.
    """,
    tools=[append_to_state],
)

# Orchestrates the concurrent operation of research and analysis agents.
analysis_loop: LoopAgent = LoopAgent(
    name="analysis_loop", sub_agents=[corp_researcher, stock_analyst], max_iterations=2
)

# Sequential pipeline coordinating the end-to-end report generation process.
corporate_biographer_team: SequentialAgent = SequentialAgent(
    name="corporate_biographer_team",
    sub_agents=[analysis_loop, business_narrator, file_writer],
)

# Main entrypoint agent handling user interaction and state initialization.
root_agent: Agent = Agent(
    name="corporate_consultant",
    model=model_name,
    description="Initializes the corporate biography research process.",
    instruction="""
    INSTRUCTIONS:
    - Greet the user professionally and state your capability to research
      corporate history and correlate it with stock performance.
    - Ask the user to provide the name of a company and its stock ticker symbol (e.g., Apple, AAPL).
    - Upon receiving the company and ticker, utilize the 'append_to_state' tool to:
        1. Store the provided input in the 'PROMPT' field.
    - Following state storage, transfer control to the 'corporate_biographer_team'.
    """,
    generate_content_config=types.GenerateContentConfig(
        temperature=0.0,
    ),
    tools=[append_to_state],
    sub_agents=[corporate_biographer_team],
)
