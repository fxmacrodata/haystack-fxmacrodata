"""Execute a real public-USD Haystack Pipeline without an LLM."""

from datetime import date, timedelta

from haystack import Pipeline

from fxmacrodata_haystack import FXMacroDataFetcher


def main() -> None:
    pipeline = Pipeline()
    today = date.today()
    arguments = {
        "catalogue": ("data_catalogue", {"currency": "USD"}),
        "history": ("indicator_history", {
            "currency": "USD", "indicator": "inflation",
            "start_date": (today - timedelta(days=90)).isoformat(), "end_date": today.isoformat(),
        }),
        "calendar": ("release_calendar", {
            "currency": "USD", "start_date": today.isoformat(),
            "end_date": (today + timedelta(days=30)).isoformat(),
        }),
    }
    for name, (operation, _) in arguments.items():
        pipeline.add_component(name, FXMacroDataFetcher(operation=operation, public_only=True))
    result = pipeline.run({name: {"arguments": params} for name, (_, params) in arguments.items()})
    for name, output in result.items():
        if output["error"]:
            raise RuntimeError(output["error"])
        print(f"{name}: {len(output['documents'])} Documents")
        print(output["source_url"])
        print(output["provider_url"])
        if not output["documents"]:
            print("No records available in this window.")


if __name__ == "__main__":
    main()
