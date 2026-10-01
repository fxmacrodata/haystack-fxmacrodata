# SPDX-FileCopyrightText: 2026-present FXMacroData <info@fxmacrodata.com>
#
# SPDX-License-Identifier: Apache-2.0

# Fetch recent US CPI prints and the upcoming release calendar into a document store.
# Runs without an API key: USD data is readable on the free tier.

from datetime import date, timedelta

from haystack import Pipeline
from haystack.components.joiners import DocumentJoiner
from haystack.components.writers import DocumentWriter
from haystack.document_stores.in_memory import InMemoryDocumentStore

from haystack_integrations.components.fetchers.fxmacrodata import FXMacroDataFetcher

store = InMemoryDocumentStore()
pipeline = Pipeline()
pipeline.add_component("history", FXMacroDataFetcher(operation="indicator_history", max_records=12))
pipeline.add_component("calendar", FXMacroDataFetcher(operation="release_calendar"))
pipeline.add_component("joiner", DocumentJoiner())
pipeline.add_component("writer", DocumentWriter(document_store=store))
pipeline.connect("history.documents", "joiner.documents")
pipeline.connect("calendar.documents", "joiner.documents")
pipeline.connect("joiner.documents", "writer.documents")

today = date.today()
pipeline.run(
    {
        "history": {"arguments": {"currency": "USD", "indicator": "inflation"}},
        "calendar": {
            "arguments": {
                "currency": "USD",
                "indicator": "inflation",
                "start_date": today.isoformat(),
                "end_date": (today + timedelta(days=60)).isoformat(),
            }
        },
    }
)

cpi_prints = store.filter_documents(filters={"field": "meta.operation", "operator": "==", "value": "indicator_history"})
for document in cpi_prints:
    # val is None when the source published no value for that period
    print(document.meta["date"], document.meta["val"])
