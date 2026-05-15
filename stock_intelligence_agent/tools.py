import datetime
import logging
import os
from typing import Any, Dict, List, Optional
import json

import pandas as pd
import wikipedia
import yfinance as yf
import requests
from pydantic import ValidationError
from .models import VolatilityEvent, CorporateEvent, MacroEvent

from google.adk.tools.tool_context import ToolContext

logger = logging.getLogger(__name__)


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


def append_structured_state(
    tool_context: ToolContext, field: str, json_string: str
) -> Dict[str, str]:
    """Parse and append structured data to a state field.

    Parse the provided JSON string, validate it against the appropriate model based on the field,
    and append the validated data to the specified state field.

    Args:
        tool_context (ToolContext): The execution context containing the state.
        field (str): The state field name to append data to.
        json_string (str): The JSON string to parse and append.

    Returns:
        Dict[str, str]: A dictionary indicating the success status of the operation.
    """
    try:
        data = json.loads(json_string)

        if field == "STOCK_DATA":
            model = VolatilityEvent
        elif field == "CORP_HISTORY":
            model = CorporateEvent
        elif field == "MACRO_HISTORY":
            model = MacroEvent
        else:
            return {
                "status": "error",
                "message": f"Unsupported field for structured state: {field}",
            }

        if isinstance(data, list):
            validated_data = [model(**item).model_dump() for item in data]
        else:
            validated_data = [model(**data).model_dump()]

        existing_state = tool_context.state.get(field, [])
        tool_context.state[field] = existing_state + validated_data
        logger.info(f"Successfully appended structured data to state field '{field}'.")
        return {"status": "success"}
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON string: {e}")
        return {"status": "error", "message": f"Invalid JSON format: {str(e)}"}
    except ValidationError as e:
        logger.error(f"Validation error against schema: {e}")
        return {"status": "error", "message": f"Schema validation failed: {str(e)}"}
    except Exception as e:
        logger.error(f"Unexpected error in append_structured_state: {e}")
        return {"status": "error", "message": f"Unexpected error: {str(e)}"}


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
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    logger.info(
        f"Initiating file write operation to directory: {directory}, filename: {filename}"
    )
    # Prevent path traversal vulnerabilities
    filename = os.path.basename(filename)
    name, _ = os.path.splitext(filename)
    filename = f"{name}_{timestamp}.md"
    target_path: str = os.path.join(directory, filename)
    os.makedirs(os.path.dirname(target_path), exist_ok=True)

    with open(target_path, "w", encoding="utf-8") as f:
        f.write(content)

    logger.info(f"Successfully wrote file to {target_path}")
    return {"status": "success"}


def get_wikipedia_section(title: str, section_title: Optional[str] = None) -> str:
    """
    Fetch a specific section of a Wikipedia page or list available sections.

    Args:
        title (str): The title of the Wikipedia page.
        section_title (Optional[str]): The specific section to extract.
            If None, returns a list of all available sections.

    Returns:
        str: The content of the section, or a list of sections, or an error message.
    """
    import re

    logger.info(f"Fetching Wikipedia section for: {title}, section: {section_title}")
    try:
        wikipedia.set_user_agent("corporation_consultant/1.0 (contact@example.com)")
        search = wikipedia.search(title)
        if not search:
            return f"No results found for '{title}'."
        page = wikipedia.page(search[0], auto_suggest=False)
        content = page.content

        # Simple regex to split sections (== Section Title ==)
        sections = re.split(r"\n==+ (.*?) ==+\n", content)

        # sections[0] is the summary (before the first section)
        available_sections = [sections[i] for i in range(1, len(sections), 2)]

        if section_title is None:
            if not available_sections:
                return "No sections found. The page might be too short."
            return "Available sections:\n" + "\n".join(available_sections)

        # Look for the specific section
        for i in range(1, len(sections), 2):
            if sections[i].strip().lower() == section_title.strip().lower():
                return sections[i + 1].strip()

        return (
            f"Section '{section_title}' not found on page '{page.title}'. Available sections:\n"
            + "\n".join(available_sections)
        )

    except wikipedia.exceptions.DisambiguationError as e:
        return f"Disambiguation error: '{title}' may refer to {e.options[:5]}..."
    except wikipedia.exceptions.PageError:
        return f"Page '{title}' not found."
    except Exception as e:
        return f"Error fetching Wikipedia page: {str(e)}"


def get_sec_filing_dates(ticker: str) -> str:
    """
    Fetch the recent 10-K and 10-Q filing dates for a given ticker from SEC EDGAR.

    Args:
        ticker (str): The stock symbol (e.g., 'AAPL').

    Returns:
        str: A formatted string of recent filing dates and forms.
    """
    headers = {"User-Agent": "AgenticStockSystem contact@example.com"}

    try:
        # Get company tickers to map ticker to CIK
        tickers_url = "https://www.sec.gov/files/company_tickers.json"
        response = requests.get(tickers_url, headers=headers)
        response.raise_for_status()
        tickers_data = response.json()

        cik = None
        for item in tickers_data.values():
            if item["ticker"].upper() == ticker.upper():
                cik = str(item["cik_str"]).zfill(10)
                break

        if not cik:
            return f"Error: Could not find CIK for ticker {ticker}"

        # Get recent submissions
        submissions_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        sub_response = requests.get(submissions_url, headers=headers)
        sub_response.raise_for_status()
        sub_data = sub_response.json()

        recent_filings = sub_data.get("filings", {}).get("recent", {})
        if not recent_filings:
            return f"No recent filings found for {ticker}"

        forms = recent_filings.get("form", [])
        dates = recent_filings.get("filingDate", [])

        results = []
        for i in range(len(forms)):
            if forms[i] in ["10-K", "10-Q"]:
                results.append(f"{dates[i]}: {forms[i]}")
                if len(results) >= 20:  # Limit to top 20
                    break

        if not results:
            return f"No recent 10-K or 10-Q filings found for {ticker}"

        return "Recent SEC Filings:\n" + "\n".join(results)

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching from SEC EDGAR: {e}")
        return f"Error connecting to SEC EDGAR: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error in get_sec_filing_dates: {e}")
        return f"Unexpected error: {str(e)}"


def get_stock_history(
    ticker: str, period: str = "20y", interval: str = "1mo"
) -> List[Dict[str, Any]]:
    """
    Fetch historical stock price data for a specified ticker symbol via Yahoo Finance.

    Args:
        ticker (str): The stock symbol (e.g., 'AAPL', 'TSLA').
        period (str): The time range to retrieve. Defaults to '20y'.
            Options include: '1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max'.
        interval (str): The frequency of data points. Defaults to '1mo'.
            Options include: '1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h',
            '1d', '5d', '1wk', '1mo', '3mo'.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries containing 'Date', 'Close', and 'Pct_Change' for the top 40 most volatile months.
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

    if isinstance(data.columns, pd.MultiIndex):
        close_series = data["Close"][ticker]
    else:
        close_series = data["Close"]

    history: pd.DataFrame = close_series.reset_index(name="Close")
    history.rename(columns={"index": "Date"}, inplace=True)

    # Standardize date formats based on the reporting interval
    if interval in ["1mo", "3mo"]:
        history["Date"] = history["Date"].dt.strftime("%Y-%m")
    else:
        history["Date"] = history["Date"].dt.strftime("%Y-%m-%d")

    # Calculate percentage change and absolute change
    history["Pct_Change"] = history["Close"].pct_change() * 100

    history = history.dropna(subset=["Pct_Change"])

    history["Abs_Change"] = history["Pct_Change"].abs()

    # Sort by absolute change descending and take top 40
    history = history.sort_values(by="Abs_Change", ascending=False).head(40)

    # Drop Abs_Change and sort chronologically
    history = history.drop(columns=["Abs_Change"]).sort_values(by="Date")

    logger.info(
        f"Successfully retrieved top 40 volatile data points for ticker {ticker}."
    )
    return history.to_dict(orient="records")
