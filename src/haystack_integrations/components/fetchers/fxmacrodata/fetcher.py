# SPDX-FileCopyrightText: 2026-present FXMacroData <info@fxmacrodata.com>
#
# SPDX-License-Identifier: Apache-2.0

import json
from typing import Any

import requests
from haystack import Document, component, default_from_dict, default_to_dict, logging
from haystack.utils import Secret, deserialize_secrets_inplace
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from haystack_integrations.components.fetchers.fxmacrodata.operations import OPERATIONS

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.fxmacrodata.com/v1"


class FXMacroDataError(Exception):
    """Raised when the FXMacroData API answers with an error status."""

    def __init__(self, message: str, status_code: int, code: str | None = None) -> None:
        """
        Create the error.

        :param message: Human-readable message, taken from the API response when available.
        :param status_code: HTTP status code of the response.
        :param code: Machine-readable error code from the API response, e.g. `api_key_required`.
        """
        super().__init__(message)
        self.status_code = status_code
        self.code = code


@component
class FXMacroDataFetcher:
    """
    Fetch FXMacroData macroeconomic, release-calendar and FX data as Haystack Documents.

    Each returned row becomes one Document whose `content` is the row serialized as JSON, unchanged.
    Scalar fields of the row (for example `date`, `val` and `source_url`) are copied into `Document.meta`
    so they can be used in filters. A `val` of `null` means the source published no value; it is kept as is.

    Paginated endpoints are read page by page with `limit`/`offset` until the API reports no more rows or
    `max_records` rows have been collected.

    USD data is readable without an API key (the most recent 90 days of history, with releases delayed by
    15 minutes). Other currencies, FX rates, commodities and predictions need a key from
    [fxmacrodata.com](https://fxmacrodata.com/subscribe).

    ### Usage example

    ```python
    from haystack_integrations.components.fetchers.fxmacrodata import FXMacroDataFetcher

    fetcher = FXMacroDataFetcher(operation="indicator_history")
    result = fetcher.run(arguments={"currency": "USD", "indicator": "inflation"})
    documents = result["documents"]
    ```
    """

    def __init__(
        self,
        operation: str = "indicator_history",
        api_key: Secret = Secret.from_env_var("FXMACRODATA_API_KEY", strict=False),
        *,
        max_records: int = 500,
        timeout: float = 30.0,
        max_retries: int = 3,
        base_url: str = DEFAULT_BASE_URL,
    ) -> None:
        """
        Initialize the FXMacroDataFetcher component.

        :param operation:
            Endpoint to call. One of `data_catalogue`, `indicator_history`, `latest_announcements`,
            `release_calendar`, `forex`, `event_predictions`, `commodities`, `cot` or `press_releases`.
        :param api_key:
            FXMacroData API key, sent in the `X-API-Key` header. Defaults to the `FXMACRODATA_API_KEY`
            environment variable. When it is not set, requests are made without a key and only USD data is readable.
        :param max_records:
            Upper bound on the rows collected from a paginated endpoint when the run arguments have no `limit`.
        :param timeout:
            Timeout in seconds for each HTTP request.
        :param max_retries:
            Retries for connection errors and 429/5xx responses, with exponential backoff.
        :param base_url:
            API base URL.
        :raises ValueError: If `operation` is unknown or `max_records` is lower than 1.
        """
        if operation not in OPERATIONS:
            msg = f"Unknown operation '{operation}'. Choose one of: {', '.join(OPERATIONS)}."
            raise ValueError(msg)
        if max_records < 1:
            msg = "max_records must be at least 1."
            raise ValueError(msg)
        self.operation = operation
        self.api_key = api_key
        self.max_records = max_records
        self.timeout = timeout
        self.max_retries = max_retries
        self.base_url = base_url.rstrip("/")
        self._session: requests.Session | None = None

    def warm_up(self) -> None:
        """Create the HTTP session. Called automatically on first run."""
        if self._session is None:
            retry = Retry(
                total=self.max_retries,
                backoff_factor=0.5,
                status_forcelist=(429, 500, 502, 503, 504),
                allowed_methods=frozenset({"GET"}),
                raise_on_status=False,
            )
            session = requests.Session()
            session.mount("https://", HTTPAdapter(max_retries=retry))
            session.mount("http://", HTTPAdapter(max_retries=retry))
            session.headers["Accept"] = "application/json"
            key = self.api_key.resolve_value()
            if key:
                session.headers["X-API-Key"] = key
            self._session = session

    def close(self) -> None:
        """Close the HTTP session."""
        if self._session is not None:
            self._session.close()
            self._session = None

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize this component to a dictionary.

        :returns: Dictionary with serialized data.
        """
        return default_to_dict(
            self,
            operation=self.operation,
            api_key=self.api_key.to_dict(),
            max_records=self.max_records,
            timeout=self.timeout,
            max_retries=self.max_retries,
            base_url=self.base_url,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FXMacroDataFetcher":
        """
        Deserialize this component from a dictionary.

        :param data: Dictionary to deserialize from.
        :returns: Deserialized component.
        """
        deserialize_secrets_inplace(data["init_parameters"], keys=["api_key"])
        return default_from_dict(cls, data)

    @component.output_types(documents=list[Document], meta=dict[str, Any])
    def run(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """
        Call the configured endpoint and return its rows as Documents.

        :param arguments:
            Path and query parameters of the endpoint, e.g. `{"currency": "USD", "indicator": "inflation"}`.
            For paginated endpoints `limit` is the total number of rows wanted and `offset` the first row.
        :returns: A dictionary with:
            - `documents`: One Document per returned row.
            - `meta`: The response fields other than the rows, such as `pagination`, `source` or `freemium_delay`.
        :raises ValueError: If a path parameter is missing from `arguments`.
        :raises FXMacroDataError: If the API answers with an error status, for example 403 when a key is required.
        """
        self.warm_up()
        operation = OPERATIONS[self.operation]
        params = {key: value for key, value in arguments.items() if value is not None}
        missing = [name for name in operation.path_params if name not in params]
        if missing:
            msg = f"Missing required argument(s) for {self.operation}: {', '.join(missing)}."
            raise ValueError(msg)
        path = operation.path.format(**{name: params.pop(name) for name in operation.path_params})

        if operation.page_size is None:
            records, meta = self._split(self._get(path, params))
        else:
            records, meta = self._get_pages(path, params, operation.page_size)

        documents = []
        for record in records:
            doc_meta = {k: v for k, v in record.items() if v is None or isinstance(v, str | int | float | bool)}
            doc_meta["operation"] = self.operation
            documents.append(Document(content=json.dumps(record, ensure_ascii=False), meta=doc_meta))
        return {"documents": documents, "meta": meta}

    def _get_pages(
        self, path: str, params: dict[str, Any], page_size: int
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        wanted = int(params.pop("limit", self.max_records))
        offset = int(params.pop("offset", 0))
        records: list[dict[str, Any]] = []
        meta: dict[str, Any] = {}
        while len(records) < wanted:
            payload = self._get(path, {**params, "limit": min(page_size, wanted - len(records)), "offset": offset})
            page, page_meta = self._split(payload)
            # keep the first page's metadata, but report where pagination ended
            meta = meta or page_meta
            meta["pagination"] = page_meta.get("pagination")
            records.extend(page)
            pagination = page_meta.get("pagination") or {}
            if not page or not pagination.get("has_more"):
                break
            next_offset = pagination.get("next_offset")
            offset = next_offset if isinstance(next_offset, int) and next_offset > offset else offset + len(page)
        return records, meta

    def _get(self, path: str, params: dict[str, Any]) -> Any:
        if self._session is None:
            msg = "The component was not warmed up."
            raise RuntimeError(msg)
        query = {key: str(value).lower() if isinstance(value, bool) else value for key, value in params.items()}
        response = self._session.get(f"{self.base_url}{path}", params=query, timeout=self.timeout)
        if response.status_code >= 400:  # noqa: PLR2004
            raise self._error(response)
        return response.json()

    @staticmethod
    def _error(response: requests.Response) -> FXMacroDataError:
        detail: str | None = None
        code: str | None = None
        try:
            body = response.json()
        except ValueError:
            body = None
        if isinstance(body, dict):
            detail = body.get("detail") if isinstance(body.get("detail"), str) else None
            code = body.get("code") if isinstance(body.get("code"), str) else None
        message = f"FXMacroData request failed with HTTP {response.status_code}"
        if code:
            message += f" ({code})"
        if detail:
            message += f": {detail}"
        return FXMacroDataError(message, status_code=response.status_code, code=code)

    def _split(self, payload: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Separate the rows of a response from its metadata."""
        if isinstance(payload, list):
            return [row for row in payload if isinstance(row, dict)], {}
        if not isinstance(payload, dict):
            return [], {}
        data = payload.get("data")
        if isinstance(data, list):
            return [row for row in data if isinstance(row, dict)], {k: v for k, v in payload.items() if k != "data"}
        if self.operation == "data_catalogue":
            # the catalogue is keyed by indicator slug
            rows = [{"indicator": key, **value} for key, value in payload.items() if isinstance(value, dict)]
            return rows, {k: v for k, v in payload.items() if not isinstance(v, dict)}
        return [payload], {}
