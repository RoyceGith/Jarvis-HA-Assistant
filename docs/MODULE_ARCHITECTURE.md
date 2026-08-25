# ZBRANO module architecture

## Runtime contract

Home Assistant continues to start `uvicorn app.main:app`. The FastAPI application,
route URLs, persistent `/data` paths, request schema fields, and stored payload formats
remain unchanged. `jarvis/app/main.py` is the composition root for stateful runtime
services and API routes.

## Backend modules

Pure, low-coupling behavior is extracted under `jarvis/app/services/`:

- `mcp_protocol.py` decodes JSON, SSE, structured MCP tool results, and MCP errors.
- `release_notes.py` renders, compacts, and reconciles canonical release records.
- `entity_policy.py` owns entity-policy persistence and migration, configured
  allowlists, access enforcement, alias-aware search, and entity risk classification.
- `ha_client.py` owns the persistent Home Assistant WebSocket transport and state cache;
  the composition root supplies its state-change callback.
- `ha_control.py` owns permission-gated Home Assistant state reads and power controls,
  including WebSocket-first verification and the existing REST resilience fallback.
- `playwright_bridge.py` owns the local-only Playwright MCP session, browser evidence,
  output bounds, credential redaction, preflight diagnostics, and built-in plugin status.
- `web_search.py` owns hosted-search configuration, search guidance, progress,
  canonical source URLs, citation priority, and bounded source rendering.
- `openai_responses.py` owns non-streaming Responses API requests, HTTP error
  normalization, assistant-text extraction, and function-call extraction.
- `agent_runtime.py` resolves model, reasoning, context-window, response-preference,
  and saved-instruction settings for each assistant request.
- `tab_activity.py` calculates stable semantic revision markers used by the frontend
  to refresh chats, files, plugins, automations, notifications, calendar, and settings.
- `plugin_storage.py` owns atomic, permission-restricted JSON persistence for the
  installed-plugin registry and secrets while retaining their existing `/data` paths.
- `plugin_policy.py` owns public-HTTPS endpoint validation, built-in icon matching,
  URL identity normalization, and the established GitHub tool permission migration.
- `plugin_presentation.py` builds the existing public installed-plugin payload from
  registry records, secrets, OAuth scopes, tool permissions, and icon policy.
- `plugin_discovery.py` owns bounded remote MCP initialization, SSE/JSON tool-list
  decoding, redirect rejection, metadata limits, and initial tool permissions.
- `workshop_approvals.py` owns Workshop Memory approval decisions, 15-minute task
  grants, pending state, bounded argument summaries, and approval prompts.
- `mcp_approvals.py` owns native remote-MCP approval extraction, decisions, provider
  attribution, safe action summaries, pending state, and approval prompts.
- `tool_progress.py` maps local, hosted, and remote tool events to safe activity,
  progress-phase, and completion messages for chat streaming.
- `automation_intents.py` detects recurring Automation Brain requests, selects the
  bounded tool subset, supplies learned memory context, and renders workflow guidance.
- `home_assistant_intents.py` distinguishes immediate device commands and bounded
  history/timeline requests, then selects their approved Home Assistant tools.
- `calendar_intents.py` detects calendar requests, selects calendar tools, and renders
  the established appointment and reminder workflow guidance.
- `grinder_intents.py` detects Grinder diagnostic requests, selects the read-only
  monitor tools, and supplies the established evidence-first diagnostic guidance.
- `fast_memory_intents.py` detects personal Fast Memory requests and selects only
  the bounded remember, search, and forget tools.
- `developer_tools.py` owns the mode-gated targeted diagnostics and local Playwright
  tool schemas exposed during Developer Mode.

The API boundary models live in `jarvis/app/schemas.py`, keeping validation contracts
separate from route orchestration without changing their names or fields.

Stateful engines live under `jarvis/app/domains/`:

- `automations.py` owns Automation Brain persistence, Home Assistant area context,
  learning, deterministic matching, decisions, suggestions, and safe execution.
- `notifications.py` owns Notification Center persistence, channel discovery,
  quiet-hours policy, notification watches, and the watch worker.
- `calendar.py` owns local appointments, reminder schedules, reminder editing,
  cancellation, and Notification Center reminder delivery.
- `google_calendar.py` owns Google OAuth-backed calendar access, event mapping,
  preview, incremental synchronization, synchronization status, and its worker.
- `fast_memory.py` owns the existing SQLite record format, pruning, relevance,
  backup/restore, prompt context, and background exchange extraction.
- `workshop_memory.py` owns the Workshop Memory MCP HTTP pool, endpoint failover,
  result cache, dynamic tool discovery, serialization lock, and connection metrics.
- `grinder.py` owns the read-only MQTT telemetry subscriber, heartbeat supervision,
  bounded pre-failure buffers, incident persistence, diagnostic tools, and task lifecycle.
- `release_sync.py` owns Release Memory manifest validation, 11-note reconciliation,
  exact write verification, persisted progress, bounded retries, and worker lifecycle.
- `settings.py` owns `/data/jarvis_settings.json`, general instructions, preference
  defaults, ElevenLabs voice settings, and pronunciation-dictionary transformation.
- `conversations.py` owns `/data/chat_sessions.json`, bounded session state, titles,
  retention, internal diagnostic cleanup, attachment views, and per-session entity context.
- `files.py` owns chat uploads and Shared Files storage, metadata, bounded text
  extraction, attachment prompt context, listing, sorting, deletion, and chat-file cleanup.
- `gmail_direct.py` owns least-privilege Gmail tools, bounded untrusted-content
  decoding, unsent draft creation, OAuth scope checks, and write-audit redaction.
- `telegram_inbound.py` owns Telegram pairing state, chat isolation, event
  deduplication, Home Assistant event subscription, replies, and worker lifecycle.
- `developer_state.py` owns `/data/zbrano_developer_mode.json`, Developer Mode
  enablement, update timestamps, and the established developer safety instructions.

The composition root retains the FastAPI route wrappers and explicitly configures
each domain with its runtime dependencies after all providers have been defined.
Notification watches intentionally remain in the automation store for data
compatibility. Local Calendar and Google Calendar exchange storage operations through
configured callbacks. Fast Memory retains `/data/zbrano_fast_memory.sqlite3`, and
Workshop Memory retains the same endpoint selection and cache semantics. Startup and
shutdown explicitly delegate Grinder and Release Memory task ownership to their
domains while retaining composition ownership for the other task objects.
Future extractions must retain `app.main:app`, use
dependency injection rather than circular imports, and preserve persisted schemas.

## Frontend modules

`jarvis/app/static/index.html` owns semantic markup and ordered asset declarations.
The initial theme bootstrap remains inline to prevent a theme flash. All other
frontend source is direct, checked-in code:

- `css/` contains the base system and ordered compatibility layers.
- `js/core.js` owns the original application controller.
- `js/chat/`, `voice/`, `entities/`, `automations/`, `notifications/`, `calendar/`,
  `memory/`, `files/`, `plugins/`, `integrations/`, `developer/`, `grinder/`, and
  `ui/` contain domain-specific controllers in their established execution order.

Scripts remain classic scripts because the existing controllers intentionally share
the browser global lexical environment. Converting them to ES modules requires a
separate dependency-explicit refactor and must not be mixed with this physical split.

## Validation contract

- `validate_inline_js.py` validates the inline bootstrap and every referenced local
  JavaScript source with Node.
- `validate_new_chat_wiring.py` resolves referenced scripts before checking wiring.
- Source-level tests aggregate direct backend and frontend modules through
  `tests/backend_source.py` and `tests/frontend_source.py`.
- The Docker build compiles the complete `app` package, not only the composition root.
- Extracted assets are served with no-cache headers so Home Assistant upgrades cannot
  combine a new HTML shell with stale JavaScript or CSS.
