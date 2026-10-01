# fxmacrodata-haystack

[![PyPI - Version](https://img.shields.io/pypi/v/fxmacrodata-haystack.svg)](https://pypi.org/project/fxmacrodata-haystack)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/fxmacrodata-haystack.svg)](https://pypi.org/project/fxmacrodata-haystack)

[Haystack](https://haystack.deepset.ai/) components and agent tools for [FXMacroData](https://fxmacrodata.com/?utm_source=github&utm_medium=referral&utm_campaign=haystack-fxmacrodata&utm_content=readme), an API for macroeconomic releases, central-bank data, economic calendars and FX rates across 22 currencies, sourced from official publishers.

- `FXMacroDataFetcher` turns an endpoint response into Haystack `Document`s, one per row.
- `FXMacroDataTool` and `FXMacroDataToolset` expose the same endpoints to Haystack Agents.

## Installation

```bash
pip install fxmacrodata-haystack
```

## Access

USD data works without an API key: the most recent 90 days of history, with new releases delayed by 15 minutes and roughly 100 requests a day. Other currencies, FX rates, commodities and predictions need a key, which you can get from the [subscription page](https://fxmacrodata.com/subscribe?utm_source=github&utm_medium=referral&utm_campaign=haystack-fxmacrodata&utm_content=subscribe).

The components read the key from the `FXMACRODATA_API_KEY` environment variable and send it in the `X-API-Key` header. Pass `api_key=Secret.from_env_var("OTHER_NAME")` to use a different variable. The key is never written into serialized pipelines.

## Usage

### Fetcher

```python
from haystack_integrations.components.fetchers.fxmacrodata import FXMacroDataFetcher

fetcher = FXMacroDataFetcher(operation="indicator_history")
result = fetcher.run(arguments={"currency": "USD", "indicator": "inflation", "start_date": "2026-01-01"})

for document in result["documents"]:
    print(document.meta["date"], document.meta["val"])
print(result["meta"]["pagination"])
```

Each `Document` holds one row of the response as JSON, unchanged. Scalar fields of the row (`date`, `val`, `announcement_datetime`, `source_url` and so on) are copied into `Document.meta`, together with `operation`, so they work with document store filters. A `val` of `None` means the publisher released no value for that period; it is passed through rather than replaced.

`meta` carries the rest of the response, such as `pagination`, `source`, and `freemium_delay` when the request was made without a key.

Paginated endpoints are read with `limit`/`offset` in pages of up to 100 rows until the API reports `has_more: false`. In `arguments`, `limit` is the total number of rows you want; without it the fetcher stops at `max_records` (500 by default).

| `operation` | Endpoint | Paginated |
| --- | --- | --- |
| `data_catalogue` | `GET /v1/data_catalogue/{currency}` | no |
| `indicator_history` | `GET /v1/announcements/{currency}/{indicator}` | yes |
| `latest_announcements` | `GET /v1/announcements/{currency}/latest` | no |
| `release_calendar` | `GET /v1/calendar/{currency}` | no |
| `forex` | `GET /v1/forex/{base}/{quote}` | yes |
| `event_predictions` | `GET /v1/predictions/{currency}/{indicator}` | yes |
| `commodities` | `GET /v1/commodities/{indicator}` | yes |
| `cot` | `GET /v1/cot/{currency}` | yes |
| `press_releases` | `GET /v1/press-releases/{currency}` | yes |

Path parameters go in `arguments` next to the query parameters. Any other query parameter documented in the [API reference](https://fxmacrodata.com/documentation/reference?utm_source=github&utm_medium=referral&utm_campaign=haystack-fxmacrodata&utm_content=docs) is passed through as is. An error response raises `FXMacroDataError` with the HTTP status and the API's error code, for example `api_key_required`.

### Agent tools

```python
from haystack.components.agents import Agent
from haystack.components.generators.chat import OpenAIChatGenerator
from haystack.dataclasses import ChatMessage

from haystack_integrations.tools.fxmacrodata import FXMacroDataToolset

tools = FXMacroDataToolset(operations=["data_catalogue", "indicator_history", "release_calendar"])
agent = Agent(chat_generator=OpenAIChatGenerator(model="gpt-5-mini"), tools=tools)

result = agent.run(messages=[ChatMessage.from_user("What was the last US CPI print and when is the next release?")])
print(result["last_message"].text)
```

Tools are named `fxmacrodata_<operation>`. The model receives the rows and the response metadata as JSON. Tools return at most 100 rows unless the model asks for more with `limit`; change this with `max_records`.

More examples are in [`examples/`](examples/).

## Development

```bash
pip install hatch

hatch run fmt-check         # lint
hatch run test:types        # mypy
hatch run test:unit         # unit tests, no network
hatch run test:integration  # calls the live API; USD tests run without a key
```

## License

`fxmacrodata-haystack` is distributed under the terms of the [Apache-2.0](LICENSE) license. Use of the FXMacroData API is governed by its own terms.
