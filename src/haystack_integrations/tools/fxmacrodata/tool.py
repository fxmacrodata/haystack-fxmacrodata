# SPDX-FileCopyrightText: 2026-present FXMacroData <info@fxmacrodata.com>
#
# SPDX-License-Identifier: Apache-2.0

import json
from copy import deepcopy
from typing import Any

from haystack.core.serialization import generate_qualified_class_name
from haystack.tools import Tool, Toolset
from haystack.utils import Secret, deserialize_secrets_inplace

from haystack_integrations.components.fetchers.fxmacrodata import OPERATIONS, FXMacroDataFetcher


def _format_result(result: dict[str, Any]) -> str:
    """
    Format a fetcher result as the tool-result string: response metadata plus the rows.

    :param result: Output of `FXMacroDataFetcher.run`.
    :returns: JSON string with `meta` and `rows` keys.
    """
    rows = [json.loads(document.content) for document in result["documents"] if document.content]
    return json.dumps({"meta": result["meta"], "rows": rows}, ensure_ascii=False)


class FXMacroDataTool(Tool):
    """
    A tool that calls one FXMacroData endpoint.

    The tool name is `fxmacrodata_<operation>` and its parameters are the endpoint's path and query parameters.
    The LLM receives the rows as JSON together with the response metadata, which includes the free-tier
    delay notice when no API key is set.

    ### Usage example

    ```python
    from haystack_integrations.tools.fxmacrodata import FXMacroDataTool

    tool = FXMacroDataTool("release_calendar")
    print(tool.invoke(currency="USD")["documents"][:3])
    ```
    """

    def __init__(
        self,
        operation: str,
        *,
        api_key: Secret | None = None,
        max_records: int = 100,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        """
        Initialize the FXMacroDataTool.

        :param operation:
            Endpoint to expose, one of the keys of `OPERATIONS`.
        :param api_key:
            FXMacroData API key. If unset, `FXMacroDataFetcher` reads the `FXMACRODATA_API_KEY` environment variable.
        :param max_records:
            Upper bound on the rows returned by a paginated endpoint when the LLM passes no `limit`.
            Kept low by default so tool results fit in the context window.
        :param timeout:
            Timeout in seconds for each HTTP request.
        :param max_retries:
            Retries for connection errors and 429/5xx responses.
        :raises ValueError: If `operation` is unknown.
        """
        if operation not in OPERATIONS:
            msg = f"Unknown operation '{operation}'. Choose one of: {', '.join(OPERATIONS)}."
            raise ValueError(msg)
        self.operation = operation
        self.api_key = api_key
        self.max_records = max_records
        self.timeout = timeout
        self.max_retries = max_retries

        fetcher_params: dict[str, Any] = {"max_records": max_records, "timeout": timeout, "max_retries": max_retries}
        if api_key is not None:
            fetcher_params["api_key"] = api_key
        self._fetcher = FXMacroDataFetcher(operation, **fetcher_params)

        spec = OPERATIONS[operation]
        super().__init__(
            name=f"fxmacrodata_{operation}",
            description=spec.description,
            parameters=deepcopy(spec.parameters),
            function=self._invoke,
            outputs_to_string={"handler": _format_result},
        )

    def _invoke(self, **arguments: Any) -> dict[str, Any]:
        return self._fetcher.run(arguments=arguments)

    def warm_up(self) -> None:
        """Create the HTTP session used by the tool."""
        self._fetcher.warm_up()

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize the tool to a dictionary.

        :returns: Dictionary with serialized data.
        """
        return {
            "type": generate_qualified_class_name(type(self)),
            "data": {
                "operation": self.operation,
                "api_key": self.api_key.to_dict() if self.api_key else None,
                "max_records": self.max_records,
                "timeout": self.timeout,
                "max_retries": self.max_retries,
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FXMacroDataTool":
        """
        Deserialize the tool from a dictionary.

        :param data: Dictionary to deserialize from.
        :returns: Deserialized tool.
        """
        inner_data = deepcopy(data["data"])
        deserialize_secrets_inplace(inner_data, keys=["api_key"])
        return cls(**inner_data)


class FXMacroDataToolset(Toolset):
    """
    A Toolset with one `FXMacroDataTool` per endpoint.

    ### Usage example

    ```python
    from haystack.components.agents import Agent
    from haystack.components.generators.chat import OpenAIChatGenerator
    from haystack.dataclasses import ChatMessage
    from haystack_integrations.tools.fxmacrodata import FXMacroDataToolset

    tools = FXMacroDataToolset(operations=["data_catalogue", "indicator_history", "release_calendar"])
    agent = Agent(chat_generator=OpenAIChatGenerator(model="gpt-5-mini"), tools=tools)

    result = agent.run(messages=[ChatMessage.from_user("When is the next US CPI release and what was the last print?")])
    print(result["last_message"].text)
    ```
    """

    def __init__(
        self,
        operations: list[str] | None = None,
        *,
        api_key: Secret | None = None,
        max_records: int = 100,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        """
        Create an FXMacroDataToolset.

        :param operations:
            Endpoints to include. Defaults to all keys of `OPERATIONS`.
        :param api_key:
            FXMacroData API key shared by all tools. If unset, the `FXMACRODATA_API_KEY` environment variable is used.
        :param max_records:
            Upper bound on the rows returned by a paginated endpoint when the LLM passes no `limit`.
        :param timeout:
            Timeout in seconds for each HTTP request.
        :param max_retries:
            Retries for connection errors and 429/5xx responses.
        :raises ValueError: If an operation is unknown.
        """
        self.operations = list(OPERATIONS) if operations is None else list(operations)
        self.api_key = api_key
        self.max_records = max_records
        self.timeout = timeout
        self.max_retries = max_retries
        super().__init__(
            tools=[
                FXMacroDataTool(
                    operation, api_key=api_key, max_records=max_records, timeout=timeout, max_retries=max_retries
                )
                for operation in self.operations
            ]
        )

    def to_dict(self) -> dict[str, Any]:
        """
        Serialize the toolset to a dictionary.

        :returns: Dictionary with serialized data.
        """
        return {
            "type": generate_qualified_class_name(type(self)),
            "data": {
                "operations": self.operations,
                "api_key": self.api_key.to_dict() if self.api_key else None,
                "max_records": self.max_records,
                "timeout": self.timeout,
                "max_retries": self.max_retries,
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FXMacroDataToolset":
        """
        Deserialize the toolset from a dictionary.

        :param data: Dictionary to deserialize from.
        :returns: Deserialized toolset.
        """
        inner_data = deepcopy(data["data"])
        deserialize_secrets_inplace(inner_data, keys=["api_key"])
        return cls(**inner_data)
