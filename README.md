# FXMacroData for Haystack

Build macro-research pipelines with official economic observations, release calendars and searchable Haystack Documents. The public USD catalogue, history and release-calendar workflow needs no API key, account or credit card.

[Explore FXMacroData](https://fxmacrodata.com/?utm_source=github&utm_medium=referral&utm_campaign=open_source_integrations&utm_content=haystack_readme) · [API documentation](https://fxmacrodata.com/documentation/reference?utm_source=github&utm_medium=referral&utm_campaign=open_source_integrations&utm_content=haystack_docs)

The public example requests the most recent 90 days of USD history. Broader history and protected datasets follow the documented access limits.

## Install from source

With the companion client and this project in sibling directories:

```bash
python -m pip install ./fxmacrodata-public-client ./haystack-fxmacrodata
```

This command uses source packages, without assuming a package-registry publication. Requires Python 3.10+ and Haystack 3.1.1+.

## Pipeline

```python
from haystack import Pipeline
from fxmacrodata_haystack import FXMacroDataFetcher

pipeline = Pipeline()
pipeline.add_component("macro", FXMacroDataFetcher(operation="indicator_history"))
result = pipeline.run({"macro": {"arguments": {"currency": "USD", "indicator": "inflation"}}})
documents = result["macro"]["documents"]
```

Connect `documents` to document writers, retrievers, joiners or prompt builders. Each Document contains a complete record and source metadata. `data` retains the unmodified endpoint response; `records` provides a tabular view. The `error` output distinguishes an unsuccessful request from a valid empty result.

For Haystack Agents, use `create_tools()` to obtain 72 separate `FXMacroDataTool` objects with complete documented input schemas. For a smaller agent context, pass `operations=["data_catalogue", "indicator_history", "release_calendar"]`. See [CAPABILITIES.md](CAPABILITIES.md).

Run `python examples/usd_macro_brief.py` to build and execute a real three-component Pipeline without a language model. Run `python examples/tool_invocation.py` to call a native Tool directly.

## Credentials and persistence

The default is Haystack `Secret.from_env_var("FXMACRODATA_API_KEY", strict=False)`. An absent variable keeps public USD access available. Set `public_only=True` to ignore ambient credentials. Use `Secret.from_env_var` with your application's own secret-variable name if desired. Environment references serialize into saved pipelines; credential values do not. Haystack deliberately refuses to serialize `Secret.from_token` values.

When loading a trusted saved pipeline, allow this specific extension module: `Pipeline.loads(saved_yaml, allowed_modules=["fxmacrodata_haystack.integration"])`. This preserves Haystack's normal deserialization protection.

Preserve units, timestamp flags, provenance, empty results and the distinction between FXMacroData-generated forecasts and market consensus. The plugin preserves MCP visual resources but does not render MCP Apps.

README links contain static referral parameters. This integration adds no analytics SDK, identifier or click beacon.

## Test

```bash
python -m pytest tests -n 8 --dist load
```

Code is Apache-2.0 licensed. API access, data use and brand rights remain governed by their applicable terms.
