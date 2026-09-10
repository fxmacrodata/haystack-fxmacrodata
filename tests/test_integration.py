"""Actual Haystack tools, Pipeline execution and secret serialization."""

import json
from unittest.mock import patch

import pytest
from fxmacrodata_public import Result, list_operations
from haystack import Document, Pipeline, component
from haystack.components.agents import Agent
from haystack.dataclasses import ChatMessage, ToolCall
from haystack.utils import Secret

from fxmacrodata_haystack import FXMacroDataFetcher, FXMacroDataTool, create_tools

PAYLOAD = {"data": [{"fixture": "synthetic", "announcement_datetime": "2026-01-01T12:00:00Z", "value": None}]}


@pytest.mark.parametrize("operation", list_operations(), ids=lambda item: item.name)
def test_native_tool_schema_documents_and_lossless_result(operation):
    tool = FXMacroDataTool(operation.name)
    assert tool.parameters == operation.input_schema
    arguments = {"fixture_argument": {"nested": [1, None]}}
    with patch(
        "fxmacrodata_haystack.integration.FXMacroDataClient.execute", return_value=Result(operation.name, PAYLOAD)
    ) as execute:
        output = tool.invoke(**arguments)
    execute.assert_called_once_with(operation.name, arguments)
    assert output["data"] == PAYLOAD
    assert isinstance(output["documents"][0], Document)
    assert json.loads(output["documents"][0].content) == PAYLOAD["data"][0]
    assert "utm_source=haystack" in output["documents"][0].meta["provider_url"]
    restored = FXMacroDataTool.from_dict(tool.to_dict())
    assert restored.parameters == tool.parameters


def test_pipeline_runs_and_round_trips_without_credentials(monkeypatch):
    monkeypatch.setenv("FXMACRODATA_API_KEY", "DO_NOT_DISCLOSE_SENTINEL")
    pipeline = Pipeline()
    pipeline.add_component("macro", FXMacroDataFetcher(operation="indicator_history"))
    serialized = pipeline.dumps()
    assert "DO_NOT_DISCLOSE_SENTINEL" not in serialized
    assert "FXMACRODATA_API_KEY" in serialized
    restored = Pipeline.loads(serialized, allowed_modules=["fxmacrodata_haystack.integration"])
    with patch(
        "fxmacrodata_haystack.integration.FXMacroDataClient.execute", return_value=Result("indicator_history", PAYLOAD)
    ):
        output = restored.run({"macro": {"arguments": {"currency": "USD", "indicator": "inflation"}}})
    assert output["macro"]["data"] == PAYLOAD
    assert len(output["macro"]["documents"]) == 1


def test_agent_consumes_native_tool():
    @component
    class FixedToolSelection:
        @component.output_types(replies=list[ChatMessage])
        def run(self, messages: list[ChatMessage], tools: list | None = None) -> dict:
            return {
                "replies": [
                    ChatMessage.from_assistant(
                        tool_calls=[
                            ToolCall(tool_name="fxmd_data_catalogue", arguments={"currency": "USD"}, id="fixture-call")
                        ]
                    )
                ]
            }

    agent = Agent(
        chat_generator=FixedToolSelection(),
        tools=create_tools(operations=["data_catalogue"]),
        exit_conditions=["fxmd_data_catalogue"],
    )
    with patch(
        "fxmacrodata_haystack.integration.FXMacroDataClient.execute", return_value=Result("data_catalogue", PAYLOAD)
    ):
        result = agent.run(messages=[ChatMessage.from_user("Inspect the synthetic catalogue fixture.")])
    assert "synthetic" in str(result["messages"])
    assert "utm_source=haystack" in str(result["messages"])


def test_errors_distinct_from_empty_and_no_secret_leak():
    fetcher = FXMacroDataFetcher(operation="release_calendar")
    with patch(
        "fxmacrodata_haystack.integration.FXMacroDataClient.execute",
        side_effect=RuntimeError("https://example.org/?api_key=DO_NOT_DISCLOSE_SENTINEL"),
    ):
        output = fetcher.run(arguments={"currency": "USD"})
    assert output["error"] and output["documents"] == []
    assert "SENTINEL" not in str(output)
    with patch(
        "fxmacrodata_haystack.integration.FXMacroDataClient.execute", return_value=Result("release_calendar", [])
    ):
        output = fetcher.run(arguments={"currency": "USD"})
    assert output["error"] == "" and output["documents"] == []


def test_token_secrets_cannot_be_serialized():
    component = FXMacroDataFetcher(api_key=Secret.from_token("DO_NOT_DISCLOSE_SENTINEL"))
    with pytest.raises(ValueError):
        component.to_dict()


def test_inventory_exact():
    assert {tool.name for tool in create_tools()} == {"fxmd_" + operation.name for operation in list_operations()}


def test_public_only_ignores_environment_credentials(monkeypatch):
    monkeypatch.setenv("FXMACRODATA_API_KEY", "DO_NOT_DISCLOSE_SENTINEL")
    fetcher = FXMacroDataFetcher(operation="data_catalogue", public_only=True)
    with patch("fxmacrodata_haystack.integration.FXMacroDataClient") as client:
        client.return_value.__enter__.return_value.execute.return_value = Result("data_catalogue", [])
        result = fetcher.run(arguments={"currency": "USD"})
    client.assert_called_once_with(api_key="", timeout=30)
    assert result["error"] == ""
