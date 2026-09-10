# Supported operations

Every operation is registered as `fxmd_<operation>` in the native tool surface. The original response is preserved alongside its record view.

| Operation | Contract | Native surface |
| --- | --- | --- |
| `health` | `GET /v1/health` | Haystack Tool, Fetcher Documents |
| `ping` | `GET /v1/ping` | Haystack Tool, Fetcher Documents |
| `forex` | `GET /v1/forex/{base}/{quote}` | Haystack Tool, Fetcher Documents |
| `intraday_reference_rates` | `GET /v1/fx/intraday-reference-rates/{base}/{quote}` | Haystack Tool, Fetcher Documents |
| `fx_sources` | `GET /v1/fx/sources` | Haystack Tool, Fetcher Documents |
| `fx_source_universe` | `GET /v1/fx/source-universe` | Haystack Tool, Fetcher Documents |
| `data_catalogue` | `GET /v1/data_catalogue/{currency}` | Haystack Tool, Fetcher Documents |
| `release_calendar` | `GET /v1/calendar/{currency}` | Haystack Tool, Fetcher Documents |
| `market_sessions` | `GET /v1/market_sessions` | Haystack Tool, Fetcher Documents |
| `rate_differentials` | `GET /v1/rate_differentials/{base}/{quote}` | Haystack Tool, Fetcher Documents |
| `curves` | `GET /v1/curves/{currency}` | Haystack Tool, Fetcher Documents |
| `financial_prices` | `GET /v1/financial_prices/{currency}` | Haystack Tool, Fetcher Documents |
| `press_releases` | `GET /v1/press-releases/{currency}` | Haystack Tool, Fetcher Documents |
| `risk_sentiment` | `GET /v1/risk_sentiment` | Haystack Tool, Fetcher Documents |
| `factors` | `GET /v1/factors/{currency}/{factor}` | Haystack Tool, Fetcher Documents |
| `event_predictions` | `GET /v1/predictions/{currency}/{indicator}` | Haystack Tool, Fetcher Documents |
| `latest_announcements` | `GET /v1/announcements/{currency}/latest` | Haystack Tool, Fetcher Documents |
| `indicator_history` | `GET /v1/announcements/{currency}/{indicator}` | Haystack Tool, Fetcher Documents |
| `cot` | `GET /v1/cot/{currency}` | Haystack Tool, Fetcher Documents |
| `latest_commodities` | `GET /v1/commodities/latest` | Haystack Tool, Fetcher Documents |
| `commodities` | `GET /v1/commodities/{indicator}` | Haystack Tool, Fetcher Documents |
| `announcement_changes` | `GET /v1/announcements/changes` | Haystack Tool, Fetcher Documents |
| `stream_events` | `GET /v1/stream/events` | Haystack Tool, Fetcher Documents |
| `mcp_ping` | `MCP /mcp` | Haystack Tool, Fetcher Documents |
| `mcp_mcp_capabilities` | `MCP /mcp` | Haystack Tool, Fetcher Documents |
| `mcp_mcp_auth_guide` | `MCP /mcp` | Haystack Tool, Fetcher Documents |
| `mcp_subscribe_for_mcp_access` | `MCP /mcp` | Haystack Tool, Fetcher Documents |
| `mcp_data_catalogue` | `MCP /mcp` | Haystack Tool, Fetcher Documents |
| `mcp_risk_sentiment` | `MCP /mcp` | Haystack Tool, Fetcher Documents |
| `mcp_macro_news` | `MCP /mcp` | Haystack Tool, Fetcher Documents |
| `mcp_release_calendar` | `MCP /mcp` | Haystack Tool, Fetcher Documents |
| `mcp_release_calendar_visual_artifact` | `MCP /mcp` | Haystack Tool, Fetcher Documents |
| `mcp_event_predictions` | `MCP /mcp` | Haystack Tool, Fetcher Documents |
| `mcp_latest_announcements` | `MCP /mcp` | Haystack Tool, Fetcher Documents |
| `mcp_announcement_changes` | `MCP /mcp` | Haystack Tool, Fetcher Documents |
| `mcp_press_releases` | `MCP /mcp` | Haystack Tool, Fetcher Documents |
| `mcp_macro_factor` | `MCP /mcp` | Haystack Tool, Fetcher Documents |
| `mcp_fx_reference_sources` | `MCP /mcp` | Haystack Tool, Fetcher Documents |
| `mcp_fx_reference_universe` | `MCP /mcp` | Haystack Tool, Fetcher Documents |
| `mcp_fx_intraday_reference_rates` | `MCP /mcp` | Haystack Tool, Fetcher Documents |
| `mcp_rate_curve` | `MCP /mcp` | Haystack Tool, Fetcher Documents |
| `mcp_rate_differentials` | `MCP /mcp` | Haystack Tool, Fetcher Documents |
| `mcp_latest_commodities` | `MCP /mcp` | Haystack Tool, Fetcher Documents |
| `mcp_forex` | `MCP /mcp` | Haystack Tool, Fetcher Documents |
| `mcp_seasonality` | `MCP /mcp` | Haystack Tool, Fetcher Documents |
| `mcp_indicator_query` | `MCP /mcp` | Haystack Tool, Fetcher Documents |
| `mcp_plot_visual_artifact` | `MCP /mcp` | Haystack Tool, Fetcher Documents |
| `mcp_indicator_visual_artifact` | `MCP /mcp` | Haystack Tool, Fetcher Documents |
| `mcp_forex_visual_artifact` | `MCP /mcp` | Haystack Tool, Fetcher Documents |
| `mcp_commodities_visual_artifact` | `MCP /mcp` | Haystack Tool, Fetcher Documents |
| `mcp_cot_visual_artifact` | `MCP /mcp` | Haystack Tool, Fetcher Documents |
| `mcp_policy_rate_differential_visual_artifact` | `MCP /mcp` | Haystack Tool, Fetcher Documents |
| `mcp_macro_briefing_task` | `MCP /mcp` | Haystack Tool, Fetcher Documents |
| `mcp_indicator_intel_task` | `MCP /mcp` | Haystack Tool, Fetcher Documents |
| `mcp_pair_intel_task` | `MCP /mcp` | Haystack Tool, Fetcher Documents |
| `mcp_macro_heatmap_task` | `MCP /mcp` | Haystack Tool, Fetcher Documents |
| `mcp_policy_scenario_modeler_task` | `MCP /mcp` | Haystack Tool, Fetcher Documents |
| `mcp_macro_war_room_task` | `MCP /mcp` | Haystack Tool, Fetcher Documents |
| `mcp_event_impact_replay_task` | `MCP /mcp` | Haystack Tool, Fetcher Documents |
| `mcp_quant_scenario_lab_task` | `MCP /mcp` | Haystack Tool, Fetcher Documents |
| `mcp_known_at_time_task` | `MCP /mcp` | Haystack Tool, Fetcher Documents |
| `mcp_macro_regime_classifier_task` | `MCP /mcp` | Haystack Tool, Fetcher Documents |
| `mcp_release_risk_score_task` | `MCP /mcp` | Haystack Tool, Fetcher Documents |
| `mcp_portfolio_risk_engine_task` | `MCP /mcp` | Haystack Tool, Fetcher Documents |
| `mcp_fx_trade_setup_task` | `MCP /mcp` | Haystack Tool, Fetcher Documents |
| `mcp_fx_backtest_task` | `MCP /mcp` | Haystack Tool, Fetcher Documents |
| `mcp_macro_research_pack_task` | `MCP /mcp` | Haystack Tool, Fetcher Documents |
| `mcp_market_sessions` | `MCP /mcp` | Haystack Tool, Fetcher Documents |
| `mcp_cot_data` | `MCP /mcp` | Haystack Tool, Fetcher Documents |
| `mcp_commodities` | `MCP /mcp` | Haystack Tool, Fetcher Documents |
| `mcp_financial_prices` | `MCP /mcp` | Haystack Tool, Fetcher Documents |
| `mcp_official_dataset_family` | `MCP /mcp` | Haystack Tool, Fetcher Documents |

REST supplies 23 operations and hosted MCP supplies 49 tools. The `mcp_` prefix distinguishes MCP capabilities from REST operations. Parameters retain their complete documented JSON schemas, including required fields, arrays, nested objects and enums.

USD catalogue, macro history and release-calendar examples are no-key. Access to other datasets follows the service's published access rules; a tool being discoverable is not a guarantee of account entitlement.

SSE event collection is finite: `max_events` and `max_seconds` bound the stream. MCP analytical operations retain their hosted semantics. MCP Apps resources and visual artifacts remain in the original response; these integrations expose data, documents and tools but do not embed an MCP Apps iframe renderer.

Forecasts retain their product labels. FXMacroData-generated predictions must not be relabelled as market consensus. No timestamps, missing observations or future release dates are inferred.
