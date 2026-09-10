"""Haystack documents and agent tools from documented FXMacroData data."""

import json
from copy import deepcopy
from typing import Any

from fxmacrodata_public import FXMacroDataClient, FXMacroDataError, list_operations
from haystack import Document, component, default_from_dict, default_to_dict
from haystack.tools import Tool
from haystack.utils import Secret

SITE_URL = (
    "https://fxmacrodata.com/?utm_source=haystack&utm_medium=integration"
    "&utm_campaign=open_source_integrations&utm_content=app"
)
_OPERATIONS = {operation.name: operation for operation in list_operations()}


def _secret(api_key: Secret | None) -> Secret:
    return api_key if api_key is not None else Secret.from_env_var("FXMACRODATA_API_KEY", strict=False)


def _query(
    operation: str, arguments: dict[str, Any], api_key: Secret, timeout: float, public_only: bool = False
) -> dict[str, Any]:
    try:
        key = "" if public_only else api_key.resolve_value() or ""
        with FXMacroDataClient(api_key=key, timeout=timeout) as client:
            result = client.execute(operation, arguments)
        records = result.records()
        documents = [
            Document(
                content=json.dumps(record, ensure_ascii=False),
                meta={"source_url": result.as_dict()["source_url"], "operation": operation, "provider_url": SITE_URL},
            )
            for record in records
        ]
        return {**result.as_dict(), "documents": documents, "provider_url": SITE_URL, "error": ""}
    except Exception as error:  # noqa: BLE001 - sanitize the external SDK boundary
        return {
            "operation": operation,
            "data": None,
            "records": [],
            "documents": [],
            "source_url": "https://fxmacrodata.com/documentation/reference",
            "provider_url": SITE_URL,
            "error": str(error)
            if isinstance(error, FXMacroDataError)
            else "FXMacroData request failed. Check parameters and access.",
        }


def _agent_message(result: dict[str, Any]) -> str:
    """Keep explicit failure and provenance fields in model-visible output."""
    return json.dumps({key: value for key, value in result.items() if key != "documents"}, ensure_ascii=False)


@component
class FXMacroDataFetcher:
    """Load an API/MCP operation into lossless data and searchable Documents.

    Inputs use a parameter mapping, allowing every documented parameter,
    including MCP objects and the Last-Event-ID stream resume header.
    Output Documents contain the complete presentation records. The original
    response remains available on the data output.
    """

    def __init__(
        self,
        operation: str = "indicator_history",
        api_key: Secret | None = None,
        timeout: float = 30,
        public_only: bool = False,
    ):
        if operation not in _OPERATIONS:
            raise ValueError("Unknown FXMacroData operation.")
        self.operation = operation
        self.api_key = _secret(api_key)
        self.timeout = timeout
        self.public_only = public_only

    @component.output_types(
        operation=str,
        data=Any,
        records=list[dict[str, Any]],
        documents=list[Document],
        source_url=str,
        provider_url=str,
        error=str,
    )
    def run(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return _query(self.operation, arguments, self.api_key, self.timeout, self.public_only)

    def to_dict(self) -> dict[str, Any]:
        """Serialize environment-based secrets without their values."""
        return default_to_dict(
            self,
            operation=self.operation,
            api_key=self.api_key.to_dict(),
            timeout=self.timeout,
            public_only=self.public_only,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FXMacroDataFetcher":
        data = deepcopy(data)
        data["init_parameters"]["api_key"] = Secret.from_dict(data["init_parameters"]["api_key"])
        return default_from_dict(cls, data)


class FXMacroDataTool(Tool):
    """A schema-aware, serializable native Haystack Tool for one operation."""

    def __init__(self, operation: str, api_key: Secret | None = None, timeout: float = 30, public_only: bool = False):
        if operation not in _OPERATIONS:
            raise ValueError("Unknown FXMacroData operation.")
        self.operation = operation
        self.api_key = _secret(api_key)
        self.timeout = timeout
        self.public_only = public_only
        spec = _OPERATIONS[operation]
        super().__init__(
            name="fxmd_" + operation,
            description=spec.description,
            parameters=deepcopy(spec.input_schema),
            function=self._invoke,
            outputs_to_string={"handler": _agent_message},
        )

    def _invoke(self, **arguments: Any) -> dict[str, Any]:
        return _query(self.operation, arguments, self.api_key, self.timeout, self.public_only)

    def to_dict(self) -> dict[str, Any]:
        """Use the host's supported Secret serialization policy."""
        return {
            "type": "fxmacrodata_haystack.integration.FXMacroDataTool",
            "data": {
                "operation": self.operation,
                "api_key": self.api_key.to_dict(),
                "timeout": self.timeout,
                "public_only": self.public_only,
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FXMacroDataTool":
        options = deepcopy(data["data"])
        options["api_key"] = Secret.from_dict(options["api_key"])
        return cls(**options)


def create_tools(
    api_key: Secret | None = None, timeout: float = 30, operations: list[str] | None = None, public_only: bool = False
) -> list[FXMacroDataTool]:
    """Create the complete inventory, or a task-specific operation subset."""
    selected = list(_OPERATIONS) if operations is None else operations
    return [
        FXMacroDataTool(operation, api_key=api_key, timeout=timeout, public_only=public_only) for operation in selected
    ]
