# SPDX-FileCopyrightText: 2026-present FXMacroData <info@fxmacrodata.com>
#
# SPDX-License-Identifier: Apache-2.0

import json
from unittest.mock import MagicMock, patch

import pytest
from haystack import component
from haystack.components.agents import Agent
from haystack.dataclasses import ChatMessage, ToolCall
from haystack.utils import Secret

from haystack_integrations.components.fetchers.fxmacrodata import OPERATIONS
from haystack_integrations.tools.fxmacrodata import FXMacroDataTool, FXMacroDataToolset

CALENDAR = {
    "currency": "USD",
    "data": [{"release": "inflation", "announcement_datetime_utc": "2026-10-15T12:30:00+00:00", "val": None}],
}


def _response(payload):
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = payload
    return response


class TestFXMacroDataTool:
    @pytest.mark.parametrize("operation", list(OPERATIONS))
    def test_init(self, operation):
        tool = FXMacroDataTool(operation)
        assert tool.name == f"fxmacrodata_{operation}"
        assert tool.parameters == OPERATIONS[operation].parameters
        assert set(tool.parameters["required"]) == set(OPERATIONS[operation].path_params)

    def test_init_unknown_operation(self):
        with pytest.raises(ValueError, match="Unknown operation"):
            FXMacroDataTool("not_an_endpoint")

    def test_invoke(self):
        tool = FXMacroDataTool("release_calendar", api_key=Secret.from_token("test-key"))
        with patch("requests.Session.get", return_value=_response(CALENDAR)) as get:
            result = tool.invoke(currency="USD")
        assert get.call_args.args == ("https://api.fxmacrodata.com/v1/calendar/USD",)
        assert json.loads(result["documents"][0].content) == CALENDAR["data"][0]

    def test_to_dict_from_dict(self, monkeypatch):
        monkeypatch.setenv("MY_FXMD_KEY", "test-key")
        tool = FXMacroDataTool(
            "cot", api_key=Secret.from_env_var("MY_FXMD_KEY"), max_records=10, timeout=5.0, max_retries=1
        )
        data = tool.to_dict()
        assert data == {
            "type": "haystack_integrations.tools.fxmacrodata.tool.FXMacroDataTool",
            "data": {
                "operation": "cot",
                "api_key": {"type": "env_var", "env_vars": ["MY_FXMD_KEY"], "strict": True},
                "max_records": 10,
                "timeout": 5.0,
                "max_retries": 1,
            },
        }
        restored = FXMacroDataTool.from_dict(data)
        assert restored.name == "fxmacrodata_cot"
        assert restored._fetcher.max_records == 10
        assert restored.api_key.resolve_value() == "test-key"


class TestFXMacroDataToolset:
    def test_default_contains_every_operation(self):
        toolset = FXMacroDataToolset()
        assert [tool.name for tool in toolset] == [f"fxmacrodata_{name}" for name in OPERATIONS]

    def test_to_dict_from_dict(self, monkeypatch):
        monkeypatch.setenv("FXMACRODATA_API_KEY", "test-key")
        toolset = FXMacroDataToolset(
            operations=["data_catalogue", "release_calendar"],
            api_key=Secret.from_env_var("FXMACRODATA_API_KEY"),
            max_records=20,
        )
        data = toolset.to_dict()
        assert "test-key" not in json.dumps(data)
        restored = FXMacroDataToolset.from_dict(data)
        assert [tool.name for tool in restored] == ["fxmacrodata_data_catalogue", "fxmacrodata_release_calendar"]
        assert restored.max_records == 20

    def test_agent_receives_rows_and_meta(self):
        @component
        class CallCalendar:
            @component.output_types(replies=list[ChatMessage])
            def run(self, messages: list[ChatMessage], tools=None) -> dict:
                call = ToolCall(tool_name="fxmacrodata_release_calendar", arguments={"currency": "USD"}, id="1")
                return {"replies": [ChatMessage.from_assistant(tool_calls=[call])]}

        agent = Agent(
            chat_generator=CallCalendar(),
            tools=FXMacroDataToolset(operations=["release_calendar"], api_key=Secret.from_token("test-key")),
            exit_conditions=["fxmacrodata_release_calendar"],
        )
        with patch("requests.Session.get", return_value=_response(CALENDAR)):
            result = agent.run(messages=[ChatMessage.from_user("When is the next US CPI release?")])

        tool_result = json.loads(result["messages"][-1].tool_call_result.result)
        assert tool_result == {"meta": {"currency": "USD"}, "rows": CALENDAR["data"]}
