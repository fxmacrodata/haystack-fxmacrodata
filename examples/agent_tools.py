# SPDX-FileCopyrightText: 2026-present FXMacroData <info@fxmacrodata.com>
#
# SPDX-License-Identifier: Apache-2.0

# An Agent that answers macro questions with FXMacroData tools.
# Needs OPENAI_API_KEY for the chat model. FXMACRODATA_API_KEY is optional for USD questions.

from haystack.components.agents import Agent
from haystack.components.generators.chat import OpenAIChatGenerator
from haystack.dataclasses import ChatMessage

from haystack_integrations.tools.fxmacrodata import FXMacroDataToolset

tools = FXMacroDataToolset(operations=["data_catalogue", "indicator_history", "release_calendar"])
agent = Agent(
    chat_generator=OpenAIChatGenerator(model="gpt-5-mini"),
    tools=tools,
    system_prompt="Answer with figures from the tools and cite the source_url of each figure.",
)

result = agent.run(messages=[ChatMessage.from_user("What was the last US CPI print and when is the next release?")])
print(result["last_message"].text)
