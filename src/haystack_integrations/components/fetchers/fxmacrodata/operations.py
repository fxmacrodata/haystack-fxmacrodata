# SPDX-FileCopyrightText: 2026-present FXMacroData <info@fxmacrodata.com>
#
# SPDX-License-Identifier: Apache-2.0

from dataclasses import dataclass, field
from string import Formatter
from typing import Any


@dataclass(frozen=True)
class Operation:
    """
    A read-only FXMacroData REST endpoint.

    :param path: Path template relative to the API base URL, e.g. `/calendar/{currency}`.
    :param description: Description shown to LLMs when the operation is exposed as a tool.
    :param parameters: JSON schema of the arguments accepted by the operation.
    :param page_size: Largest `limit` the endpoint accepts. `None` means the endpoint is not paginated.
    """

    path: str
    description: str
    parameters: dict[str, Any]
    page_size: int | None = None
    path_params: tuple[str, ...] = field(init=False)

    def __post_init__(self) -> None:
        names = tuple(name for _, name, _, _ in Formatter().parse(self.path) if name)
        object.__setattr__(self, "path_params", names)


_CURRENCY = {"type": "string", "description": "Three-letter currency code, for example USD, EUR or JPY."}
_INDICATOR = {
    "type": "string",
    "description": "Indicator slug as listed by the data catalogue, for example inflation, policy_rate or gdp.",
}
_START = {"type": "string", "description": "Inclusive start date, YYYY-MM-DD."}
_END = {"type": "string", "description": "Inclusive end date, YYYY-MM-DD."}
_LIMIT = {"type": "integer", "minimum": 1, "description": "Maximum number of rows to return."}
_OFFSET = {"type": "integer", "minimum": 0, "description": "Number of rows to skip."}

_ACCESS = " USD is readable without an API key; other currencies need a key."


def _schema(required: list[str], **properties: dict[str, Any]) -> dict[str, Any]:
    return {"type": "object", "properties": properties, "required": required}


OPERATIONS: dict[str, Operation] = {
    "data_catalogue": Operation(
        path="/data_catalogue/{currency}",
        description="List the macroeconomic indicators available for a currency, with units, frequency and coverage."
        + _ACCESS,
        parameters=_schema(["currency"], currency=_CURRENCY),
    ),
    "indicator_history": Operation(
        path="/announcements/{currency}/{indicator}",
        description=(
            "Get the release history of one macroeconomic indicator, each row with its value (`val`, may be null), "
            "period date, announcement time and official source." + _ACCESS
        ),
        parameters=_schema(
            ["currency", "indicator"],
            currency=_CURRENCY,
            indicator=_INDICATOR,
            start_date=_START,
            end_date=_END,
            revisions={
                "type": "string",
                "enum": ["latest", "first", "final", "all"],
                "description": "Revision view: latest values, first prints, final values or every vintage.",
            },
            limit=_LIMIT,
            offset=_OFFSET,
        ),
        page_size=100,
    ),
    "latest_announcements": Operation(
        path="/announcements/{currency}/latest",
        description="Get the most recent released value of every indicator for a currency." + _ACCESS,
        parameters=_schema(["currency"], currency=_CURRENCY),
    ),
    "release_calendar": Operation(
        path="/calendar/{currency}",
        description="Get scheduled economic data release dates and times for a currency." + _ACCESS,
        parameters=_schema(
            ["currency"],
            currency=_CURRENCY,
            indicator={"type": "string", "description": "Only return releases of this indicator slug."},
            start_date=_START,
            end_date=_END,
            timezone={"type": "string", "description": "IANA timezone for an extra local timestamp field."},
        ),
    ),
    "forex": Operation(
        path="/forex/{base}/{quote}",
        description="Get daily FX spot rates for a currency pair. Requires an API key.",
        parameters=_schema(
            ["base", "quote"],
            base={"type": "string", "description": "Base currency code, for example EUR."},
            quote={"type": "string", "description": "Quote currency code, for example USD."},
            start_date=_START,
            end_date=_END,
            limit=_LIMIT,
            offset=_OFFSET,
        ),
        page_size=100,
    ),
    "event_predictions": Operation(
        path="/predictions/{currency}/{indicator}",
        description="Get forecasts for upcoming releases of one indicator, with their source. Requires an API key.",
        parameters=_schema(
            ["currency", "indicator"],
            currency=_CURRENCY,
            indicator=_INDICATOR,
            start_date=_START,
            end_date=_END,
            limit=_LIMIT,
            offset=_OFFSET,
        ),
        page_size=100,
    ),
    "commodities": Operation(
        path="/commodities/{indicator}",
        description="Get commodity and energy price history. Requires an API key.",
        parameters=_schema(
            ["indicator"],
            indicator={
                "type": "string",
                "enum": [
                    "crude_oil_inventories",
                    "gold",
                    "natural_gas",
                    "natural_gas_storage",
                    "oil_brent",
                    "oil_wti",
                    "platinum",
                    "silver",
                ],
                "description": "Commodity slug.",
            },
            start_date=_START,
            end_date=_END,
            limit=_LIMIT,
            offset=_OFFSET,
        ),
        page_size=100,
    ),
    "cot": Operation(
        path="/cot/{currency}",
        description="Get weekly CFTC Commitments of Traders positioning for a currency's futures contract." + _ACCESS,
        parameters=_schema(
            ["currency"], currency=_CURRENCY, start_date=_START, end_date=_END, limit=_LIMIT, offset=_OFFSET
        ),
        page_size=100,
    ),
    "press_releases": Operation(
        path="/press-releases/{currency}",
        description="Get recent press releases published by the central bank of a currency." + _ACCESS,
        parameters=_schema(["currency"], currency=_CURRENCY, limit=_LIMIT, offset=_OFFSET),
        page_size=50,
    ),
}
