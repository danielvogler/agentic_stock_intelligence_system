"""
Corporate Explainer Agent Module.

This module provides a multi-agent system utilizing Google Cloud and Vertex AI to
research a given corporation's history and correlate it with historical stock performance.
It orchestrates research, analysis, narrative generation, and document formatting.
"""

import logging
import os
from typing import Optional

import google.cloud.logging
import vertexai
from dotenv import load_dotenv
from google.adk import Agent
from google.adk.agents import LoopAgent, SequentialAgent
from google.genai import types

from .tools import (
    append_structured_state,
    append_to_state,
    get_sec_filing_dates,
    get_stock_history,
    get_wikipedia_section,
    write_file,
)

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

model_name: Optional[str] = os.getenv("MODEL", "gemini-2.5-flash")
logger.info(f"Model initialized for: {model_name}")
logger.info(f"SDK initialized for project: {project} in location: {location}")

# ---------------------------------------------------------------------------
# Agent Definitions
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
    - Use your 'write_file' tool to create a new .md (Markdown) file with the following arguments:
        - filename: Use a slugified version of the company name (e.g., 'apple_biography').
        - directory: Write to the 'corporate_reports' directory.
        - content: Construct a formal report including:
            1. EXECUTIVE SUMMARY (from FINAL_STORY)
            2. HISTORICAL MILESTONES (from CORP_HISTORY)
            3. FINANCIAL DATA POINTS (from STOCK_DATA)
            4. MACROECONOMIC CONTEXT (from MACRO_HISTORY)

    PROMPT:
    { PROMPT? }

    FINAL_STORY:
    { FINAL_STORY? }

    CORP_HISTORY:
    { CORP_HISTORY? }

    STOCK_DATA:
    { STOCK_DATA? }

    MACRO_HISTORY:
    { MACRO_HISTORY? }

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
    description="Researches company history and major news events based on stock volatility dates.",
    instruction="""
    Read the exact dates from the STOCK_DATA state:
    { STOCK_DATA? }

    Use the 'get_wikipedia_section' tool to explicitly search for corporate events that happened during those exact months for the company in { PROMPT }.
    You can now list available sections by calling the tool without a section_title, and then extract specific sections by providing the section_title.
    Also use the 'get_sec_filing_dates' tool to check if SEC EDGAR earnings filings (10-K/10-Q) correlate with the volatility spikes.
    Append the causally linked event findings to the 'CORP_HISTORY' state field using 'append_structured_state'.
    You MUST format your output as a JSON list matching the CorporateEvent schema:
    [
      {
        "date": "YYYY-MM",
        "event_summary": "Summary of the event",
        "sec_filing": "Optional SEC filing info"
      }
    ]
    NEVER use a tool named 'transfer_to_orchestrator'.
    """,
    tools=[
        get_wikipedia_section,
        get_sec_filing_dates,
        append_structured_state,
    ],
)

# Retrieves and processes stock market data for analysis.
stock_analyst: Agent = Agent(
    name="stock_analyst",
    model=model_name,
    description="Pulls and interprets monthly stock data.",
    instruction="""
    Use 'get_stock_history' for the ticker in { PROMPT }.
    The tool automatically returns the top 40 most volatile months. Extract the top 10 largest stock volatility spikes from this pre-filtered list (include exact dates (YYYY-MM) and percentages).
    Append these dates and percentages to the 'STOCK_DATA' state field using 'append_structured_state'.
    You MUST format your output as a JSON list matching the VolatilityEvent schema:
    [
      {
        "date": "YYYY-MM",
        "pct_change": 12.34,
        "description": "Optional description"
      }
    ]
    Do NOT attempt to transfer control to another agent; that is handled by the orchestrating agents.
    NEVER use a tool named 'transfer_to_orchestrator'.
    """,
    tools=[get_stock_history, append_structured_state],
)

# Analyzes macroeconomic trends to provide broader market context.
macro_economist: Agent = Agent(
    name="macro_economist",
    model=model_name,
    description="Analyzes macroeconomic trends to provide broader market context.",
    instruction="""
    Read the volatile dates from STOCK_DATA. Use 'get_stock_history' with ticker 'SPY' to find the S&P 500 percentage change for those exact same months. Compare the company's performance against the broader market. Append your analysis to the 'MACRO_HISTORY' state field using 'append_structured_state'.
    You MUST format your output as a JSON list matching the MacroEvent schema:
    [
      {
        "date": "YYYY-MM",
        "spy_pct_change": 1.23,
        "macro_context": "Optional context"
      }
    ]

    STOCK_DATA:
    { STOCK_DATA? }

    NEVER use a tool named 'transfer_to_orchestrator'.
    """,
    tools=[get_stock_history, append_structured_state],
)

# Analyzes research data to compose a narrative linking events to market performance.
business_narrator: Agent = Agent(
    name="business_narrator",
    model=model_name,
    description="Combines history and stock data into a cohesive analytical narrative.",
    instruction="""
    Receive the perfectly matched causal data from CORP_HISTORY and STOCK_DATA below:

    CORP_HISTORY:
    { CORP_HISTORY? }

    STOCK_DATA:
    { STOCK_DATA? }

    MACRO_HISTORY:
    { MACRO_HISTORY? }

    Write a crisp final Markdown-formatted report outlining 5-10 major shifts in company projects/events with corresponding stock changes.
    Explicitly mention the "largest monthly increase" and "largest monthly decrease" in your report.
    Also use the MACRO_HISTORY to provide a more sophisticated report (e.g., "Apple dropped 30%, but the broader market dropped 25%").
    Store this final, synthesized narrative in the 'FINAL_STORY' field using 'append_to_state'.
    NEVER use a tool named 'transfer_to_orchestrator'.
    """,
    tools=[append_to_state],
)

# Orchestrates the concurrent operation of research and analysis agents.
analysis_loop: LoopAgent = LoopAgent(
    name="analysis_loop",
    sub_agents=[stock_analyst, corp_researcher, macro_economist],
    max_iterations=1,
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
    - You are a corporate consultant capable of researching corporate history and correlating it with stock performance.
    - If the user provides a company name and stock ticker symbol (e.g., Apple Inc., AAPL), you MUST IMMEDIATELY use the 'append_to_state' tool to store the provided input in the 'PROMPT' field.
    - After calling 'append_to_state', you MUST IMMEDIATELY use the `transfer_to_corporate_biographer_team` tool to transfer control. Do not ask any questions if the user has already provided the ticker.
    """,
    generate_content_config=types.GenerateContentConfig(
        temperature=0.0,
    ),
    tools=[append_to_state],
    sub_agents=[corporate_biographer_team],
)
