"""Invoke a native Haystack Tool directly without a language model."""

from fxmacrodata_haystack import create_tools


def main() -> None:
    tool = create_tools(public_only=True, operations=["data_catalogue"])[0]
    result = tool.invoke(currency="USD")
    if result["error"]:
        raise RuntimeError(result["error"])
    print(f"The native tool returned {len(result['documents'])} Documents.")
    print(result["provider_url"])


if __name__ == "__main__":
    main()
