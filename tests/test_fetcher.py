# SPDX-FileCopyrightText: 2026-present FXMacroData <info@fxmacrodata.com>
#
# SPDX-License-Identifier: Apache-2.0

import json
import os
from unittest.mock import MagicMock, patch

import pytest
from haystack import Pipeline
from haystack.utils import Secret

from haystack_integrations.components.fetchers.fxmacrodata import FXMacroDataError, FXMacroDataFetcher


def _response(payload, status_code=200):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = payload
    return response


def _page(rows, offset, has_more, next_offset=None):
    return {
        "currency": "USD",
        "indicator": "inflation",
        "data": rows,
        "pagination": {"limit": len(rows), "offset": offset, "has_more": has_more, "next_offset": next_offset},
    }


def _rows(start, count):
    return [{"date": f"2026-01-{day:02d}", "val": float(day)} for day in range(start + 1, start + count + 1)]


class TestInit:
    def test_init_default(self, monkeypatch):
        monkeypatch.delenv("FXMACRODATA_API_KEY", raising=False)
        fetcher = FXMacroDataFetcher()
        assert fetcher.operation == "indicator_history"
        assert fetcher.api_key == Secret.from_env_var("FXMACRODATA_API_KEY", strict=False)
        assert fetcher.max_records == 500
        assert fetcher._session is None

    def test_init_unknown_operation(self):
        with pytest.raises(ValueError, match="Unknown operation"):
            FXMacroDataFetcher(operation="not_an_endpoint")

    def test_init_invalid_max_records(self):
        with pytest.raises(ValueError, match="max_records"):
            FXMacroDataFetcher(max_records=0)

    def test_to_dict_from_dict(self, monkeypatch):
        monkeypatch.setenv("MY_FXMD_KEY", "test-key")
        fetcher = FXMacroDataFetcher(
            operation="forex",
            api_key=Secret.from_env_var("MY_FXMD_KEY"),
            max_records=50,
            timeout=5.0,
            max_retries=1,
            base_url="https://example.test/v1/",
        )
        data = fetcher.to_dict()
        assert data == {
            "type": "haystack_integrations.components.fetchers.fxmacrodata.fetcher.FXMacroDataFetcher",
            "init_parameters": {
                "operation": "forex",
                "api_key": {"type": "env_var", "env_vars": ["MY_FXMD_KEY"], "strict": True},
                "max_records": 50,
                "timeout": 5.0,
                "max_retries": 1,
                "base_url": "https://example.test/v1",
            },
        }
        restored = FXMacroDataFetcher.from_dict(data)
        assert restored.operation == "forex"
        assert restored.max_records == 50
        assert restored.api_key.resolve_value() == "test-key"

    def test_token_secret_is_not_serialized(self):
        fetcher = FXMacroDataFetcher(api_key=Secret.from_token("test-key"))
        with pytest.raises(ValueError):
            fetcher.to_dict()

    def test_pipeline_round_trip_keeps_key_out(self, monkeypatch):
        monkeypatch.setenv("FXMACRODATA_API_KEY", "test-key")
        pipeline = Pipeline()
        pipeline.add_component("fetcher", FXMacroDataFetcher(operation="release_calendar"))
        dumped = pipeline.dumps()
        assert "test-key" not in dumped
        restored = Pipeline.loads(dumped)
        assert restored.get_component("fetcher").operation == "release_calendar"


class TestWarmUp:
    def test_key_sent_in_header(self, monkeypatch):
        monkeypatch.setenv("FXMACRODATA_API_KEY", "test-key")
        fetcher = FXMacroDataFetcher()
        fetcher.warm_up()
        assert fetcher._session.headers["X-API-Key"] == "test-key"

    def test_no_header_without_key(self, monkeypatch):
        monkeypatch.delenv("FXMACRODATA_API_KEY", raising=False)
        fetcher = FXMacroDataFetcher()
        fetcher.warm_up()
        assert "X-API-Key" not in fetcher._session.headers

    def test_warm_up_is_idempotent_and_close_resets(self):
        fetcher = FXMacroDataFetcher(api_key=Secret.from_token("test-key"))
        fetcher.warm_up()
        session = fetcher._session
        fetcher.warm_up()
        assert fetcher._session is session
        fetcher.close()
        assert fetcher._session is None


class TestRun:
    def test_pages_until_has_more_is_false(self):
        fetcher = FXMacroDataFetcher(api_key=Secret.from_token("test-key"))
        pages = [_response(_page(_rows(0, 100), 0, True, 100)), _response(_page(_rows(100, 30), 100, False))]
        with patch("requests.Session.get", side_effect=pages) as get:
            result = fetcher.run(arguments={"currency": "USD", "indicator": "inflation"})

        assert len(result["documents"]) == 130
        assert get.call_args_list[0].args == ("https://api.fxmacrodata.com/v1/announcements/USD/inflation",)
        assert get.call_args_list[0].kwargs["params"] == {"limit": 100, "offset": 0}
        assert get.call_args_list[1].kwargs["params"] == {"limit": 100, "offset": 100}
        assert result["meta"]["currency"] == "USD"
        assert result["meta"]["pagination"]["has_more"] is False

    def test_limit_is_total_rows_and_page_size_is_capped(self):
        fetcher = FXMacroDataFetcher(api_key=Secret.from_token("test-key"))
        pages = [_response(_page(_rows(0, 100), 10, True)), _response(_page(_rows(100, 50), 110, True))]
        with patch("requests.Session.get", side_effect=pages) as get:
            result = fetcher.run(arguments={"currency": "USD", "indicator": "inflation", "limit": 150, "offset": 10})

        assert len(result["documents"]) == 150
        # no next_offset in the response, so the offset advances by the rows received
        assert [call.kwargs["params"] for call in get.call_args_list] == [
            {"limit": 100, "offset": 10},
            {"limit": 50, "offset": 110},
        ]

    def test_press_releases_page_size(self):
        fetcher = FXMacroDataFetcher(operation="press_releases", max_records=60)
        pages = [_response(_page(_rows(0, 50), 0, True, 50)), _response(_page(_rows(50, 10), 50, True, 60))]
        with patch("requests.Session.get", side_effect=pages) as get:
            result = fetcher.run(arguments={"currency": "USD"})
        assert len(result["documents"]) == 60
        assert get.call_args_list[0].kwargs["params"] == {"limit": 50, "offset": 0}
        assert get.call_args_list[1].kwargs["params"] == {"limit": 10, "offset": 50}

    def test_stops_on_empty_page(self):
        fetcher = FXMacroDataFetcher(api_key=Secret.from_token("test-key"))
        with patch("requests.Session.get", return_value=_response(_page([], 0, True))) as get:
            result = fetcher.run(arguments={"currency": "USD", "indicator": "inflation"})
        assert result["documents"] == []
        assert get.call_count == 1

    def test_null_values_are_kept(self):
        fetcher = FXMacroDataFetcher(api_key=Secret.from_token("test-key"))
        rows = [{"date": "2026-01-31", "val": None, "source_url": "https://www.bls.gov/"}]
        with patch("requests.Session.get", return_value=_response(_page(rows, 0, False))):
            result = fetcher.run(arguments={"currency": "USD", "indicator": "inflation"})
        document = result["documents"][0]
        assert json.loads(document.content) == rows[0]
        assert document.meta == {
            "date": "2026-01-31",
            "val": None,
            "source_url": "https://www.bls.gov/",
            "operation": "indicator_history",
        }

    def test_unpaginated_endpoint_sends_only_given_params(self):
        fetcher = FXMacroDataFetcher(operation="release_calendar", api_key=Secret.from_token("test-key"))
        payload = {"currency": "USD", "timezone": "America/New_York", "data": [{"release": "inflation"}]}
        with patch("requests.Session.get", return_value=_response(payload)) as get:
            result = fetcher.run(arguments={"currency": "USD", "indicator": "inflation", "end_date": None})
        assert get.call_args.args == ("https://api.fxmacrodata.com/v1/calendar/USD",)
        assert get.call_args.kwargs["params"] == {"indicator": "inflation"}
        assert result["meta"] == {"currency": "USD", "timezone": "America/New_York"}
        assert len(result["documents"]) == 1

    def test_boolean_params_are_lowercase(self):
        fetcher = FXMacroDataFetcher(operation="data_catalogue", api_key=Secret.from_token("test-key"))
        with patch("requests.Session.get", return_value=_response({})) as get:
            fetcher.run(arguments={"currency": "USD", "include_coverage": True})
        assert get.call_args.kwargs["params"] == {"include_coverage": "true"}

    def test_data_catalogue_rows(self):
        fetcher = FXMacroDataFetcher(operation="data_catalogue", api_key=Secret.from_token("test-key"))
        payload = {"inflation": {"name": "Inflation (CPI)", "unit": "%YoY"}, "gdp": {"name": "GDP", "unit": "%QoQ"}}
        with patch("requests.Session.get", return_value=_response(payload)):
            result = fetcher.run(arguments={"currency": "USD"})
        assert [doc.meta["indicator"] for doc in result["documents"]] == ["inflation", "gdp"]
        assert json.loads(result["documents"][0].content) == {
            "indicator": "inflation",
            "name": "Inflation (CPI)",
            "unit": "%YoY",
        }

    def test_missing_path_argument(self):
        fetcher = FXMacroDataFetcher(api_key=Secret.from_token("test-key"))
        with pytest.raises(ValueError, match="indicator"):
            fetcher.run(arguments={"currency": "USD"})

    def test_error_response(self):
        fetcher = FXMacroDataFetcher(operation="forex", api_key=Secret.from_token("test-key"))
        body = {"detail": "This endpoint requires an API key.", "code": "api_key_required"}
        with patch("requests.Session.get", return_value=_response(body, status_code=403)):
            with pytest.raises(FXMacroDataError) as error:
                fetcher.run(arguments={"base": "EUR", "quote": "USD"})
        assert error.value.status_code == 403
        assert error.value.code == "api_key_required"
        assert str(error.value) == (
            "FXMacroData request failed with HTTP 403 (api_key_required): This endpoint requires an API key."
        )

    def test_error_response_without_json(self):
        fetcher = FXMacroDataFetcher(api_key=Secret.from_token("test-key"))
        response = _response(None, status_code=502)
        response.json.side_effect = ValueError("not json")
        with patch("requests.Session.get", return_value=response):
            with pytest.raises(FXMacroDataError, match="HTTP 502$"):
                fetcher.run(arguments={"currency": "USD", "indicator": "inflation"})


@pytest.mark.integration
class TestIntegration:
    def test_usd_history_without_key(self):
        # an unset variable means no key is sent; USD history is still readable
        keyless = Secret.from_env_var("FXMACRODATA_TEST_UNSET_KEY", strict=False)
        fetcher = FXMacroDataFetcher(api_key=keyless, max_records=5)
        result = fetcher.run(arguments={"currency": "USD", "indicator": "policy_rate"})
        assert 0 < len(result["documents"]) <= 5
        assert "date" in result["documents"][0].meta

    @pytest.mark.skipif(not os.environ.get("FXMACRODATA_API_KEY"), reason="FXMACRODATA_API_KEY is not set")
    def test_forex_with_key(self):
        fetcher = FXMacroDataFetcher(operation="forex", max_records=5)
        result = fetcher.run(arguments={"base": "EUR", "quote": "USD"})
        assert 0 < len(result["documents"]) <= 5
