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
- `entity_policy.py` classifies approved Home Assistant entity capabilities and risk.
- `ha_client.py` owns the persistent Home Assistant WebSocket transport and state cache;
  the composition root supplies its state-change callback.

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
