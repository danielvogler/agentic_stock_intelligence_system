from typing import Optional
from pydantic import BaseModel, Field


class VolatilityEvent(BaseModel):
    """Represents a significant stock volatility event.

    Attributes:
        date (str): The date of the event in YYYY-MM format.
        pct_change (float): The percentage change in stock price.
        description (Optional[str]): An optional description of the event.
    """

    date: str = Field(description="YYYY-MM format")
    pct_change: float
    description: Optional[str] = None


class CorporateEvent(BaseModel):
    """Represents a significant corporate event.

    Attributes:
        date (str): The date of the event in YYYY-MM format.
        event_summary (str): A summary of the corporate event.
        sec_filing (Optional[str]): An optional reference to an SEC filing.
    """

    date: str = Field(description="YYYY-MM format")
    event_summary: str
    sec_filing: Optional[str] = None


class MacroEvent(BaseModel):
    """Represents a significant macroeconomic event.

    Attributes:
        date (str): The date of the event in YYYY-MM format.
        spy_pct_change (float): The percentage change in the SPY ETF.
        macro_context (Optional[str]): An optional description of the macroeconomic context.
    """

    date: str = Field(description="YYYY-MM format")
    spy_pct_change: float
    macro_context: Optional[str] = None
