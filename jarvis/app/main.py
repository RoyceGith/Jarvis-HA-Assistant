from __future__ import annotations

import asyncio
import contextlib
import hashlib
import json
import os
import re
import shutil
import time
from pathlib import Path
from typing import Any, AsyncIterator

from .intent_router import parse_local_ha_intent

from .domains.automations import (
    configure_automation_domain,
    AUTOMATION_ENGINE_LOCK,
    AUTOMATION_PENDING_TASKS,
    _activate_automation,
    _automation_brain_state_change,
    _automation_entity_role,
    _automation_evaluate_state_change,
    _automation_event,
    _automation_execute_action,
    _automation_label_blocks_control,
    _automation_payload_http,
    _automation_refresh_area_context,
    _automation_save,
    _prepare_chat_automation,
    automation_brain_memory_context,
    automation_entity_memory_context,
    automation_store,
)
from .domains.notifications import (
    configure_notification_domain,
    NOTIFICATION_STORAGE_PATH,
    _create_notification_watch,
    _notification_delivery,
    _notification_quiet_now,
    _notification_save,
    notification_channels,
    notification_store,
    notification_watch_worker,
    notification_watches,
)

from .domains.calendar import (
    configure_calendar_domain,
    CALENDAR_REMINDER_OFFSETS,
    CALENDAR_STORAGE_PATH,
    _calendar_save,
    _cancel_calendar_appointment,
    _create_calendar_appointment,
    _update_calendar_reminders,
    calendar_reminder_worker,
    calendar_store,
    list_calendar_appointments,
)
from .domains.google_calendar import (
    configure_google_calendar_domain,
    GOOGLE_CALENDAR_API_BASE,
    GOOGLE_CALENDAR_OAUTH_SCOPES,
    GOOGLE_CALENDAR_RESOURCE_URL,
    _google_calendar_plugin_id,
    _google_calendar_sync_save,
    google_calendar_connected,
    google_calendar_list_calendars,
    google_calendar_preview,
    google_calendar_sync_once,
    google_calendar_sync_status,
    google_calendar_sync_store,
    google_calendar_sync_worker,
)
from .domains.fast_memory import (
    configure_fast_memory_domain,
    FAST_MEMORY_TASKS,
    _fast_memory_connect,
    delete_fast_memory,
    export_fast_memory,
    fast_memory_input,
    fast_memory_search,
    fast_memory_status,
    forget_fast_memory,
    restore_fast_memory,
    schedule_fast_memory_extraction,
    upsert_fast_memory,
)
from .domains.workshop_memory import (
    configure_workshop_memory_domain,
    call_workshop_memory_tool,
    call_workshop_memory_tool_uncached,
    close_mcp_client,
    get_mcp_client,
    refresh_workshop_memory_tools,
    select_workshop_memory_endpoint,
    workshop_memory_function_tools,
    workshop_memory_runtime_status,
    workshop_memory_tool_permission,
)
from .domains.grinder import (
    GRINDER_MONITOR_TOOLS,
    get_grinder_incident,
    grinder_monitor_status,
    list_grinder_incidents,
    start_grinder_monitor,
    stop_grinder_monitor,
)
from .domains.release_sync import (
    cancel_release_sync,
    configure_release_sync_domain,
    release_sync_enabled,
    release_sync_status,
    schedule_release_sync,
    stop_release_sync,
)
from .domains.settings import (
    ELEVENLABS_MODELS,
    ELEVENLABS_VOICE_DEFAULTS,
    GENERAL_INSTRUCTIONS_MAX_CHARS,
    SETTINGS_STORAGE_PATH,
    append_general_instruction,
    apply_pronunciation_dictionary,
    load_elevenlabs_voice_settings,
    load_general_instructions,
    load_preferences,
    load_settings_payload,
    save_elevenlabs_voice_settings,
    save_general_instructions,
    save_preferences,
    save_settings_payload,
)
from .domains.conversations import (
    CHAT_CONTEXT_MAX_MESSAGES,
    CHAT_SESSIONS,
    CHAT_SESSION_META,
    CHAT_SESSION_ORDER,
    CHAT_STORAGE_PATH,
    append_chat_message,
    chat_title,
    clear_chat_history,
    configure_conversations_domain,
    get_chat_history,
    get_session_entity,
    is_entity_followup,
    is_internal_chat_session,
    load_chat_sessions,
    model_chat_history,
    persist_chat_sessions,
    prune_expired_chats,
    public_chat_message,
    purge_internal_chat_sessions,
    remember_session_entity,
)
from .domains.files import (
    FILE_ID_RE,
    SHARED_FILE_ROOT,
    attachment_context,
    chat_upload_path,
    clear_chat_files,
    delete_shared_files as delete_shared_file_ids,
    list_files,
    list_shared_files as shared_file_records,
    store_upload,
)
from .domains.gmail_direct import (
    GMAIL_DIRECT_TOOL_NAMES,
    GMAIL_DIRECT_WRITE_TOOLS,
    GMAIL_MCP_OAUTH_SCOPES,
    GMAIL_MCP_RESOURCE_URL,
    _gmail_plugin_id,
    configure_gmail_direct_domain,
    execute_gmail_direct_tool,
    gmail_direct_function_tools,
    gmail_direct_tool_records,
    gmail_direct_write_calls,
    pending_has_gmail_write,
    safe_tool_audit_arguments,
)
from .domains.telegram_inbound import (
    configure_telegram_inbound_domain,
    save_telegram_inbound,
    start_telegram_inbound as start_telegram_inbound_worker,
    stop_telegram_inbound as stop_telegram_inbound_worker,
    telegram_inbound_store,
    telegram_public_status,
)
from .domains.developer_state import (
    DEVELOPER_STATE_PATH,
    developer_mode_enabled,
    developer_system_instructions,
    set_developer_mode,
)

from .schemas import (
    ChatRequest,
    ChatSessionCreate,
    ChatRenameRequest,
    JarvisSettingsUpdate,
    AgentSettingsUpdate,
    CatalogInstallRequest,
    PluginOAuthStartRequest,
    PluginInstallRequest,
    PluginToolUpdate,
    AutonomySettingsRequest,
    AutonomousAutomationRequest,
    AutomationChatDraftRequest,
    AutomationDiscoveryFeedbackRequest,
    NotificationCenterSettingsRequest,
    NotificationTestRequest,
    NotificationWatchRequest,
    NotificationWatchStateRequest,
    CalendarAppointmentRequest,
    CalendarRemindersUpdateRequest,
    GoogleCalendarSyncSettingsRequest,
    FastMemoryWriteRequest,
    FastMemoryForgetRequest,
    TelegramInboundSettingsRequest,
    TelegramInboundUnlinkRequest,
    SettingsRestoreRequest,
    SpeechRequest,
    EntityCatalogItem,
    EntityCatalogDraftRequest,
    EntityPolicyUpdate,
    NotificationDeliveryDeleteRequest,
    SharedFilesDeleteRequest,
    DeveloperModeRequest,
    DeveloperInvestigationRequest,
)

from .services.entity_policy import (
    ENTITY_POLICY_PATH,
    HA_CONTROL_ENTITIES,
    HA_READ_ENTITIES,
    SAFE_CONTROL_DOMAINS,
    V063_ENTITY_POLICY_PATH,
    V063_MIGRATION_MARKER,
    _search_tokens,
    classify_entity_risk,
    configure_entity_policy_service,
    effective_entity_access,
    ensure_control_allowed,
    ensure_read_allowed,
    entity_domain,
    find_approved_entities,
    load_entity_policy,
    save_entity_policy,
    should_auto_approve_entity,
)
from .services.ha_client import HomeAssistantWebSocketClient
from .services.ha_control import (
    _ha_power_state_matches,
    configure_ha_control_service,
    ha_get_state,
    ha_get_state_rest,
    ha_set_power,
    normalize_ha_state,
)
from .services.mcp_protocol import (
    MCPError,
    _decode_sse,
    _find_result,
    _read_mcp_response,
    decode_workshop_tool_result,
)
from .services.release_notes import (
    _insert_after_title,
    render_current_release_truth,
    render_release_history_backfill,
    upsert_marked_release_history_entry,
)
from .services.playwright_bridge import (
    PLAYWRIGHT_REQUIRED_TOOLS,
    configure_playwright_bridge,
    inspect_zbrano_ui_with_playwright,
    playwright_builtin_plugin,
    playwright_mcp_inventory,
    playwright_preflight_summary,
)
from .services.web_search import (
    canonical_web_source_url,
    configure_web_search_service,
    native_web_search_tool,
    response_web_sources,
    web_search_include_options,
    web_search_progress,
    web_search_quality_instructions,
    web_search_tool_choice,
    web_sources_markdown,
)
from .services.openai_responses import (
    OpenAIError,
    configure_openai_responses,
    create_openai_response,
    function_calls,
    openai_error_message,
    response_text,
)
from .services.agent_runtime import (
    active_agent_model,
    active_reasoning_effort,
    agent_reasoning_payload,
    chat_context_limit,
    configure_agent_runtime,
    effective_system_instructions,
)
from .services.tab_activity import (
    configure_tab_activity_service,
    tab_activity_revisions,
)
from .services.plugin_storage import (
    PLUGIN_REGISTRY_PATH,
    PLUGIN_SECRETS_PATH,
    _plugin_load,
    _plugin_save,
    plugin_registry,
    plugin_secrets,
)
from .services.plugin_policy import (
    _apply_github_tool_policy,
    _github_discovered_permission,
    _is_github_plugin,
    _plugin_url_key,
    plugin_icon_url,
    validate_plugin_url,
)
from .services.plugin_presentation import (
    configure_plugin_presentation,
    plugin_public,
)
from .services.plugin_discovery import (
    _mcp_response_json,
    configure_plugin_discovery,
    discover_plugin_tools,
)
from .services.workshop_approvals import (
    PENDING_WORKSHOP_APPROVALS,
    WORKSHOP_TASK_APPROVAL_GRANTS,
    configure_workshop_approvals,
    grant_workshop_memory_task_approval,
    store_workshop_memory_approval,
    summarize_workshop_memory_arguments,
    workshop_memory_approval_decision,
    workshop_memory_approval_prompt,
    workshop_memory_task_approval_active,
    workshop_memory_write_calls,
    workshop_write_call_ids,
)
from .services.mcp_approvals import (
    PENDING_MCP_APPROVALS,
    configure_mcp_approvals,
    mcp_approval_decision,
    mcp_approval_plugin_id,
    mcp_approval_prompt,
    mcp_approval_provider,
    mcp_approval_requests,
    mcp_approval_summary,
)
from .services.tool_progress import (
    _tool_completion_status,
    _tool_progress_phases,
    configure_tool_progress,
    local_tool_activity,
    openai_tool_activity,
    remote_mcp_progress,
)
from .services.automation_intents import (
    automation_memory_input,
    automation_priority_tools,
    automation_system_instructions,
    configure_automation_intents,
    is_automation_intent,
)
from .services.home_assistant_intents import (
    configure_home_assistant_intents,
    home_assistant_history_system_instructions,
    home_assistant_history_tools,
    home_assistant_priority_tools,
    is_home_assistant_history_intent,
    is_home_assistant_priority_intent,
)
from .services.calendar_intents import (
    calendar_priority_tools,
    calendar_system_instructions,
    configure_calendar_intents,
    is_calendar_intent,
)
from .services.grinder_intents import (
    configure_grinder_intents,
    grinder_priority_tools,
    grinder_system_instructions,
    is_grinder_diagnostic_intent,
)
from .services.fast_memory_intents import (
    configure_fast_memory_intents,
    fast_memory_priority_tools,
    is_fast_memory_intent,
)
from .services.developer_tools import configure_developer_tools, developer_runtime_tools
from .services.ha_history import (
    HA_LIVE_EVENTS,
    configure_ha_history_service,
    correlate_home_assistant_timeline,
    dispatch_ha_state_changed as _dispatch_ha_state_changed,
    get_home_assistant_history,
    search_home_assistant_logbook,
)
from .services.plugin_catalog import (
    catalog_entry as _catalog_entry,
    configure_plugin_catalog_service,
    fetch_plugin_catalog as _fetch_plugin_catalog,
    plugin_catalog_payload,
    verify_catalog_result_contract as _verify_catalog_result_contract,
)
from .services.plugin_oauth import (
    PLUGIN_OAUTH_FLOWS,
    PLUGIN_OAUTH_PATH,
    configure_plugin_oauth_service,
    oauth_discover as _oauth_discover,
    oauth_exchange_token as _oauth_exchange_token,
    oauth_pkce as _oauth_pkce,
    oauth_popup_response as _oauth_popup_response,
    oauth_register_client as _oauth_register_client,
    oauth_safe_json as _oauth_safe_json,
    oauth_scope_set as _oauth_scope_set,
    oauth_token_request_auth as _oauth_token_request_auth,
    oauth_validate_https_url as _oauth_validate_https_url,
    oauth_validate_redirect_uri as _oauth_validate_redirect_uri,
    plugin_oauth_records,
)
from .services.google_oauth import (
    configure_google_oauth_service,
    enforce_stored_gmail_scope_policy,
    revoke_rejected_oauth_token as _revoke_rejected_oauth_token,
    validate_gmail_oauth_grant as _validate_gmail_oauth_grant,
    validate_google_calendar_oauth_grant as _validate_google_calendar_oauth_grant,
)
from .services.github_device_oauth import (
    GitHubDeviceFlowError,
    complete_github_device_flow,
    configure_github_device_oauth,
    github_oauth_client_id as _github_oauth_client_id,
    start_github_device_flow,
)
from .services.runtime_routing import (
    configure_runtime_routing,
    priority_system_instructions,
    runtime_chat_tools,
)
from .services.developer_support import (
    DEVELOPER_FEATURE_SPECS,
    DEVELOPER_FRONTEND_PATH,
    DEVELOPER_REPOSITORY,
    _developer_check,
    _developer_frontend_source,
    _resolve_developer_feature,
)
from .services.wake_calibration import (
    WAKE_CALIBRATION_DIR,
    WAKE_NEGATIVE_DIR,
    WAKE_POSITIVE_DIR,
    WAKE_VERIFIER_ENABLED_PATH,
    WAKE_VERIFIER_PATH,
    WAKE_VERIFIER_TRAIN_LOCK,
    _new_wake_shadow_model,
    _train_personal_wake_verifier,
    _wake_calibration_status,
    _wake_clip_quality,
)

import httpx
import websockets
from websockets.exceptions import ConnectionClosed
from fastapi import FastAPI, File, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, Response, StreamingResponse

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"

HA_API_BASE = "http://supervisor/core/api"
HA_WS_URL = "ws://supervisor/core/websocket"
SUPERVISOR_TOKEN = os.getenv("SUPERVISOR_TOKEN", "")
WORKSHOP_MEMORY_URL = os.getenv(
    "WORKSHOP_MEMORY_URL",
    "http://workshop-memory.local:3001/mcp",
).rstrip("/")
WORKSHOP_MEMORY_INTERNAL_URL = os.getenv(
    "WORKSHOP_MEMORY_INTERNAL_URL",
    "http://workshop_memory:3001/mcp",
).rstrip("/")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
OPENAI_TRANSCRIPTION_MODEL = os.getenv(
    "OPENAI_TRANSCRIPTION_MODEL", "gpt-4o-transcribe"
)
OPENAI_TTS_MODEL = os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
OPENAI_TRANSCRIPTIONS_URL = "https://api.openai.com/v1/audio/transcriptions"
OPENAI_SPEECH_URL = "https://api.openai.com/v1/audio/speech"
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "").strip()
ELEVENLABS_VOICE_NAME = os.getenv("ELEVENLABS_VOICE_NAME", "ElevenLabs").strip() or "ElevenLabs"
ELEVENLABS_MODEL_ID = os.getenv("ELEVENLABS_MODEL_ID", "eleven_flash_v2_5").strip()
ELEVENLABS_SPEECH_URL = "https://api.elevenlabs.io/v1/text-to-speech"
SPEECH_PROVIDER = os.getenv("SPEECH_PROVIDER", "openai").strip().lower()
SPEECH_FALLBACK_TO_OPENAI = os.getenv("SPEECH_FALLBACK_TO_OPENAI", "true").strip().lower() in {
    "1", "true", "yes", "on",
}
VOICE_UPLOAD_MAX_BYTES = 12 * 1024 * 1024
TTS_VOICES = {
    "alloy", "ash", "ballad", "coral", "echo", "fable", "nova", "onyx",
    "sage", "shimmer", "verse", "marin", "cedar",
}

PENDING_LOW_RISK_ACTIONS: dict[str, dict[str, Any]] = {}
PENDING_AUTOMATION_CONFIRMATIONS: dict[str, str] = {}





























































































DATA_DIR = Path("/data")


# Grinder deep monitoring is intentionally one-way. ZBRANO subscribes to
# diagnostic topics and never publishes commands to the machine controller.




























ha_ws = HomeAssistantWebSocketClient(
    HA_WS_URL,
    SUPERVISOR_TOKEN,
    lambda event: _dispatch_ha_state_changed(event),
)

app = FastAPI(
    title="ZBRANO",
    version="0.13.45",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)
















WORKSHOP_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "update_calendar_reminders",
        "description": (
            "Replace the reminder schedule and optional notification destination for one existing ZBRANO "
            "calendar appointment. List appointments first when its exact ID is unknown or the title is "
            "ambiguous. The user's explicit request to change reminders authorizes this update."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "appointment_id": {"type": "string", "description": "Exact appointment ID."},
                "destination": {"type": "string", "description": "Optional notify entity; blank uses the Notification Center default."},
                "reminder_offsets_minutes": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Complete replacement list of minutes before start; [] removes all reminders."
                }
            },
            "required": ["appointment_id", "destination", "reminder_offsets_minutes"],
            "additionalProperties": False
        },
        "strict": True
    },
    {
        "type": "function",
        "name": "create_calendar_appointment",
        "description": (
            "Create a ZBRANO calendar appointment after the user explicitly asks for it and all essential "
            "details are known. If the date, start time, or reminder preference is missing, ask one concise "
            "follow-up question before calling this tool. DD.MM.YYYY means day-month-year and HH.MM means "
            "local 24-hour time. The explicit request authorizes creation without another approval prompt."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Short appointment title."},
                "start_at": {"type": "string", "description": "ISO-8601 appointment start, preferably with the user's local UTC offset."},
                "duration_minutes": {"type": "integer", "description": "Duration in minutes; use 60 when the user accepts the default."},
                "location": {"type": "string", "description": "Optional location, or an empty string."},
                "notes": {"type": "string", "description": "Optional notes, or an empty string."},
                "destination": {"type": "string", "description": "Optional notify entity; blank uses Notification Center default."},
                "reminder_offsets_minutes": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Minutes before start. Same day defaults to 120, day before to 1440, both to [1440,120], and [] means no reminder."
                }
            },
            "required": ["title", "start_at", "duration_minutes", "location", "notes", "destination", "reminder_offsets_minutes"],
            "additionalProperties": False
        },
        "strict": True
    },
    {
        "type": "function",
        "name": "list_calendar_appointments",
        "description": "List ZBRANO calendar appointments and reminder delivery state. Use this before answering schedule questions or cancelling an appointment.",
        "parameters": {
            "type": "object",
            "properties": {"include_past": {"type": "boolean", "description": "Include completed past appointments when true."}},
            "required": ["include_past"],
            "additionalProperties": False
        },
        "strict": True
    },
    {
        "type": "function",
        "name": "cancel_calendar_appointment",
        "description": "Cancel one ZBRANO calendar appointment by exact ID after the user explicitly asks to cancel or delete it. List appointments first if the ID is unknown or the title is ambiguous.",
        "parameters": {
            "type": "object",
            "properties": {"appointment_id": {"type": "string", "description": "Exact appointment ID returned by list_calendar_appointments."}},
            "required": ["appointment_id"],
            "additionalProperties": False
        },
        "strict": True
    },
    {
        "type": "function",
        "name": "prepare_autonomous_automation",
        "description": (
            "Prepare a disabled, reviewable ZBRANO automation draft after the user asks for recurring behavior. "
            "Resolve every natural entity name with find_home_assistant_entities and inspect action capabilities "
            "with get_home_assistant_state first. If a required entity is ambiguous, ask one concise question and "
            "do not call this tool yet. This tool never enables or executes the automation. It saves a structured "
            "preview, remembers confirmed natural-name mappings, and requires a separate user confirmation before activation."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "objective": {"type": "string"},
                "trigger_alias": {"type": "string", "description": "Natural trigger name used by the user."},
                "trigger_entity": {"type": "string"},
                "trigger_operator": {"type": "string", "enum": ["any_change", "changes_to", "equals", "not_equals", "above", "below"]},
                "trigger_value": {"type": "string"},
                "trigger_for_seconds": {"type": "integer"},
                "presence_alias": {"type": "string"},
                "presence_entity": {"type": "string"},
                "signal_entities": {"type": "array", "items": {"type": "string"}},
                "suggestion": {"type": "string"},
                "action_alias": {"type": "string", "description": "Natural action-device name used by the user."},
                "action_entity": {"type": "string"},
                "action_service": {"type": "string"},
                "action_service_data": {"type": "object"},
                "execution_policy": {"type": "string", "enum": ["observe", "suggest", "approval_required", "autonomous"]},
                "cooldown_minutes": {"type": "integer"},
                "risk_level": {"type": "string", "enum": ["informational", "low", "controlled", "high"]},
                "reversible_only": {"type": "boolean"},
                "max_actions_per_hour": {"type": "integer"},
                "notify_on_action": {"type": "boolean"}
            },
            "required": ["name", "objective", "trigger_alias", "trigger_entity", "trigger_operator", "trigger_value", "trigger_for_seconds", "presence_alias", "presence_entity", "signal_entities", "suggestion", "action_alias", "action_entity", "action_service", "action_service_data", "execution_policy", "cooldown_minutes", "risk_level", "reversible_only", "max_actions_per_hour", "notify_on_action"],
            "additionalProperties": False
        },
        "strict": False
    },
    {
        "type": "function",
        "name": "create_notification_watch",
        "description": (
            "Create and arm a notification-only automation when the user explicitly asks "
            "to be notified when a Home Assistant entity reaches a state. Use an exact "
            "entity ID, normally found first with find_home_assistant_entities. The explicit "
            "request authorizes creation; future matching events notify automatically."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Short watch name."},
                "entity_id": {"type": "string", "description": "Exact Home Assistant entity ID to watch."},
                "trigger_state": {"type": "string", "description": "Exact state that triggers the notification, such as on, open, or finished."},
                "destination": {"type": "string", "description": "Optional notify entity; blank uses the Notification Center default."},
                "severity": {"type": "string", "enum": ["information", "suggestion", "warning", "critical"]},
                "title": {"type": "string", "description": "Notification title."},
                "message": {"type": "string", "description": "Message to deliver when triggered."},
                "active_start": {"type": "string", "description": "Optional local HH:MM start time."},
                "active_end": {"type": "string", "description": "Optional local HH:MM end time."},
                "one_shot": {"type": "boolean", "description": "Disable after the first successful delivery."},
                "expires_at": {"type": "number", "description": "Optional Unix expiry time; use 0 for no expiry."},
                "cooldown_minutes": {"type": "integer", "description": "Minimum minutes between repeat deliveries."},
                "enabled": {"type": "boolean", "description": "Arm immediately when true."}
            },
            "required": ["name", "entity_id", "trigger_state", "destination", "severity", "title", "message", "active_start", "active_end", "one_shot", "expires_at", "cooldown_minutes", "enabled"],
            "additionalProperties": False
        },
        "strict": True
    },
    {
        "type": "function",
        "name": "list_projects",
        "description": "List available projects in the Workshop Memory Obsidian vault.",
        "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_project_context",
        "description": (
            "Load compact context for a named workshop project, including its "
            "overview, latest handoff, unresolved decisions, and requirements."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "project": {
                    "type": "string",
                    "description": "Exact project name.",
                },
                "include_requirements": {
                    "type": "boolean",
                    "description": "Whether project requirements should be included.",
                },
            },
            "required": ["project", "include_requirements"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_latest_handoff",
        "description": "Return the latest session handoff for a named project.",
        "parameters": {
            "type": "object",
            "properties": {
                "project": {"type": "string", "description": "Exact project name."},
            },
            "required": ["project"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_open_decisions",
        "description": "Return unresolved Open or Proposed design decisions for a project.",
        "parameters": {
            "type": "object",
            "properties": {
                "project": {"type": "string", "description": "Exact project name."},
            },
            "required": ["project"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_profile_summary",
        "description": "Return the user's compact workshop workflow and preferences summary.",
        "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_home_assistant_state",
        "description": "Read one approved Home Assistant entity state.",
        "parameters": {
            "type": "object",
            "properties": {
                "entity_id": {"type": "string", "description": "Exact Home Assistant entity ID."}
            },
            "required": ["entity_id"],
            "additionalProperties": False
        },
        "strict": True
    },
    {
        "type": "function",
        "name": "turn_on_home_assistant_entity",
        "description": "Immediately turn on one enabled entity whose access is low_risk_control_proposed. No extra approval is required.",
        "parameters": {
            "type": "object",
            "properties": {
                "entity_id": {"type": "string", "description": "Exact approved Home Assistant entity ID."}
            },
            "required": ["entity_id"],
            "additionalProperties": False
        },
        "strict": True
    },
    {
        "type": "function",
        "name": "turn_off_home_assistant_entity",
        "description": "Immediately turn off one enabled entity whose access is low_risk_control_proposed. No extra approval is required.",
        "parameters": {
            "type": "object",
            "properties": {
                "entity_id": {"type": "string", "description": "Exact approved Home Assistant entity ID."}
            },
            "required": ["entity_id"],
            "additionalProperties": False
        },
        "strict": True
    },
    {
        "type": "function",
        "name": "find_home_assistant_entities",
        "description": (
            "Find ZBRANO-approved Home Assistant entities by friendly name, "
            "entity ID, or alias. Use this before state or control calls when "
            "the user gives a natural device name."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural device name, alias, or partial entity ID."
                }
            },
            "required": ["query"],
            "additionalProperties": False
        },
        "strict": True
    },
    {
        "type": "function",
        "name": "list_home_assistant_entity_inventory",
        "description": (
            "Return the complete Home Assistant entity inventory for documentation, "
            "including entity IDs and stable metadata but excluding live state values. "
            "Use this when the user asks to inventory or document all HA entities."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "remember_fast_memory",
        "description": "Save or update one concise local Fast Memory when the user explicitly asks ZBRANO to remember it. Existing type/subject/key records are updated instead of duplicated.",
        "parameters": {
            "type": "object",
            "properties": {
                "kind": {"type": "string", "enum": ["profile", "preference", "project", "decision", "fact", "follow_up", "temporary"]},
                "subject": {"type": "string"}, "key": {"type": "string"}, "value": {"type": "string"},
                "summary": {"type": "string"}, "keywords": {"type": "array", "items": {"type": "string"}},
                "importance": {"type": "integer", "minimum": 1, "maximum": 5},
                "expires_at": {"type": "number", "description": "Unix expiry timestamp or 0 for permanent."}
            },
            "required": ["kind", "subject", "key", "value", "summary", "keywords", "importance", "expires_at"],
            "additionalProperties": False
        },
        "strict": True
    },
    {
        "type": "function",
        "name": "search_fast_memory",
        "description": "Search ZBRANO's fast local memory for profile, preference, project, decision, fact, follow-up, and session-summary context.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string"},
            "kind": {"type": "string", "enum": ["", "profile", "preference", "project", "decision", "fact", "follow_up", "session_summary", "temporary"]},
            "limit": {"type": "integer", "minimum": 1, "maximum": 50}
        }, "required": ["query", "kind", "limit"], "additionalProperties": False},
        "strict": True
    },
    {
        "type": "function",
        "name": "forget_fast_memory",
        "description": "Delete matching Fast Memory only when the user explicitly asks ZBRANO to forget or remove that remembered information.",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"], "additionalProperties": False},
        "strict": True
    },
    {
        "type": "function",
        "name": "get_home_assistant_history",
        "description": "Read bounded state history and deterministic trend summaries for one to eight ZBRANO-approved Home Assistant entities. This is read-only and never changes Home Assistant.",
        "parameters": {
            "type": "object",
            "properties": {
                "entity_ids": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 8},
                "hours": {"type": "integer", "minimum": 1, "maximum": 168},
                "max_points": {"type": "integer", "minimum": 10, "maximum": 240}
            },
            "required": ["entity_ids", "hours", "max_points"],
            "additionalProperties": False
        },
        "strict": True
    },
    {
        "type": "function",
        "name": "correlate_home_assistant_timeline",
        "description": "Build a bounded chronological timeline across approved Home Assistant entities, including state changes, logbook events, trends, and close-in-time correlation windows. Read-only.",
        "parameters": {
            "type": "object",
            "properties": {
                "entity_ids": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 8},
                "hours": {"type": "integer", "minimum": 1, "maximum": 168},
                "query": {"type": "string", "description": "Optional case-insensitive logbook text filter; use an empty string for all relevant events."},
                "limit": {"type": "integer", "minimum": 10, "maximum": 300}
            },
            "required": ["entity_ids", "hours", "query", "limit"],
            "additionalProperties": False
        },
        "strict": True
    },
    {
        "type": "function",
        "name": "search_home_assistant_logbook",
        "description": "Search bounded Home Assistant logbook events for one to eight approved entities. Read-only; returns only the requested time window and a maximum of 300 events.",
        "parameters": {
            "type": "object",
            "properties": {
                "entity_ids": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 8},
                "hours": {"type": "integer", "minimum": 1, "maximum": 168},
                "query": {"type": "string"},
                "limit": {"type": "integer", "minimum": 10, "maximum": 300}
            },
            "required": ["entity_ids", "hours", "query", "limit"],
            "additionalProperties": False
        },
        "strict": True
    },
    {
        "type": "function",
        "name": "save_general_instruction",
        "description": (
            "Append one behavior or preference to ZBRANO General Instructions. "
            "Call this only when the user explicitly asks to save, remember, add, "
            "or use a behavior as a standing instruction. Never infer permission "
            "to save from an ordinary example or correction."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "instruction": {
                    "type": "string",
                    "description": "A concise standalone instruction preserving the user's intent.",
                }
            },
            "required": ["instruction"],
            "additionalProperties": False,
        },
        "strict": True,
    }
]


BASE_SYSTEM_INSTRUCTIONS = """
You are ZBRANO, a practical workshop intelligence core assistant.

Workshop Memory is the source of truth for accepted project knowledge.
Use Workshop Memory tools whenever the user asks about projects, prior
decisions, requirements, current status, handoffs, next actions, or the
user's documented workflow. Never pretend to remember project facts that
were not returned by a tool.

Workshop Memory remains review-controlled. Its MCP tool catalog is discovered at
runtime. You may use advertised tools to create projects or templates, update
project progress, and add notes when the user requests it. Every discovered
tool not explicitly annotated read-only requires an approval prompt and must
not execute until the user approves the exact tool and arguments. Never claim
a permanent write completed until its tool result confirms success. Do not use
save_general_instruction as a substitute for a project note. Prefer one generic
write_project_note call when the user requests a Markdown note beneath Projects;
that tool can create missing folders and the note in one approved operation.
For project-wide content edits, discover and read each relevant note only once,
then batch independent write calls into as few response rounds as possible. Do
not repeatedly reread a note after a successful write merely to confirm it. If
the Workshop Memory server has no bulk replacement tool, update each relevant
note exactly once under task approval and report the completed scope.

You may read Home Assistant entities only when they are enabled in ZBRANO policy.
An enabled entity with access value `low_risk_control_proposed` is ALREADY
APPROVED for immediate control in this version; the word "proposed" is only a
legacy label. Follow the user's confirmation preference for these low-risk actions.
For a unique enabled match in the
light, switch, fan, input_boolean, or climate domain, call the requested turn-on or
turn-off tool immediately.

Never attempt to control locks, covers, machinery, grinders,
laser cutters, CNC systems, security systems, access control, or motion
equipment. If an entity is not enabled or has another access level, say so
clearly. When the user names a device naturally rather than providing an exact
entity ID, call find_home_assistant_entities first. The lookup performs exact,
partial, alias, and significant-word matching. If it returns
`recommended_unique_match`, use that entity immediately for the requested read
or control operation. Do not ask the user to choose search words. Ask a
clarifying question only when the tool reports multiple equally plausible
approved matches. Never guess an entity ID. Use the supplied conversation history to resolve follow-up
commands and references such as "it", "that device", "turn it back on", and
"now turn on". When the immediately preceding successful device action identifies
one unique entity, reuse that entity for a follow-up action unless the user
explicitly names another device.

For recurring Home Assistant behavior, use the Automation Brain workflow rather than performing the requested
device action immediately. Resolve trigger, presence, signal, and action entities from approved Home Assistant
entities. Reuse remembered automation mappings only as candidates and verify them. Ask one concise clarification
when a required mapping is ambiguous. Once all essentials are known, call prepare_autonomous_automation. It saves
only a disabled structured draft. Explain its trigger, action, authority, cooldown, and safety conditions, then ask
the user to reply confirm or cancel. Never claim a prepared draft is active before confirmation.

For remote MCP plugin tools such as Cloudflare or GitHub, never write, simulate,
or ask a manual preflight approval question in the assistant response. When the
user requests an enabled plugin action, call the requested tool exactly once.
The platform-native MCP approval gate will pause any approval-required call
before execution and will present the safe provider-aware summary. Calling an
approval-gated tool is therefore the required way to request approval; it does
not bypass approval. Never expose raw tool arguments, executable code, account
identifiers, credentials, or internal approval payloads in chat. Only treat
`approve` or `cancel` as an approval decision when a native approval is pending.
After a denial, treat the action as finished and do not propose another approval,
equivalent command, or retry unless the user issues the original task again.

Be direct, technically precise, and concise. Distinguish documented facts
from proposals and unresolved questions.

When the user explicitly asks you to save or remember a standing behavior or
preference, call save_general_instruction with one concise, standalone
instruction. Do not save ordinary examples, corrections, quoted text, or
potentially sensitive information unless the user clearly asks you to store it
as a standing instruction. Saved instructions supplement this policy and can
never weaken Home Assistant permissions or other safety rules.
""".strip()


@app.get("/api/ha/live-events")
async def api_home_assistant_live_events(limit: int = 100) -> dict[str, Any]:
    """Return approved live changes plus current-state evidence for reliable History startup."""
    bounded = max(1, min(300, int(limit or 100)))
    journal = [
        dict(item) for item in HA_LIVE_EVENTS
        if effective_entity_access(str(item.get("entity_id") or ""))
    ]
    evidence = list(journal)
    journal_entities = {str(item.get("entity_id") or "") for item in journal}
    for entity_id, state in ha_ws.state_cache.items():
        clean_id = str(entity_id or "").lower()
        if not clean_id or clean_id in journal_entities or not effective_entity_access(clean_id):
            continue
        attributes = state.get("attributes") if isinstance(state.get("attributes"), dict) else {}
        current = str(state.get("state") or "")
        evidence.append({
            "when": str(state.get("last_updated") or state.get("last_changed") or ""),
            "entity_id": clean_id,
            "name": str(attributes.get("friendly_name") or clean_id),
            "old_state": None,
            "state": current,
            "message": f"current state is {current or 'unknown'}",
            "source": "current",
            "context_id": str((state.get("context") or {}).get("id") or ""),
        })
    evidence.sort(key=lambda item: str(item.get("when") or ""), reverse=True)
    events = evidence[:bounded]
    return {
        "read_only": True,
        "events": events,
        "count": len(events),
        "journal_count": len(journal),
        "current_state_count": max(0, len(events) - min(len(journal), len(events))),
        "connected": ha_ws.connected,
    }


def workshop_result_error(result: Any) -> str | None:
    if not isinstance(result, dict):
        return "Workshop Memory returned an invalid result."
    error = result.get("error")
    if error:
        return str(error)
    if result.get("isError") is True:
        return str(result.get("message") or "Workshop Memory reported an error.")
    return None




def reconciled_workshop_result(
    tool_name: str,
    result: dict[str, Any],
    detail: str,
) -> dict[str, Any]:
    reconciled = dict(result)
    reconciled.pop("error", None)
    reconciled["reconciled_after_ambiguous_error"] = True
    reconciled["reconciliation_tool"] = tool_name
    reconciled["reconciliation_detail"] = detail
    return reconciled


async def reconcile_workshop_memory_write(
    tool_name: str,
    arguments: dict[str, Any],
    original_result: dict[str, Any],
) -> dict[str, Any]:
    """Verify ambiguous writes and retry only operations known to be safe."""
    if tool_name == "write_project_note":
        relative_path = str(arguments.get("relative_path") or "").strip()
        expected = str(arguments.get("content") or "")
        mode = str(arguments.get("mode") or "create").strip().lower()
        if not relative_path:
            return original_result

        existing: dict[str, Any] | None = None
        try:
            existing = await call_workshop_memory_tool_uncached(
                "read_project_note",
                {"relative_path": relative_path},
            )
        except Exception:
            existing = None

        actual = str((existing or {}).get("content") or "")
        already_applied = actual == expected or (
            mode == "append" and bool(expected) and actual.endswith(expected)
        )
        if already_applied:
            return reconciled_workshop_result(
                tool_name,
                {"relative_path": relative_path, "mode": mode, "verified": True},
                "The saved note content was read back and matched the approved write.",
            )

        if mode == "create" and existing and not workshop_result_error(existing):
            return {
                "error": (
                    "Workshop Memory returned an ambiguous create result, and the note "
                    "now exists with different content. Automatic retry stopped to avoid "
                    "overwriting a conflict."
                ),
                "relative_path": relative_path,
                "reconciliation_conflict": True,
            }
        if mode == "append":
            return {
                "error": (
                    "Workshop Memory returned an ambiguous append result and exact suffix "
                    "verification did not confirm it. Automatic retry stopped to prevent "
                    "duplicate appended content."
                ),
                "relative_path": relative_path,
                "reconciliation_uncertain": True,
            }

        # A create of a missing note and an explicitly approved replacement are
        # safe to retry once. The original approval already covered these exact
        # arguments; no broader mutation is introduced here.
        try:
            retry_result = await call_workshop_memory_tool_uncached(
                tool_name,
                arguments,
            )
        except Exception as exc:
            return {
                **original_result,
                "reconciliation_attempted": True,
                "reconciliation_error": str(exc)[:300],
            }
        if workshop_result_error(retry_result):
            return {
                **retry_result,
                "reconciliation_attempted": True,
            }
        return reconciled_workshop_result(
            tool_name,
            retry_result,
            "The missing approved note operation succeeded on one bounded retry.",
        )

    if tool_name == "apply_project_template_pack":
        # Template packs are server-defined create-missing operations. Repeating
        # the exact approved call preserves existing notes and cannot duplicate
        # or overwrite them.
        try:
            retry_result = await call_workshop_memory_tool_uncached(
                tool_name,
                arguments,
            )
        except Exception as exc:
            return {
                **original_result,
                "reconciliation_attempted": True,
                "reconciliation_error": str(exc)[:300],
            }
        if workshop_result_error(retry_result):
            return {
                **retry_result,
                "reconciliation_attempted": True,
            }
        return reconciled_workshop_result(
            tool_name,
            retry_result,
            "The idempotent template pack was rerun and only missing notes were created.",
        )

    # Unknown write tools are never retried automatically. Their state may be
    # inspected by a later read-only request, but guessing could duplicate or
    # overwrite permanent project data.
    return {
        **original_result,
        "reconciliation_supported": False,
        "reconciliation_detail": (
            "Automatic retry is unavailable for this write type; inspect current "
            "Workshop Memory state before retrying."
        ),
    }


def workshop_execution_fallback_reply(tool_outputs: Any) -> str:
    succeeded = 0
    failed = 0
    reconciled = 0
    for output in tool_outputs if isinstance(tool_outputs, list) else []:
        if not isinstance(output, dict):
            continue
        raw = output.get("output")
        try:
            result = json.loads(raw) if isinstance(raw, str) else raw
        except (json.JSONDecodeError, TypeError):
            result = {"error": "Invalid tool result"}
        if workshop_result_error(result):
            failed += 1
        else:
            succeeded += 1
            if isinstance(result, dict) and result.get("reconciled_after_ambiguous_error"):
                reconciled += 1
    if failed:
        return (
            "Workshop Memory execution completed, but the response step failed. "
            f"State reconciliation confirmed {succeeded} operation(s); {failed} "
            "operation(s) still reported an error. Inspect current project state "
            "before retrying the failed operations."
        )
    detail = f" Reconciled after an ambiguous result: {reconciled}." if reconciled else ""
    return (
        "Workshop Memory execution completed successfully, but the normal response "
        f"could not be generated. Confirmed operations: {succeeded}.{detail} No "
        "automatic duplicate retry is required."
    )


async def create_workshop_continuation_response(
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Return a truthful synthetic completion if post-write AI rendering fails."""
    try:
        return await create_openai_response(payload)
    except Exception:
        reply = workshop_execution_fallback_reply(payload.get("input"))
        return {
            "id": str(payload.get("previous_response_id") or "workshop-reconciled"),
            "output": [
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": reply}],
                }
            ],
        }


async def execute_tool_calls(
    calls: list[dict[str, Any]],
    audit: list[dict[str, Any]],
    session_id: str = "default",
    approved_workshop_call_ids: set[str] | None = None,
    denied_workshop_call_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    tool_outputs: list[dict[str, Any]] = []
    approved_workshop_call_ids = approved_workshop_call_ids or set()
    denied_workshop_call_ids = denied_workshop_call_ids or set()
    allowed_function_tools = (
        developer_runtime_tools()
        if developer_mode_enabled()
        else WORKSHOP_TOOLS + GRINDER_MONITOR_TOOLS + workshop_memory_function_tools() + gmail_direct_function_tools()
    )
    allowed_names = {tool["name"] for tool in allowed_function_tools}
    if developer_mode_enabled():
        allowed_names.update(HOME_ASSISTANT_PRIORITY_TOOL_NAMES)

    for call in calls:
        name = call.get("name", "")
        call_id = call.get("call_id", "")
        try:
            arguments = json.loads(call.get("arguments", "{}"))
        except json.JSONDecodeError as exc:
            raise OpenAIError(f"Invalid tool arguments for {name}") from exc

        permission = workshop_memory_tool_permission(name)
        if name not in allowed_names:
            result: dict[str, Any] = {"error": f"Tool is not allowed: {name}"}
        elif permission == "write" and call_id in denied_workshop_call_ids:
            result = {"error": "User denied this Workshop Memory change."}
        elif permission == "write" and call_id not in approved_workshop_call_ids:
            result = {"error": "Explicit user approval is required before this Workshop Memory change."}
        else:
            try:
                if name == "get_home_assistant_history":
                    result = await get_home_assistant_history(arguments["entity_ids"], arguments["hours"], arguments["max_points"])
                elif name == "correlate_home_assistant_timeline":
                    result = await correlate_home_assistant_timeline(arguments["entity_ids"], arguments["hours"], arguments["query"], arguments["limit"])
                elif name == "search_home_assistant_logbook":
                    result = await search_home_assistant_logbook(arguments["entity_ids"], arguments["hours"], arguments["query"], arguments["limit"])
                elif name == "create_calendar_appointment":
                    result = await _create_calendar_appointment(CalendarAppointmentRequest(**arguments), source="chat")
                elif name == "update_calendar_reminders":
                    result = await _update_calendar_reminders(
                        str(arguments.get("appointment_id") or ""),
                        CalendarRemindersUpdateRequest(
                            destination=str(arguments.get("destination") or ""),
                            reminder_offsets_minutes=arguments.get("reminder_offsets_minutes") or [],
                        ),
                        source="chat",
                    )
                elif name == "list_calendar_appointments":
                    result = list_calendar_appointments(bool(arguments.get("include_past")))
                elif name == "cancel_calendar_appointment":
                    result = _cancel_calendar_appointment(str(arguments.get("appointment_id") or ""))
                elif name == "get_grinder_diagnostic_status":
                    result = grinder_monitor_status()
                elif name == "list_grinder_incidents":
                    result = list_grinder_incidents(arguments.get("limit", 20))
                elif name == "get_grinder_incident":
                    result = get_grinder_incident(arguments.get("incident_id", ""))
                elif name in GMAIL_DIRECT_TOOL_NAMES:
                    result = await execute_gmail_direct_tool(name, arguments)
                elif name == "create_notification_watch":
                    result = await _create_notification_watch(NotificationWatchRequest(**arguments), source="chat")
                elif name == "prepare_autonomous_automation":
                    result = await _prepare_chat_automation(AutomationChatDraftRequest(**arguments), session_id)
                elif name == "find_home_assistant_entities":
                    result = find_approved_entities(arguments["query"])
                elif name == "get_home_assistant_state":
                    result = await ha_get_state(arguments["entity_id"])
                elif name == "list_home_assistant_entity_inventory":
                    inventory = await list_ha_entities()
                    entities = inventory.get("entities") or []
                    result = {
                        "count": len(entities),
                        "entities": [
                            {
                                "entity_id": entity.get("entity_id"),
                                "friendly_name": entity.get("friendly_name"),
                                "domain": entity.get("domain"),
                                "device_class": entity.get("device_class"),
                                "unit": entity.get("unit"),
                            }
                            for entity in entities
                        ],
                        "note": "Inventory metadata only; live state values are intentionally excluded.",
                    }
                elif name == "turn_on_home_assistant_entity":
                    if load_preferences()["confirmation_strictness"] == "cautious":
                        result = {"error": "Cautious mode requires explicit confirmation through the local confirmation flow."}
                    else:
                        result = await ha_set_power(arguments["entity_id"], True)
                elif name == "turn_off_home_assistant_entity":
                    if load_preferences()["confirmation_strictness"] == "cautious":
                        result = {"error": "Cautious mode requires explicit confirmation through the local confirmation flow."}
                    else:
                        result = await ha_set_power(arguments["entity_id"], False)
                elif name == "investigate_zbrano_feature":
                    result = await asyncio.wait_for(
                        investigate_zbrano_feature(
                            arguments["feature"],
                            arguments["symptom"],
                        ),
                        timeout=30.0,
                    )
                elif name == "inspect_zbrano_ui_with_playwright":
                    result = await inspect_zbrano_ui_with_playwright(
                        arguments["path"],
                        arguments["surface"],
                        arguments["wait_ms"],
                    )
                elif name == "remember_fast_memory":
                    arguments["confidence"] = 1.0
                    arguments["pinned"] = bool(arguments.get("importance", 3) >= 5)
                    result = upsert_fast_memory(arguments, source_session=session_id, automatic=False)
                elif name == "search_fast_memory":
                    result = fast_memory_search(arguments.get("query", ""), kind=arguments.get("kind", ""), limit=arguments.get("limit", 20), session_id=session_id)
                elif name == "forget_fast_memory":
                    result = forget_fast_memory(arguments.get("query", ""))
                elif name == "save_general_instruction":
                    result = append_general_instruction(arguments["instruction"])
                else:
                    result = await (
                        call_workshop_memory_tool_uncached(name, arguments)
                        if permission == "write"
                        else call_workshop_memory_tool(name, arguments)
                    )

                if name in {
                    "get_home_assistant_state",
                    "turn_on_home_assistant_entity",
                    "turn_off_home_assistant_entity",
                } and "error" not in result:
                    remember_session_entity(
                        session_id,
                        result.get("entity_id") or arguments["entity_id"],
                        result.get("friendly_name"),
                        result.get("verified_state") or result.get("state"),
                    )
            except (asyncio.TimeoutError, MCPError, httpx.HTTPError, RuntimeError, PermissionError, ValueError, HTTPException) as exc:
                result = {"error": str(exc)}

        if (
            permission == "write"
            and call_id in approved_workshop_call_ids
            and workshop_result_error(result)
        ):
            result = await reconcile_workshop_memory_write(name, arguments, result)

        audit.append(
            {
                "tool": name,
                "arguments": safe_tool_audit_arguments(name, arguments),
                "success": "error" not in result,
            }
        )
        tool_outputs.append(
            {
                "type": "function_call_output",
                "call_id": call_id,
                "output": json.dumps(result, ensure_ascii=False),
            }
        )

    return tool_outputs


async def try_local_ha_route(
    message: str,
    session_id: str = "default",
) -> dict[str, Any] | None:
    """Execute a deterministic HA request, or return None for the model path."""
    previous_entity = get_session_entity(session_id)
    normalized = " ".join(message.lower().strip().split())
    pending_automation_store = globals().get("PENDING_AUTOMATION_CONFIRMATIONS", {})
    pending_automation = pending_automation_store.get(session_id)
    if pending_automation and normalized in {"confirm", "yes", "yes confirm", "confirm it", "enable it", "proceed"}:
        pending_automation_store.pop(session_id, None)
        try:
            result = _activate_automation(pending_automation, "chat_confirmation")
        except HTTPException as exc:
            return {"reply": f"I could not activate that automation: {exc.detail}", "tool_calls": []}
        preview = result["preview"]
        return {
            "reply": f"Activated {preview['name']}. Trigger: {preview['trigger']}. Authority: {preview['authority']}.",
            "tool_calls": [{"tool": "activate_autonomous_automation", "arguments": {"automation_id": pending_automation}, "success": True, "route": "local"}],
        }
    if pending_automation and normalized in {"cancel", "no", "no cancel", "do not", "don't"}:
        pending_automation_store.pop(session_id, None)
        return {"reply": "Cancelled. The automation remains saved as a disabled draft for later review.", "tool_calls": []}
    pending = PENDING_LOW_RISK_ACTIONS.get(session_id)
    if pending and normalized in {"confirm", "yes confirm", "confirm it", "proceed"}:
        intent = pending
        PENDING_LOW_RISK_ACTIONS.pop(session_id, None)
    elif pending and normalized in {"cancel", "no", "do not", "don't"}:
        PENDING_LOW_RISK_ACTIONS.pop(session_id, None)
        return {"reply": "Cancelled. No device action was taken.", "tool_calls": []}

    elif previous_entity and is_entity_followup(message):
        intent: dict[str, Any] = {
            "kind": "control" if "turn" in normalized or "switch" in normalized else "state",
            "entity": previous_entity,
            "source": "session_reference",
        }
        if intent["kind"] == "control":
            intent["turn_on"] = " on" in f" {normalized}" and " off" not in f" {normalized}"
    else:
        parsed = parse_local_ha_intent(message)
        if not parsed:
            return None
        lookup = find_approved_entities(parsed["query"])
        entity = lookup.get("recommended_unique_match")
        if not entity:
            return None
        intent = {**parsed, "entity": entity, "source": "approved_entity_lookup"}

    entity_id = intent["entity"]["entity_id"]
    if (
        intent["kind"] == "control"
        and load_preferences()["confirmation_strictness"] == "cautious"
        and pending is not intent
    ):
        PENDING_LOW_RISK_ACTIONS[session_id] = intent
        friendly_name = intent["entity"].get("friendly_name") or entity_id
        action = "turn on" if intent["turn_on"] else "turn off"
        return {
            "reply": f"Confirm: {action} {friendly_name}? Reply “confirm” to proceed or “cancel” to stop.",
            "tool_calls": [],
        }
    if intent["kind"] == "control":
        result = await ha_set_power(entity_id, bool(intent["turn_on"]))
        state = result.get("verified_state")
        friendly_name = result.get("friendly_name") or entity_id
        remember_session_entity(session_id, entity_id, friendly_name, state)
        reply = f"{friendly_name} is now {state or ('on' if intent['turn_on'] else 'off')}."
        tool_name = (
            "turn_on_home_assistant_entity"
            if intent["turn_on"]
            else "turn_off_home_assistant_entity"
        )
    else:
        result = await ha_get_state(entity_id)
        state = result.get("state")
        friendly_name = result.get("friendly_name") or entity_id
        remember_session_entity(session_id, entity_id, friendly_name, state)
        reply = f"{friendly_name} is {state}."
        tool_name = "get_home_assistant_state"

    return {
        "reply": reply,
        "tool_calls": [{
            "tool": tool_name,
            "arguments": {"entity_id": entity_id},
            "success": True,
            "route": "local",
            "source": intent["source"],
        }],
    }


def runtime_tool_round_limit(session_id: str) -> int:
    """Bound tool loops while giving approved multi-note tasks enough capacity."""
    if developer_mode_enabled():
        return 12
    if workshop_memory_task_approval_active(session_id):
        return 24
    return 12

async def run_jarvis(message: str, session_id: str = "default") -> dict[str, Any]:
    if not developer_mode_enabled():
        await refresh_workshop_memory_tools()
    pending_workshop = PENDING_WORKSHOP_APPROVALS.get(session_id)
    workshop_decision = workshop_memory_approval_decision(message)
    if pending_workshop and workshop_decision is not None:
        PENDING_WORKSHOP_APPROVALS.pop(session_id, None)
        if workshop_decision == "task" and not pending_has_gmail_write(pending_workshop):
            grant_workshop_memory_task_approval(session_id)
        elif workshop_decision == "deny":
            WORKSHOP_TASK_APPROVAL_GRANTS.pop(session_id, None)
        result = await continue_workshop_memory_approval(
            pending_workshop,
            workshop_decision in {"once", "task"},
            session_id,
            message,
        )
        append_chat_message(session_id, "user", message)
        append_chat_message(session_id, "assistant", result["reply"])
        return result
    local_result = (
        await try_local_ha_route(message, session_id)
        if is_home_assistant_priority_intent(message) or not developer_mode_enabled()
        else None
    )
    if local_result:
        append_chat_message(session_id, "user", message)
        append_chat_message(session_id, "assistant", local_result["reply"])
        return local_result

    response = await create_openai_response(
        {
            "model": active_agent_model(),
            **agent_reasoning_payload(),
            "instructions": priority_system_instructions(effective_system_instructions(), message),
            "input": (
                model_chat_history(session_id)
                + fast_memory_input(message, session_id)
                + automation_memory_input(message)
                + (
                    [{
                        "role": "developer",
                        "content": (
                            "The current conversational device reference is "
                            + json.dumps(get_session_entity(session_id), ensure_ascii=False)
                            + ". Resolve 'it' and 'that device' to this exact entity."
                        ),
                    }]
                    if get_session_entity(session_id)
                    else []
                )
                + [{"role": "user", "content": message}]
            ),
            "tools": runtime_chat_tools(message=message),
            "tool_choice": "auto",
        }
    )

    audit: list[dict[str, Any]] = []
    max_tool_rounds = runtime_tool_round_limit(session_id)

    for _round in range(max_tool_rounds + 1):
        calls = function_calls(response)

        if not calls:
            text = response_text(response)
            if not text:
                raise OpenAIError("The model returned no text or function call")
            append_chat_message(session_id, "user", message)
            append_chat_message(session_id, "assistant", text)
            return {"reply": text, "tool_calls": audit}

        if _round >= max_tool_rounds:
            raise OpenAIError(
                f"Tool-call limit exceeded after {max_tool_rounds} rounds"
            )

        write_calls = workshop_memory_write_calls(calls)
        if write_calls and (gmail_direct_write_calls(calls) or not workshop_memory_task_approval_active(session_id)):
            prompt = store_workshop_memory_approval(session_id, response["id"], calls)
            append_chat_message(session_id, "user", message)
            append_chat_message(session_id, "assistant", prompt)
            return {"reply": prompt, "tool_calls": audit}

        tool_outputs = await execute_tool_calls(
            calls,
            audit,
            session_id,
            approved_workshop_call_ids=(
                workshop_write_call_ids(calls) if write_calls else set()
            ),
        )

        response = await create_openai_response(
            {
                "model": active_agent_model(),
            **agent_reasoning_payload(),
                "instructions": priority_system_instructions(effective_system_instructions(), message),
                "previous_response_id": response["id"],
                "input": tool_outputs,
                "tools": runtime_chat_tools(message=message),
                "tool_choice": "auto",
            }
        )

    raise OpenAIError("ZBRANO tool loop ended unexpectedly")


def stream_event(event_type: str, **data: Any) -> bytes:
    payload = {"type": event_type, **data}
    return (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")


async def stream_openai_response(payload: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
    if not OPENAI_API_KEY:
        raise OpenAIError("OpenAI API key is not configured")

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    request_payload = {**payload, "stream": True}

    async with httpx.AsyncClient(timeout=httpx.Timeout(210.0, connect=10.0)) as client:
        async with client.stream(
            "POST",
            OPENAI_RESPONSES_URL,
            headers=headers,
            json=request_payload,
        ) as response:
            if response.is_error:
                body = await response.aread()
                raise OpenAIError(
                    f"OpenAI HTTP {response.status_code}: "
                    f"{body.decode('utf-8', errors='replace')[:1000]}"
                )

            data_lines: list[str] = []
            async for raw_line in response.aiter_lines():
                line = raw_line.rstrip("\r")

                if not line:
                    if data_lines:
                        payload_text = "\n".join(data_lines)
                        data_lines = []
                        if payload_text == "[DONE]":
                            continue
                        try:
                            yield json.loads(payload_text)
                        except json.JSONDecodeError as exc:
                            raise OpenAIError(
                                f"Invalid OpenAI stream event: {payload_text[:500]}"
                            ) from exc
                    continue

                if line.startswith("data:"):
                    data_lines.append(line[5:].lstrip())

            if data_lines:
                payload_text = "\n".join(data_lines)
                if payload_text != "[DONE]":
                    yield json.loads(payload_text)


async def stream_openai_response_with_progress(
    payload: dict[str, Any],
    *,
    hard_timeout: float,
) -> AsyncIterator[dict[str, Any]]:
    """Keep a silent Responses stream observable and enforce its caller deadline."""
    stream = stream_openai_response(payload).__aiter__()
    pending = asyncio.create_task(stream.__anext__())
    started = time.monotonic()
    continuation = bool(payload.get("previous_response_id"))
    if developer_mode_enabled():
        phases = (
            [
                "Reviewing the diagnostic evidence...",
                "Waiting for Developer repository tools...",
                "Checking the supported repair path...",
                "Developer analysis is still active...",
            ]
            if continuation
            else [
                "Planning the Developer investigation...",
                "Waiting for the first diagnostic step...",
                "Developer analysis is still active...",
            ]
        )
    else:
        phases = [
            "Waiting for the model response...",
            "The request is still active...",
        ]
    phase_index = 0
    try:
        while True:
            elapsed = time.monotonic() - started
            remaining = hard_timeout - elapsed
            if remaining <= 0:
                pending.cancel()
                with contextlib.suppress(asyncio.CancelledError, StopAsyncIteration):
                    await pending
                raise OpenAIError(
                    f"Developer model/tool continuation timed out after {int(hard_timeout)} seconds. "
                    "The request was stopped safely; no unapproved repository write was performed."
                )
            try:
                event = await asyncio.wait_for(
                    asyncio.shield(pending),
                    timeout=min(10.0, remaining),
                )
            except asyncio.TimeoutError:
                elapsed_seconds = int(time.monotonic() - started)
                phase = phases[min(phase_index, len(phases) - 1)]
                phase_index += 1
                yield {
                    "type": "zbrano.progress",
                    "message": f"{phase} · {elapsed_seconds}s",
                }
                continue
            except StopAsyncIteration:
                break
            yield event
            pending = asyncio.create_task(stream.__anext__())
    finally:
        if not pending.done():
            pending.cancel()
        with contextlib.suppress(asyncio.CancelledError, StopAsyncIteration):
            await pending
        with contextlib.suppress(Exception):
            await stream.aclose()


async def continue_workshop_memory_approval(
    pending: dict[str, Any],
    approved: bool,
    session_id: str,
    approval_message: str,
) -> dict[str, Any]:
    audit: list[dict[str, Any]] = []
    write_ids = {
        str(call.get("call_id") or "")
        for call in workshop_memory_write_calls(pending["calls"])
    }
    tool_outputs = await execute_tool_calls(
        pending["calls"],
        audit,
        session_id,
        approved_workshop_call_ids=write_ids if approved else set(),
        denied_workshop_call_ids=set() if approved else write_ids,
    )
    response = await create_workshop_continuation_response({
        "model": active_agent_model(),
        **agent_reasoning_payload(),
        "instructions": priority_system_instructions(effective_system_instructions(), approval_message),
        "previous_response_id": pending["response_id"],
        "input": tool_outputs,
        "tools": runtime_chat_tools(message=approval_message),
        "tool_choice": "auto",
    })
    for _round in range(6):
        native_approvals = mcp_approval_requests(response)
        if native_approvals:
            PENDING_MCP_APPROVALS[session_id] = {
                "response_id": response["id"],
                "requests": native_approvals,
            }
            return {"reply": mcp_approval_prompt(native_approvals), "tool_calls": audit}
        calls = function_calls(response)
        if not calls:
            reply = response_text(response)
            if not reply:
                reply = "Workshop Memory change completed." if approved else "Workshop Memory change was denied."
            return {"reply": reply, "tool_calls": audit}
        write_calls = workshop_memory_write_calls(calls)
        if write_calls and (gmail_direct_write_calls(calls) or not workshop_memory_task_approval_active(session_id)):
            prompt = store_workshop_memory_approval(session_id, response["id"], calls)
            return {"reply": prompt, "tool_calls": audit}
        tool_outputs = await execute_tool_calls(
            calls,
            audit,
            session_id,
            approved_workshop_call_ids=(
                workshop_write_call_ids(calls) if write_calls else set()
            ),
        )
        response = await create_workshop_continuation_response({
            "model": active_agent_model(),
            **agent_reasoning_payload(),
            "instructions": priority_system_instructions(effective_system_instructions(), approval_message),
            "previous_response_id": response["id"],
            "input": tool_outputs,
            "tools": runtime_chat_tools(message=approval_message),
            "tool_choice": "auto",
        })
    raise OpenAIError("Workshop Memory approval continuation exceeded 6 tool rounds")


async def _run_jarvis_stream_events(message: str, session_id: str = "default", search_mode: str = "auto") -> AsyncIterator[bytes]:
    yield stream_event("status", message="Searching the web..." if search_mode == "search" and not developer_mode_enabled() else "Thinking…")

    if not developer_mode_enabled():
        await refresh_workshop_memory_tools()
    pending_workshop = PENDING_WORKSHOP_APPROVALS.get(session_id)
    workshop_decision = workshop_memory_approval_decision(message)
    if pending_workshop and workshop_decision is not None:
        PENDING_WORKSHOP_APPROVALS.pop(session_id, None)
        if workshop_decision == "task" and not pending_has_gmail_write(pending_workshop):
            grant_workshop_memory_task_approval(session_id)
        elif workshop_decision == "deny":
            WORKSHOP_TASK_APPROVAL_GRANTS.pop(session_id, None)
        approved = workshop_decision in {"once", "task"}
        yield stream_event(
            "status",
            message="Executing approved Workshop Memory change…" if approved else "Denying Workshop Memory change…",
        )
        result = await continue_workshop_memory_approval(
            pending_workshop,
            approved,
            session_id,
            message,
        )
        yield stream_event("status", message="Responding…")
        yield stream_event("delta", text=result["reply"])
        yield stream_event("done", tool_calls=result["tool_calls"])
        return

    pending_approval = PENDING_MCP_APPROVALS.get(session_id)
    approval_decision = mcp_approval_decision(message)
    if pending_approval and approval_decision is not None:
        PENDING_MCP_APPROVALS.pop(session_id, None)
        requests = pending_approval["requests"]
        approval_provider = mcp_approval_provider(requests[0]) if requests else "Plugin"
        if approval_decision is False:
            yield stream_event("status", message=f"{approval_provider} action cancelled.")
            for request in requests[:5]:
                yield stream_event(
                    "activity",
                    id=str(request.get("id") or "cancelled-plugin-action"),
                    label=mcp_approval_summary(request),
                    state="cancelled",
                    provider="plugin",
                    plugin_id=mcp_approval_plugin_id(request),
                )
            yield stream_event("delta", text=f"{approval_provider} action cancelled. No action was performed.")
            yield stream_event("done", tool_calls=[])
            return
        yield stream_event("status", message=f"Executing approved {approval_provider} action…")
        continued_response: dict[str, Any] | None = None
        emitted_continuation_text = False
        # Cancellation returned above, so this continuation is approval-only.
        # OpenAI rejects `reason` when approve is true.
        approval_input = [
            {
                "type": "mcp_approval_response",
                "approval_request_id": request["id"],
                "approve": True,
            }
            for request in pending_approval["requests"]
        ]
        async for event in stream_openai_response_with_progress(
            {
                "model": OPENAI_MODEL,
                "instructions": web_search_quality_instructions(priority_system_instructions(effective_system_instructions(), message), search_mode),
                "previous_response_id": pending_approval["response_id"],
                "input": approval_input,
                "tools": runtime_chat_tools(search_mode, message),
                "tool_choice": web_search_tool_choice(search_mode),
                **web_search_include_options(search_mode),
            },
            hard_timeout=180.0,
        ):
            event_type = event.get("type")
            if event_type == "zbrano.progress":
                yield stream_event("status", message=event.get("message") or "Approved Developer work is active...")
                continue
            activity = openai_tool_activity(event)
            if activity:
                yield stream_event("activity", **activity)
            remote_status = remote_mcp_progress(event)
            if remote_status:
                yield stream_event("status", message=remote_status)
            if event_type == "response.output_text.delta":
                if not emitted_continuation_text:
                    yield stream_event("status", message="Responding…")
                    emitted_continuation_text = True
                delta = event.get("delta", "")
                if delta:
                    yield stream_event("delta", text=delta)
            elif event_type == "response.completed":
                continued_response = event.get("response")
            elif event_type in {"response.failed", "error"}:
                raise OpenAIError(
                    event.get("message")
                    or event.get("error", {}).get("message")
                    or "OpenAI MCP approval continuation failed"
                )
        if continued_response is None:
            raise OpenAIError("OpenAI approval continuation ended without response.completed")
        followup_approvals = mcp_approval_requests(continued_response)
        if followup_approvals:
            PENDING_MCP_APPROVALS[session_id] = {
                "response_id": continued_response["id"],
                "requests": followup_approvals,
            }
            prompt = mcp_approval_prompt(followup_approvals)
            yield stream_event("status", message="Permission required…")
            yield stream_event("delta", text=prompt)
            yield stream_event("done", tool_calls=[])
            return
        if not emitted_continuation_text:
            final_text = response_text(continued_response)
            if final_text:
                yield stream_event("status", message="Responding…")
                yield stream_event("delta", text=final_text)
        yield stream_event("done", tool_calls=[])
        return

    local_result = (
        await try_local_ha_route(message, session_id)
        if is_home_assistant_priority_intent(message) or not developer_mode_enabled()
        else None
    )
    if local_result:
        yield stream_event("activity", id="local-home-assistant", label="Reading Home Assistant", state="completed", provider="home_assistant", plugin_id="")
        yield stream_event("status", message="Using Home Assistant…")
        reply = local_result["reply"]
        yield stream_event("status", message="Responding…")
        yield stream_event("delta", text=reply)
        yield stream_event("done", tool_calls=local_result["tool_calls"])
        return

    audit: list[dict[str, Any]] = []
    max_tool_rounds = runtime_tool_round_limit(session_id)
    response: dict[str, Any] | None = None
    emitted_initial_text = False
    request_deadline = time.monotonic() + (300.0 if developer_mode_enabled() else 180.0)

    async def bounded_model_stream(payload: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
        remaining = request_deadline - time.monotonic()
        if remaining <= 0:
            raise OpenAIError(
                "The self-repair request reached its 5-minute safety limit. "
                "It was stopped without an unapproved repository write."
            )
        async for stream_item in stream_openai_response_with_progress(
            payload,
            hard_timeout=min(180.0, remaining),
        ):
            yield stream_item

    async for event in bounded_model_stream(
        {
            "model": active_agent_model(),
            **agent_reasoning_payload(),
            "instructions": web_search_quality_instructions(priority_system_instructions(effective_system_instructions(), message), search_mode),
            "input": (
                model_chat_history(session_id)
                + fast_memory_input(message, session_id)
                + automation_memory_input(message)
                + (
                    [{
                        "role": "developer",
                        "content": (
                            "The current conversational device reference is "
                            + json.dumps(get_session_entity(session_id), ensure_ascii=False)
                            + ". Resolve 'it' and 'that device' to this exact entity."
                        ),
                    }]
                    if get_session_entity(session_id)
                    else []
                )
                + [{"role": "user", "content": message}]
            ),
            "tools": runtime_chat_tools(search_mode, message),
            "tool_choice": web_search_tool_choice(search_mode),
                **web_search_include_options(search_mode),
        }
    ):
        event_type = event.get("type")
        if event_type == "zbrano.progress":
            yield stream_event("status", message=event.get("message") or "Developer analysis is active...")
            continue
        activity = openai_tool_activity(event)
        if activity:
            yield stream_event("activity", **activity)
        remote_status = remote_mcp_progress(event)
        if remote_status:
            yield stream_event("status", message=remote_status)
        search_status = web_search_progress(event)
        if search_status:
            yield stream_event("status", message=search_status)
        if event_type == "response.output_text.delta":
            if not emitted_initial_text:
                yield stream_event("status", message="Responding…")
                emitted_initial_text = True
            delta = event.get("delta", "")
            if delta:
                yield stream_event("delta", text=delta)
        elif event_type == "response.completed":
            response = event.get("response")
        elif event_type in {"response.failed", "error"}:
            raise OpenAIError(
                event.get("message")
                or event.get("error", {}).get("message")
                or "OpenAI streaming response failed"
            )

    if response is None:
        raise OpenAIError("OpenAI stream ended without response.completed")

    approval_requests = mcp_approval_requests(response)
    if approval_requests:
        PENDING_MCP_APPROVALS[session_id] = {
            "response_id": response["id"],
            "requests": approval_requests,
        }
        prompt = mcp_approval_prompt(approval_requests)
        yield stream_event("status", message="Permission required…")
        yield stream_event("delta", text=prompt)
        yield stream_event("done", tool_calls=audit)
        return

    if emitted_initial_text and not function_calls(response):
        sources = response_web_sources(response)
        if sources:
            yield stream_event("sources", sources=sources)
        yield stream_event("done", tool_calls=audit)
        return

    for round_index in range(max_tool_rounds + 1):
        calls = function_calls(response)

        if not calls:
            # The first response already contains the final text. Emit it in
            # small chunks so the UI still updates progressively.
            text = response_text(response)
            if not text:
                raise OpenAIError("The model returned no text or function call")
            yield stream_event("status", message="Responding…")
            chunk_size = 24
            for index in range(0, len(text), chunk_size):
                yield stream_event("delta", text=text[index:index + chunk_size])
            sources = response_web_sources(response)
            if sources:
                yield stream_event("sources", sources=sources)
            yield stream_event("done", tool_calls=audit)
            return

        if round_index >= max_tool_rounds:
            raise OpenAIError(
                f"Tool-call limit exceeded after {max_tool_rounds} rounds"
            )

        tool_names_list = [call.get("name", "unknown") for call in calls]
        tool_names = ", ".join(tool_names_list)
        local_ha_tools = {
            "find_home_assistant_entities",
            "get_home_assistant_state",
            "turn_on_home_assistant_entity",
            "turn_off_home_assistant_entity",
            "get_home_assistant_history",
            "correlate_home_assistant_timeline",
            "search_home_assistant_logbook",
        }
        if all(name in local_ha_tools for name in tool_names_list):
            status_message = f"Using Home Assistant: {tool_names}…"
        elif "investigate_zbrano_feature" in tool_names_list:
            status_message = "Investigating the reported feature..."
        elif "inspect_zbrano_ui_with_playwright" in tool_names_list:
            status_message = "Inspecting the ZBRANO interface..."
        else:
            status_message = f"Working with: {tool_names}…"
        yield stream_event("status", message=status_message)
        write_calls = workshop_memory_write_calls(calls)
        activity_meta = local_tool_activity(tool_names_list, writing=bool(write_calls))
        activity_id = (
            "local-home-assistant"
            if activity_meta.get("provider") == "home_assistant"
            else f"function-round-{round_index}"
        )
        yield stream_event("activity", id=activity_id, state="started", **activity_meta)

        if write_calls and (gmail_direct_write_calls(calls) or not workshop_memory_task_approval_active(session_id)):
            yield stream_event("activity", id=activity_id, state="waiting_approval", **activity_meta)
            prompt = store_workshop_memory_approval(session_id, response["id"], calls)
            yield stream_event("status", message="Permission required…")
            yield stream_event("delta", text=prompt)
            yield stream_event("done", tool_calls=audit)
            return

        tool_task = asyncio.create_task(
            execute_tool_calls(
                calls,
                audit,
                session_id,
                approved_workshop_call_ids=(
                    workshop_write_call_ids(calls) if write_calls else set()
                ),
            )
        )
        progress_started = time.monotonic()
        progress_phases = _tool_progress_phases(tool_names_list)
        progress_index = 0
        hard_timeout = (
            40.0 if "investigate_zbrano_feature" in tool_names_list
            else 35.0 if "inspect_zbrano_ui_with_playwright" in tool_names_list
            else 90.0
        )
        while not tool_task.done():
            elapsed = time.monotonic() - progress_started
            remaining = hard_timeout - elapsed
            if remaining <= 0:
                tool_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await tool_task
                raise OpenAIError(
                    f"Tool work timed out after {int(hard_timeout)} seconds. "
                    "No repository changes were made; retry or inspect the runtime log."
                )
            try:
                await asyncio.wait_for(asyncio.shield(tool_task), timeout=min(8.0, remaining))
            except asyncio.TimeoutError:
                elapsed_seconds = int(time.monotonic() - progress_started)
                phase = progress_phases[min(progress_index, len(progress_phases) - 1)]
                yield stream_event("status", message=f"{phase} · {elapsed_seconds}s")
                progress_index += 1
        tool_outputs = await tool_task
        failed = any('"error"' in str(output.get("output") or "") for output in tool_outputs)
        yield stream_event("activity", id=activity_id, state="failed" if failed else "completed", **activity_meta)
        yield stream_event(
            "status",
            message=_tool_completion_status(tool_names_list, tool_outputs),
        )

        # Stream the next model response. If it requests more tools, collect
        # the completed response and continue the loop. If it produces text,
        # forward each output_text delta immediately.
        streamed_response: dict[str, Any] | None = None
        emitted_text = False

        async for event in bounded_model_stream(
            {
                "model": active_agent_model(),
            **agent_reasoning_payload(),
                "instructions": web_search_quality_instructions(priority_system_instructions(effective_system_instructions(), message), search_mode),
                "previous_response_id": response["id"],
                "input": tool_outputs,
                "tools": runtime_chat_tools(search_mode, message),
                "tool_choice": web_search_tool_choice(search_mode),
                **web_search_include_options(search_mode),
            }
        ):
            event_type = event.get("type")

            if event_type == "zbrano.progress":
                yield stream_event("status", message=event.get("message") or "Developer analysis is active...")
                continue
            activity = openai_tool_activity(event)
            if activity:
                yield stream_event("activity", **activity)
            remote_status = remote_mcp_progress(event)
            if remote_status:
                yield stream_event("status", message=remote_status)
            search_status = web_search_progress(event)
            if search_status:
                yield stream_event("status", message=search_status)

            if event_type == "response.output_text.delta":
                if not emitted_text:
                    yield stream_event("status", message="Responding…")
                    emitted_text = True
                delta = event.get("delta", "")
                if delta:
                    yield stream_event("delta", text=delta)

            elif event_type == "response.completed":
                streamed_response = event.get("response")

            elif event_type in {"response.failed", "error"}:
                raise OpenAIError(
                    event.get("message")
                    or event.get("error", {}).get("message")
                    or "OpenAI streaming response failed"
                )

        if streamed_response is None:
            raise OpenAIError("OpenAI stream ended without response.completed")

        approval_requests = mcp_approval_requests(streamed_response)
        if approval_requests:
            PENDING_MCP_APPROVALS[session_id] = {
                "response_id": streamed_response["id"],
                "requests": approval_requests,
            }
            prompt = mcp_approval_prompt(approval_requests)
            yield stream_event("status", message="Permission required…")
            yield stream_event("delta", text=prompt)
            yield stream_event("done", tool_calls=audit)
            return

        if emitted_text and not function_calls(streamed_response):
            sources = response_web_sources(streamed_response)
            if sources:
                yield stream_event("sources", sources=sources)
            yield stream_event("done", tool_calls=audit)
            return

        response = streamed_response

    raise OpenAIError("ZBRANO streaming tool loop ended unexpectedly")


async def run_jarvis_stream(message: str, session_id: str = "default", search_mode: str = "auto") -> AsyncIterator[bytes]:
    """Persist a completed streamed exchange while forwarding events unchanged."""
    reply_parts: list[str] = []
    completed = False
    async for event_bytes in _run_jarvis_stream_events(message, session_id, search_mode):
        try:
            event = json.loads(event_bytes.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            event = {}
        if event.get("type") == "delta" and event.get("text"):
            reply_parts.append(str(event["text"]))
        elif event.get("type") == "sources":
            reply_parts.append(web_sources_markdown(event.get("sources") or []))
        elif event.get("type") == "done":
            completed = True
        yield event_bytes
    if completed and reply_parts:
        append_chat_message(session_id, "user", message)
        append_chat_message(session_id, "assistant", "".join(reply_parts))


@app.websocket("/api/chat/ws")
async def chat_websocket(websocket: WebSocket) -> None:
    await websocket.accept()
    stream_task: asyncio.Task[None] | None = None
    control_task: asyncio.Task[dict[str, Any]] | None = None

    try:
        payload = await websocket.receive_json()
        request = ChatRequest.model_validate(payload)

        async def send_stream() -> None:
            effective_message=request.message+attachment_context(request.session_id,request.attachment_ids)
            async for event_bytes in run_jarvis_stream(effective_message, request.session_id, request.search_mode):
                event_text = event_bytes.decode("utf-8").strip()
                if event_text:
                    await websocket.send_text(event_text)

        stream_task = asyncio.create_task(send_stream(), name="jarvis-response-stream")
        control_task = asyncio.create_task(websocket.receive_json(), name="jarvis-stop-listener")
        done, _pending = await asyncio.wait(
            {stream_task, control_task},
            return_when=asyncio.FIRST_COMPLETED,
        )

        if control_task in done:
            control = control_task.result()
            if control.get("type") == "stop" and not stream_task.done():
                stream_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await stream_task
                await websocket.send_json({"type": "stopped"})
        elif stream_task in done:
            await stream_task

    except WebSocketDisconnect:
        return
    except Exception as exc:
        try:
            await websocket.send_json({"type": "error", "message": str(exc)})
        except Exception:
            pass
    finally:
        for task in (stream_task, control_task):
            if task is not None and not task.done():
                task.cancel()
        for task in (stream_task, control_task):
            if task is not None:
                with contextlib.suppress(asyncio.CancelledError, Exception):
                    await task
        try:
            await websocket.close()
        except Exception:
            pass


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    async def generate() -> AsyncIterator[bytes]:
        try:
            effective_message=request.message+attachment_context(request.session_id,request.attachment_ids)
            async for event in run_jarvis_stream(effective_message, request.session_id, request.search_mode):
                yield event
        except (OpenAIError, MCPError, httpx.HTTPError) as exc:
            yield stream_event("error", message=str(exc))

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/health")
async def health() -> dict[str, Any]:
    configured_speech_provider = SPEECH_PROVIDER if SPEECH_PROVIDER in {"openai", "elevenlabs"} else "openai"
    return {
        "status": "ok",
        "version": "0.13.45",
        "home_assistant_configured": bool(SUPERVISOR_TOKEN),
        "workshop_memory_configured": bool(WORKSHOP_MEMORY_URL),
        "openai_configured": bool(OPENAI_API_KEY),
        "openai_model": OPENAI_MODEL,
        "voice_configured": bool(OPENAI_API_KEY) or bool(ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID),
        "speech_provider": configured_speech_provider,
        "speech_providers": {
            "openai": {"configured": bool(OPENAI_API_KEY)},
            "elevenlabs": {
                "configured": bool(ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID),
                "voice_name": ELEVENLABS_VOICE_NAME,
            },
        },
        "transcription_model": OPENAI_TRANSCRIPTION_MODEL,
        "tts_model": OPENAI_TTS_MODEL,
        "elevenlabs_model": ELEVENLABS_MODEL_ID,
        "ha_read_entity_count": len((await approved_ha_entities())["read_entities"]),
        "ha_control_entity_count": len((await approved_ha_entities())["control_entities"]),
    }


@app.get("/api/connections/status")
async def connections_status() -> dict[str, Any]:
    ha_status = ha_ws.status()
    return {
        "home_assistant": {
            **ha_status,
            "websocket_url": HA_WS_URL,
            "rest_fallback_url": HA_API_BASE,
        },
        "workshop_memory": {
            **workshop_memory_runtime_status(),
            "release_sync": release_sync_status(),
        },
        "openai": {
            "configured": bool(OPENAI_API_KEY),
            "model": active_agent_model(),
            **agent_reasoning_payload(),
        },
    }


@app.get("/api/memory/status")
async def memory_status() -> dict[str, Any]:
    try:
        result = await call_workshop_memory_tool("check_server_status", {})
        return {"connected": True, "result": result}
    except (MCPError, httpx.HTTPError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/api/memory/project/{project_name}")
async def memory_project(project_name: str) -> dict[str, Any]:
    try:
        result = await call_workshop_memory_tool(
            "get_project_context",
            {"project": project_name, "include_requirements": True},
        )
        return {"connected": True, "project": project_name, "result": result}
    except (MCPError, httpx.HTTPError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


























@app.get("/api/release-memory-sync")
async def get_release_memory_sync() -> dict[str, Any]:
    return release_sync_status()


@app.post("/api/release-memory-sync/retry")
async def retry_release_memory_sync() -> dict[str, Any]:
    if not release_sync_enabled():
        raise HTTPException(status_code=409, detail="Automatic release synchronization is disabled in Settings")
    schedule_release_sync()
    return {**release_sync_status(), "scheduled": True}


@app.get("/api/grinder-monitor/status")
async def get_grinder_monitor_status() -> dict[str, Any]:
    return grinder_monitor_status()


@app.get("/api/grinder-monitor/incidents")
async def get_grinder_monitor_incidents(limit: int = 20) -> dict[str, Any]:
    return list_grinder_incidents(limit)


@app.get("/api/grinder-monitor/incidents/{incident_id}")
async def get_grinder_monitor_incident(incident_id: str) -> dict[str, Any]:
    result = get_grinder_incident(incident_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@app.on_event("startup")
async def start_ha_websocket() -> None:
    global PLUGIN_OAUTH_REFRESH_TASK, NOTIFICATION_WATCH_TASK, CALENDAR_REMINDER_TASK, GOOGLE_CALENDAR_SYNC_TASK
    load_chat_sessions()
    prune_expired_chats()
    await enforce_stored_gmail_scope_policy()
    await refresh_plugin_oauth_tokens()
    if PLUGIN_OAUTH_REFRESH_TASK is None or PLUGIN_OAUTH_REFRESH_TASK.done():
        PLUGIN_OAUTH_REFRESH_TASK = asyncio.create_task(
            _plugin_oauth_refresh_loop(), name="zbrano-plugin-oauth-refresh"
        )
    await get_mcp_client()
    with contextlib.suppress(MCPError, httpx.HTTPError, OSError, RuntimeError):
        await select_workshop_memory_endpoint(force=True)
    schedule_release_sync()
    if CALENDAR_REMINDER_TASK is None or CALENDAR_REMINDER_TASK.done():
        CALENDAR_REMINDER_TASK = asyncio.create_task(calendar_reminder_worker(), name="zbrano-calendar-reminders")
    if GOOGLE_CALENDAR_SYNC_TASK is None or GOOGLE_CALENDAR_SYNC_TASK.done():
        GOOGLE_CALENDAR_SYNC_TASK = asyncio.create_task(google_calendar_sync_worker(), name="zbrano-google-calendar-sync")
    start_grinder_monitor()

    if not SUPERVISOR_TOKEN:
        return
    try:
        await ha_ws.connect()
    except RuntimeError:
        # App remains available; the client reconnects lazily and REST is a fallback.
        pass

    # Apply the owner's socket/HVAC auto-approval policy without requiring the
    # Entities screen to be opened first.
    with contextlib.suppress(HTTPException, OSError, RuntimeError):
        await list_ha_entities()
    if NOTIFICATION_WATCH_TASK is None or NOTIFICATION_WATCH_TASK.done():
        NOTIFICATION_WATCH_TASK = asyncio.create_task(notification_watch_worker(), name="zbrano-notification-watchlist")


@app.on_event("shutdown")
async def stop_ha_websocket() -> None:
    global PLUGIN_OAUTH_REFRESH_TASK, NOTIFICATION_WATCH_TASK, CALENDAR_REMINDER_TASK, GOOGLE_CALENDAR_SYNC_TASK
    if GOOGLE_CALENDAR_SYNC_TASK is not None:
        GOOGLE_CALENDAR_SYNC_TASK.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await GOOGLE_CALENDAR_SYNC_TASK
        GOOGLE_CALENDAR_SYNC_TASK = None
    if CALENDAR_REMINDER_TASK is not None:
        CALENDAR_REMINDER_TASK.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await CALENDAR_REMINDER_TASK
        CALENDAR_REMINDER_TASK = None
    await stop_grinder_monitor()
    if NOTIFICATION_WATCH_TASK is not None:
        NOTIFICATION_WATCH_TASK.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await NOTIFICATION_WATCH_TASK
        NOTIFICATION_WATCH_TASK = None
    await stop_release_sync()
    if PLUGIN_OAUTH_REFRESH_TASK is not None:
        PLUGIN_OAUTH_REFRESH_TASK.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await PLUGIN_OAUTH_REFRESH_TASK
        PLUGIN_OAUTH_REFRESH_TASK = None
    await ha_ws.close()
    await close_mcp_client()


@app.get("/api/chats")
async def list_chats() -> dict[str, Any]:
    chats = [
        {
            "session_id": session_id,
            "title": CHAT_SESSION_META.get(session_id, {}).get("title") or chat_title(messages),
            "updated_at": CHAT_SESSION_META.get(session_id, {}).get("updated_at", 0),
            "message_count": len(messages),
        }
        for session_id, messages in CHAT_SESSIONS.items()
        if not is_internal_chat_session(session_id)
    ]
    chats.sort(key=lambda item: item["updated_at"], reverse=True)
    return {"chats": chats}


@app.put("/api/chats/{session_id}/title")
async def rename_chat(session_id: str, request: ChatRenameRequest) -> dict[str, Any]:
    if session_id not in CHAT_SESSIONS:
        raise HTTPException(status_code=404, detail="Chat not found")
    title = " ".join(request.title.strip().split())
    if not title:
        raise HTTPException(status_code=400, detail="Chat title cannot be empty")
    metadata = CHAT_SESSION_META.setdefault(session_id, {})
    metadata["title"] = title
    metadata["title_manual"] = True
    metadata["updated_at"] = time.time()
    persist_chat_sessions()
    return {"saved": True, "session_id": session_id, "title": title}


@app.get("/api/models")
async def list_openai_models() -> dict[str, Any]:
    preferences = load_preferences()
    selected_model = str(preferences.get("agent_model") or OPENAI_MODEL)
    models = {"gpt-5.5", "gpt-5-mini", selected_model, OPENAI_MODEL}
    if OPENAI_API_KEY:
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get("https://api.openai.com/v1/models", headers=headers)
            if not response.is_error:
                for item in response.json().get("data", []):
                    model_id = str(item.get("id") or "")
                    if model_id.startswith("gpt-"):
                        models.add(model_id)
        except (httpx.HTTPError, ValueError, TypeError):
            pass
    return {"models": sorted(models), "selected_model": selected_model, "reasoning_effort": preferences.get("reasoning_effort", "medium")}


@app.put("/api/agent/settings")
async def update_agent_settings(request: AgentSettingsUpdate) -> dict[str, Any]:
    preferences = load_preferences()
    preferences.update({"agent_model": request.agent_model.strip(), "reasoning_effort": request.reasoning_effort})
    return {"saved": True, "preferences": save_preferences(preferences)}


PLUGIN_TIMEOUT=httpx.Timeout(15.0,connect=4.0)



def active_mcp_tools():
    active = []
    secrets = plugin_secrets()
    registry = plugin_registry()
    if _apply_github_tool_policy(registry):
        _plugin_save(PLUGIN_REGISTRY_PATH, registry)
    for pid, plugin in registry.items():
        if pid == _gmail_plugin_id():
            # Gmail Direct tools execute locally against the standard Gmail REST API.
            # Never expose the Developer Preview remote MCP for this connection.
            continue
        enabled_tools = [
            tool for tool in plugin.get("tools", [])
            if tool.get("enabled") and tool.get("permission") in {"read_only", "write"}
        ]
        if not plugin.get("enabled") or not enabled_tools:
            continue
        read_tools = [tool.get("name") for tool in enabled_tools if tool.get("permission") == "read_only"]
        approval_tools = [tool.get("name") for tool in enabled_tools if tool.get("permission") == "write"]
        allowed = [tool.get("name") for tool in enabled_tools if tool.get("name")]
        item = {
            "type": "mcp",
            "server_label": f"plugin_{pid}"[:64],
            "server_url": plugin["url"],
            "server_description": str(plugin.get("name") or pid)[:200],
            "allowed_tools": allowed,
        }
        if approval_tools and read_tools:
            item["require_approval"] = {
                "always": {"tool_names": approval_tools},
                "never": {"tool_names": read_tools},
            }
        elif approval_tools:
            item["require_approval"] = "always"
        else:
            item["require_approval"] = "never"
        if secrets.get(pid):
            item["authorization"] = secrets[pid]
        active.append(item)
    return active


@app.get("/api/plugin-catalog")
async def plugin_catalog(q: str = "", category: str = "", refresh: bool = False):
    return await plugin_catalog_payload(q, category, refresh)


@app.post("/api/plugin-catalog/{catalog_id}/install")
async def install_catalog_plugin(catalog_id: str, request: CatalogInstallRequest):
    plugins, _, _ = _verify_catalog_result_contract(
        await _fetch_plugin_catalog(force=False)
    )
    entry = next((plugin for plugin in plugins if plugin.get("id") == catalog_id), None)
    if not entry:
        raise HTTPException(status_code=404, detail="Catalog plugin not found")
    if entry.get("installable") is False:
        raise HTTPException(status_code=409, detail=entry.get("setup_label") or "This connector requires an OAuth setup workflow")
    install = PluginInstallRequest(
        name=str(entry.get("title") or entry.get("name") or "MCP Plugin"),
        url=str(entry.get("url") or ""),
        bearer_token=request.bearer_token,
    )
    return await install_plugin(install)


PLUGIN_OAUTH_REFRESH_TASK = None

async def _oauth_start_for_target(name, resource_url, redirect_uri, catalog_id="", plugin_id=""):
    import secrets
    from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl

    redirect_uri = _oauth_validate_redirect_uri(redirect_uri)
    if len(PLUGIN_OAUTH_FLOWS) >= 20:
        expired = [key for key, flow in PLUGIN_OAUTH_FLOWS.items() if flow.get("expires_at", 0) <= time.time()]
        for key in expired:
            PLUGIN_OAUTH_FLOWS.pop(key, None)
    if len(PLUGIN_OAUTH_FLOWS) >= 20:
        raise ValueError("Too many OAuth authorizations are already pending")

    google_service = (
        "gmail" if str(catalog_id) == "gmail-official" or str(plugin_id) == _gmail_plugin_id()
        else "calendar" if str(catalog_id) == "google-calendar-official" or str(plugin_id) == _google_calendar_plugin_id()
        else ""
    )
    google_connector = bool(google_service)
    if google_connector:
        resource_url = GMAIL_MCP_RESOURCE_URL if google_service == "gmail" else GOOGLE_CALENDAR_RESOURCE_URL
        resource_metadata = {"resource": ""}
        auth_metadata = {
            "authorization_endpoint": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_endpoint": "https://oauth2.googleapis.com/token",
            "revocation_endpoint": "https://oauth2.googleapis.com/revoke",
            "issuer": "https://accounts.google.com",
        }
    else:
        resource_url, resource_metadata, auth_metadata = await _oauth_discover(resource_url)
    if google_connector:
        google_client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "").strip()
        google_client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "").strip()
        if not google_client_id or not google_client_secret:
            raise ValueError("Configure Google OAuth client ID and secret in the ZBRANO add-on settings first")
        client_data = {
            "client_id": google_client_id,
            "client_secret": google_client_secret,
            "token_endpoint_auth_method": "client_secret_post",
        }
    else:
        client_data = await _oauth_register_client(auth_metadata, redirect_uri)
    verifier, challenge = _oauth_pkce()
    state = secrets.token_urlsafe(32)
    flow = {
        "name": str(name or "MCP Plugin")[:80], "resource_url": resource_url,
        "resource": "" if google_connector else str(resource_metadata.get("resource") or resource_url),
        "redirect_uri": redirect_uri, "catalog_id": str(catalog_id), "plugin_id": str(plugin_id),
        "state": state, "code_verifier": verifier, "expires_at": time.time() + 600,
        "authorization_endpoint": auth_metadata["authorization_endpoint"],
        "issuer": str(auth_metadata["issuer"]),
        "google_connector": google_connector,
        "google_service": google_service,
        "scope": (
            " ".join(GMAIL_MCP_OAUTH_SCOPES if google_service == "gmail" else GOOGLE_CALENDAR_OAUTH_SCOPES)
            if google_connector else
            " ".join(
                str(scope).strip() for scope in (
                    resource_metadata.get("scopes_supported")
                    or auth_metadata.get("scopes_supported") or []
                ) if str(scope).strip()
            )[:2000]
        ),
        "token_endpoint": auth_metadata["token_endpoint"],
        "revocation_endpoint": str(auth_metadata.get("revocation_endpoint") or ""),
        **client_data,
    }
    PLUGIN_OAUTH_FLOWS[state] = flow
    parts = urlsplit(flow["authorization_endpoint"])
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.update({
        "response_type": "code", "client_id": flow["client_id"],
        "redirect_uri": redirect_uri, "state": state,
        "code_challenge": challenge, "code_challenge_method": "S256",
    })
    if flow.get("resource"):
        query["resource"] = flow["resource"]
    if flow.get("scope"):
        query["scope"] = flow["scope"]
    if flow.get("google_connector"):
        query.update({"access_type": "offline", "prompt": "select_account consent"})
    authorization_url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
    return {"authorization_url": authorization_url, "expires_in": 600}


@app.post("/api/plugin-catalog/{catalog_id}/oauth/start")
async def plugin_catalog_oauth_start(catalog_id: str, request: PluginOAuthStartRequest):
    entry = await _catalog_entry(catalog_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Catalog plugin not found")
    if not entry.get("oauth_connectable"):
        raise HTTPException(status_code=409, detail="This plugin requires manual OAuth client configuration")
    try:
        return await _oauth_start_for_target(
            entry.get("title") or entry.get("name"), entry.get("url"),
            request.redirect_uri, catalog_id=catalog_id,
        )
    except (ValueError, httpx.HTTPError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/plugins/{plugin_id}/oauth/start")
async def installed_plugin_oauth_start(plugin_id: str, request: PluginOAuthStartRequest):
    plugin = plugin_registry().get(plugin_id)
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")
    if plugin.get("auth_mode") != "oauth":
        raise HTTPException(status_code=409, detail="Plugin does not use OAuth")
    try:
        return await _oauth_start_for_target(
            plugin.get("name"), plugin.get("url"), request.redirect_uri,
            catalog_id=str(plugin.get("catalog_id") or ""), plugin_id=plugin_id,
        )
    except (ValueError, httpx.HTTPError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/plugin-oauth/callback")
async def plugin_oauth_callback(
    state: str = "", code: str = "", iss: str = "",
    error: str = "", error_description: str = "",
):
    flow = PLUGIN_OAUTH_FLOWS.pop(state, None)
    if not flow:
        return _oauth_popup_response(False, "OAuth state is missing, expired, or already used")
    if flow.get("expires_at", 0) <= time.time():
        return _oauth_popup_response(False, "OAuth authorization expired")
    if iss and iss.rstrip("/") != str(flow.get("issuer") or "").rstrip("/"):
        return _oauth_popup_response(False, "OAuth authorization-server issuer mismatch")
    if error:
        return _oauth_popup_response(False, error_description or error)
    if not code:
        return _oauth_popup_response(False, "OAuth provider returned no authorization code")
    try:
        token = await _oauth_exchange_token(flow, {
            "grant_type": "authorization_code", "code": code,
            "redirect_uri": flow["redirect_uri"], "code_verifier": flow["code_verifier"],
            "resource": flow["resource"],
        })
        oauth_account = await _validate_gmail_oauth_grant(flow, token)
        if flow.get("google_service") == "calendar":
            oauth_account = await _validate_google_calendar_oauth_grant(flow, token)
        access_token = str(token["access_token"])
        if flow.get("google_service") == "gmail":
            tools = gmail_direct_tool_records()
            plugin_id = _gmail_plugin_id()
        elif flow.get("google_service") == "calendar":
            tools = []
            plugin_id = _google_calendar_plugin_id()
        else:
            tools = await discover_plugin_tools(flow["resource_url"], access_token)
            for tool in tools:
                if tool.get("permission") == "blocked":
                    tool["permission"] = "write"
                tool["enabled"] = tool.get("permission") in {"read_only", "write"}
            import hashlib
            plugin_id = hashlib.sha256(flow["resource_url"].encode()).hexdigest()[:16]
        registry = plugin_registry()
        if plugin_id not in registry and len(registry) >= 20:
            raise ValueError("Plugin limit reached (20)")
        registry[plugin_id] = {
            "name": (
                "Gmail Direct" if flow.get("google_service") == "gmail"
                else "Google Calendar Direct" if flow.get("google_service") == "calendar"
                else flow["name"]
            ),
            "url": (
                "https://gmail.googleapis.com/gmail/v1" if flow.get("google_service") == "gmail"
                else GOOGLE_CALENDAR_API_BASE if flow.get("google_service") == "calendar"
                else flow["resource_url"]
            ),
            "catalog_id": (
                "gmail-official" if flow.get("google_service") == "gmail"
                else "google-calendar-official" if flow.get("google_service") == "calendar"
                else str(flow.get("catalog_id") or "")
            ),
            "enabled": True, "healthy": True, "last_error": None, "last_checked": time.time(),
            "tools": tools, "auth_mode": "oauth",
            "oauth_provider": str(flow.get("authorization_endpoint") or "").split("/")[2],
            "oauth_connected_at": time.time(),
            "oauth_account": oauth_account,
        }
        _plugin_save(PLUGIN_REGISTRY_PATH, registry)
        secrets_store = plugin_secrets()
        secrets_store[plugin_id] = access_token
        _plugin_save(PLUGIN_SECRETS_PATH, secrets_store)
        oauth_records = plugin_oauth_records()
        expires_in = max(0, int(token.get("expires_in") or 0))
        oauth_records[plugin_id] = {
            "resource": flow["resource"], "token_endpoint": flow["token_endpoint"],
            "revocation_endpoint": flow.get("revocation_endpoint") or "",
            "client_id": flow["client_id"], "client_secret": flow.get("client_secret") or "",
            "token_endpoint_auth_method": flow.get("token_endpoint_auth_method") or "none",
            "refresh_token": str(token.get("refresh_token") or ""),
            "scope": str(token.get("scope") or ""),
            "expires_at": time.time() + expires_in if expires_in else 0,
        }
        _plugin_save(PLUGIN_OAUTH_PATH, oauth_records)
        return _oauth_popup_response(True, "Plugin authorized and connected", plugin_id)
    except (ValueError, httpx.HTTPError) as exc:
        return _oauth_popup_response(False, str(exc))


async def _refresh_plugin_oauth_token(plugin_id, force=False):
    records = plugin_oauth_records()
    record = records.get(plugin_id)
    if not isinstance(record, dict) or not record.get("refresh_token"):
        return False
    expires_at = float(record.get("expires_at") or 0)
    if not force and (not expires_at or expires_at > time.time() + 300):
        return False
    token = await _oauth_exchange_token(record, {
        "grant_type": "refresh_token", "refresh_token": record["refresh_token"],
        "resource": record.get("resource") or "",
    })
    secrets_store = plugin_secrets()
    secrets_store[plugin_id] = str(token["access_token"])
    _plugin_save(PLUGIN_SECRETS_PATH, secrets_store)
    if token.get("refresh_token"):
        record["refresh_token"] = str(token["refresh_token"])
    expires_in = max(0, int(token.get("expires_in") or 0))
    record["expires_at"] = time.time() + expires_in if expires_in else 0
    record["scope"] = str(token.get("scope") or record.get("scope") or "")
    records[plugin_id] = record
    _plugin_save(PLUGIN_OAUTH_PATH, records)
    return True


async def refresh_plugin_oauth_tokens():
    for plugin_id in list(plugin_oauth_records()):
        with contextlib.suppress(ValueError, httpx.HTTPError, OSError):
            await _refresh_plugin_oauth_token(plugin_id)


async def _plugin_oauth_refresh_loop():
    while True:
        await asyncio.sleep(60)
        await refresh_plugin_oauth_tokens()


@app.post("/api/plugins/{plugin_id}/oauth/disconnect")
async def disconnect_plugin_oauth(plugin_id: str):
    registry = plugin_registry()
    plugin = registry.get(plugin_id)
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")
    record = plugin_oauth_records().get(plugin_id) or {}
    access_token = str(plugin_secrets().get(plugin_id) or "")
    revocation_endpoint = str(record.get("revocation_endpoint") or "")
    if revocation_endpoint and access_token:
        with contextlib.suppress(ValueError, httpx.HTTPError):
            endpoint = _oauth_validate_https_url(revocation_endpoint, "OAuth revocation endpoint")
            data = {"token": access_token, "token_type_hint": "access_token"}
            auth = _oauth_token_request_auth(data, record)
            async with httpx.AsyncClient(timeout=PLUGIN_TIMEOUT, follow_redirects=False) as client:
                await client.post(endpoint, data=data, auth=auth)
    secrets_store = plugin_secrets()
    secrets_store.pop(plugin_id, None)
    _plugin_save(PLUGIN_SECRETS_PATH, secrets_store)
    records = plugin_oauth_records()
    records.pop(plugin_id, None)
    _plugin_save(PLUGIN_OAUTH_PATH, records)
    plugin.update({
        "enabled": False, "healthy": False, "last_error": "OAuth disconnected",
        "last_checked": time.time(), "auth_mode": "oauth",
    })
    registry[plugin_id] = plugin
    _plugin_save(PLUGIN_REGISTRY_PATH, registry)
    return {"disconnected": True, "plugin": plugin_public(plugin_id, plugin)}


@app.post("/api/plugin-catalog/{catalog_id}/github-device/start")
async def github_device_start(catalog_id: str):
    try:
        return await start_github_device_flow(catalog_id)
    except GitHubDeviceFlowError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@app.post("/api/plugin-catalog/github-device/{flow_id}/complete")
async def github_device_complete(flow_id: str):
    try:
        return await complete_github_device_flow(flow_id)
    except GitHubDeviceFlowError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

@app.get("/api/plugins")
async def list_plugins():
    registry = plugin_registry()
    if _apply_github_tool_policy(registry):
        _plugin_save(PLUGIN_REGISTRY_PATH, registry)
    installed = [plugin_public(pid, plugin) for pid, plugin in registry.items()]
    return {"plugins": [await playwright_builtin_plugin(), *installed]}


@app.post("/api/plugins")
async def install_plugin(request:PluginInstallRequest):
    import hashlib
    registry=plugin_registry()
    if len(registry)>=20: raise HTTPException(status_code=400,detail="Plugin limit reached (20)")
    try: url=validate_plugin_url(request.url);tools=await discover_plugin_tools(url,request.bearer_token)
    except ValueError as exc: raise HTTPException(status_code=400,detail=str(exc)) from exc
    pid=hashlib.sha256(url.encode()).hexdigest()[:16];registry[pid]={"name":" ".join(request.name.strip().split()),"url":url,"enabled":False,"healthy":True,"last_error":None,"last_checked":time.time(),"tools":tools};_plugin_save(PLUGIN_REGISTRY_PATH,registry)
    secrets=plugin_secrets()
    if request.bearer_token: secrets[pid]=request.bearer_token
    else: secrets.pop(pid,None)
    _plugin_save(PLUGIN_SECRETS_PATH,secrets)
    return {"installed":True,"plugin":plugin_public(pid,registry[pid])}

@app.post("/api/plugins/{plugin_id}/toggle")
async def toggle_plugin(plugin_id:str):
    registry=plugin_registry();p=registry.get(plugin_id)
    if not p: raise HTTPException(status_code=404,detail="Plugin not found")
    if not p.get("healthy") and not p.get("enabled"): raise HTTPException(status_code=400,detail="Refresh and validate before enabling")
    p["enabled"]=not bool(p.get("enabled"));_plugin_save(PLUGIN_REGISTRY_PATH,registry);return {"saved":True,"plugin":plugin_public(plugin_id,p)}

@app.post("/api/plugins/{plugin_id}/refresh")
async def refresh_plugin(plugin_id:str):
    registry=plugin_registry();p=registry.get(plugin_id)
    if not p: raise HTTPException(status_code=404,detail="Plugin not found")
    old={t.get("name"):t for t in p.get("tools",[])}
    try:
        tools=await discover_plugin_tools(p["url"],str(plugin_secrets().get(plugin_id) or ""))
        for t in tools:
            previous = old.get(t["name"], {})
            if _is_github_plugin(str(p.get("url") or ""), str(p.get("name") or "")):
                t["enabled"] = t.get("permission") in {"read_only", "write"}
            elif previous.get("permission") == "read_only":
                t["permission"] = "read_only"
                t["enabled"] = bool(previous.get("enabled"))
        p.update({"tools":tools,"healthy":True,"last_error":None,"last_checked":time.time()})
    except ValueError as exc: p.update({"healthy":False,"enabled":False,"last_error":str(exc),"last_checked":time.time()})
    _plugin_save(PLUGIN_REGISTRY_PATH,registry);return {"plugin":plugin_public(plugin_id,p)}

@app.put("/api/plugins/{plugin_id}/tools/{tool_name}")
async def update_plugin_tool(plugin_id:str,tool_name:str,request:PluginToolUpdate):
    registry=plugin_registry();p=registry.get(plugin_id)
    if not p: raise HTTPException(status_code=404,detail="Plugin not found")
    tool=next((t for t in p.get("tools",[]) if t.get("name")==tool_name),None)
    if not tool: raise HTTPException(status_code=404,detail="Tool not found")
    declared = str(tool.get("permission") or "blocked")
    if declared not in {"read_only", "write"}:
        raise HTTPException(status_code=400, detail="Blocked tools cannot be enabled")
    if request.permission != declared:
        raise HTTPException(status_code=400, detail="Tool permission classification cannot be changed from the UI")
    tool["enabled"]=bool(request.enabled);_plugin_save(PLUGIN_REGISTRY_PATH,registry);return {"saved":True,"tool":tool}

@app.delete("/api/plugins/{plugin_id}")
async def remove_plugin(plugin_id:str):
    registry=plugin_registry()
    if plugin_id not in registry: raise HTTPException(status_code=404,detail="Plugin not found")
    registry.pop(plugin_id);_plugin_save(PLUGIN_REGISTRY_PATH,registry)
    secrets=plugin_secrets();secrets.pop(plugin_id,None);_plugin_save(PLUGIN_SECRETS_PATH,secrets)
    oauth_records=plugin_oauth_records();oauth_records.pop(plugin_id,None);_plugin_save(PLUGIN_OAUTH_PATH,oauth_records)
    return {"removed":True}


@app.get("/api/automations")
async def read_autonomous_automations():
    with contextlib.suppress(RuntimeError, OSError, asyncio.TimeoutError):
        await _automation_refresh_area_context()
    data = automation_store()
    return {
        **data,
        "engine": {
            "status": "active" if ha_ws.connected else "waiting_for_home_assistant",
            "continuous_monitoring": True,
            "context_reasoning": True,
            "passive_learning": bool(data["settings"].get("passive_learning_enabled", True)),
            "known_areas": len((data.get("area_context") or {}).get("areas", [])),
            "known_labels": len((data.get("area_context") or {}).get("labels", [])),
            "known_zones": len((data.get("area_context") or {}).get("zones", [])),
            "observation_count": len(data.get("observations") or []),
            "learned_pattern_count": len(data.get("patterns") or []),
            "automatic_execution": data["settings"].get("operating_mode") == "selective_autonomy",
            "live_event_count": len(HA_LIVE_EVENTS),
            "pending_evaluations": sum(not task.done() for task in AUTOMATION_PENDING_TASKS.values()),
            "message": "Event-driven evaluator active; no AI model is called while idle.",
        },
    }


@app.put("/api/automations/settings")
async def update_autonomy_settings(request: AutonomySettingsRequest):
    data = automation_store()
    settings = request.model_dump()
    settings["presence_entity"] = settings["presence_entity"].strip()
    data["settings"] = settings
    _automation_event(
        data, "policy", "Autonomy policy updated",
        f"Mode: {settings['operating_mode']}; event-driven evaluator active.",
    )
    _automation_save(data)
    return {"saved": True, "settings": settings}


@app.post("/api/automations")
async def create_autonomous_automation(request: AutonomousAutomationRequest):
    import secrets

    data = automation_store()
    if len(data["automations"]) >= 100:
        raise HTTPException(status_code=400, detail="Automation draft limit reached (100)")
    now = time.time()
    automation = {
        "id": secrets.token_hex(12), "status": "armed" if request.enabled else "draft",
        "created_at": now, "updated_at": now,
        **_automation_payload_http(request),
    }
    data["automations"].insert(0, automation)
    _automation_event(data, "draft", f"Draft created: {automation['name']}", automation["objective"])
    _automation_save(data)
    return {"created": True, "automation": automation}


@app.post("/api/automations/{automation_id}/activate")
async def activate_autonomous_automation(automation_id: str) -> dict[str, Any]:
    return _activate_automation(automation_id, "interface_confirmation")


@app.delete("/api/automations/entity-memory/{memory_id}")
async def delete_automation_entity_memory(memory_id: str) -> dict[str, Any]:
    data = automation_store()
    original = list(data.get("entity_memory") or [])
    data["entity_memory"] = [item for item in original if str(item.get("id") or "") != memory_id]
    if len(data["entity_memory"]) == len(original):
        raise HTTPException(status_code=404, detail="Automation entity mapping not found")
    _automation_event(data, "memory", "Automation entity mapping forgotten", memory_id)
    _automation_save(data)
    return {"deleted": True, "remaining": len(data["entity_memory"])}


@app.put("/api/automations/{automation_id}")
async def update_autonomous_automation(automation_id: str, request: AutonomousAutomationRequest):
    data = automation_store()
    automation = next((item for item in data["automations"] if item.get("id") == automation_id), None)
    if not automation:
        raise HTTPException(status_code=404, detail="Automation draft not found")
    automation.update(_automation_payload_http(request))
    automation["updated_at"] = time.time()
    automation["status"] = "armed" if automation.get("enabled") else "draft"
    if automation.get("enabled"):
        automation["review_required"] = False
        automation["reviewed_at"] = time.time()
    _automation_event(data, "configuration", f"Automation updated: {automation['name']}", automation["status"])
    _automation_save(data)
    return {"saved": True, "automation": automation}


@app.delete("/api/automations/{automation_id}")
async def delete_autonomous_automation(automation_id: str):
    data = automation_store()
    automation = next((item for item in data["automations"] if item.get("id") == automation_id), None)
    if not automation:
        raise HTTPException(status_code=404, detail="Automation draft not found")
    data["automations"] = [item for item in data["automations"] if item.get("id") != automation_id]
    _automation_event(data, "draft", f"Draft deleted: {automation.get('name') or automation_id}")
    _automation_save(data)
    return {"removed": True}


@app.post("/api/automations/suggestions/{suggestion_id}/approve")
async def approve_automation_suggestion(suggestion_id: str) -> dict[str, Any]:
    async with AUTOMATION_ENGINE_LOCK:
        data = automation_store()
        suggestion = next((item for item in data["suggestions"] if item.get("id") == suggestion_id), None)
        if not suggestion or suggestion.get("status") not in {"pending", "approval_required"}:
            raise HTTPException(status_code=404, detail="Pending automation suggestion not found")
        if suggestion.get("source") == "automation_brain":
            entity_id = str(suggestion.get("action_entity") or "")
            service = str(suggestion.get("action_service") or "")
            if _automation_label_blocks_control(data, entity_id):
                raise HTTPException(status_code=403, detail="Automation Brain control is blocked by a Home Assistant label")
            try:
                domain = ensure_control_allowed(entity_id)
            except (PermissionError, ValueError) as exc:
                raise HTTPException(status_code=403, detail=str(exc)) from exc
            if service != f"{domain}.turn_on" or domain not in {"light", "switch", "fan", "input_boolean"}:
                raise HTTPException(status_code=400, detail="Automation Brain action is outside its low-risk approval boundary")
            try:
                await ha_ws.call_service(domain, "turn_on", {"entity_id": entity_id})
            except Exception as exc:
                raise HTTPException(status_code=502, detail=f"Automation Brain action failed: {exc}") from exc
            suggestion["status"] = "executed"
            suggestion["resolved_at"] = time.time()
            discovery = next((item for item in data.get("discoveries", []) if item.get("id") == suggestion.get("discovery_id")), None)
            if discovery:
                discovery["positive_feedback"] = int(discovery.get("positive_feedback") or 0) + 1
                discovery["last_feedback"] = "helpful"
            _automation_event(data, "feedback", f"Automation Brain suggestion approved: {suggestion.get('title')}", entity_id)
            _automation_save(data)
            return {"executed": True, "service": service, "entity_id": entity_id, "suggestion": suggestion}
        automation = next((item for item in data["automations"] if item.get("id") == suggestion.get("automation_id")), None)
        if not automation:
            raise HTTPException(status_code=404, detail="Automation definition not found")
        try:
            result = await _automation_execute_action(data, automation, suggestion, "explicit_approval")
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Automation action failed: {exc}") from exc
        return {**result, "suggestion": suggestion}


@app.post("/api/automations/suggestions/{suggestion_id}/dismiss")
async def dismiss_automation_suggestion(suggestion_id: str) -> dict[str, Any]:
    data = automation_store()
    suggestion = next((item for item in data["suggestions"] if item.get("id") == suggestion_id), None)
    if not suggestion or suggestion.get("status") not in {"pending", "approval_required"}:
        raise HTTPException(status_code=404, detail="Pending automation suggestion not found")
    suggestion["status"] = "dismissed"
    suggestion["resolved_at"] = time.time()
    if suggestion.get("source") == "automation_brain":
        discovery = next((item for item in data.get("discoveries", []) if item.get("id") == suggestion.get("discovery_id")), None)
        if discovery:
            discovery["negative_feedback"] = int(discovery.get("negative_feedback") or 0) + 1
            discovery["last_feedback"] = "not_helpful"
    _automation_event(data, "dismissed", f"Suggestion dismissed: {suggestion.get('title')}")
    _automation_save(data)
    return {"dismissed": True, "suggestion": suggestion}


@app.post("/api/automations/discoveries/{discovery_id}/feedback")
async def automation_discovery_feedback(discovery_id: str, request: AutomationDiscoveryFeedbackRequest) -> dict[str, Any]:
    data = automation_store()
    discovery = next((item for item in data.get("discoveries", []) if item.get("id") == discovery_id), None)
    if not discovery:
        raise HTTPException(status_code=404, detail="Automation Brain discovery not found")
    feedback = request.feedback
    if feedback in {"helpful", "always_suggest"}:
        discovery["positive_feedback"] = int(discovery.get("positive_feedback") or 0) + 1
    else:
        discovery["negative_feedback"] = int(discovery.get("negative_feedback") or 0) + 1
    discovery["preference"] = feedback if feedback in {"always_suggest", "never_suggest"} else discovery.get("preference", "ask")
    discovery["status"] = "suppressed" if feedback == "never_suggest" else "ready"
    discovery["last_feedback"] = feedback
    discovery["last_feedback_at"] = time.time()
    _automation_event(data, "feedback", f"Automation Brain learned: {discovery.get('title')}", feedback.replace("_", " "))
    _automation_save(data)
    return {"learned": True, "discovery": discovery}


GOOGLE_CALENDAR_SYNC_TASK: asyncio.Task[Any] | None = None


@app.get("/api/calendar/google/status")
async def read_google_calendar_sync_status() -> dict[str, Any]:
    return google_calendar_sync_status()


@app.get("/api/calendar/google/calendars")
async def read_google_calendars() -> dict[str, Any]:
    return await google_calendar_list_calendars()


@app.post("/api/calendar/google/preview")
async def preview_google_calendar_sync() -> dict[str, Any]:
    return await google_calendar_preview()


@app.put("/api/calendar/google/settings")
async def update_google_calendar_sync_settings(request: GoogleCalendarSyncSettingsRequest) -> dict[str, Any]:
    state = google_calendar_sync_store()
    if request.enabled:
        if not google_calendar_connected():
            raise HTTPException(status_code=409, detail="Connect Google Calendar Direct first")
        if time.time() - float(state.get("previewed_at") or 0) > 1800 or request.calendar_id != state.get("calendar_id"):
            raise HTTPException(status_code=409, detail="Preview this calendar before enabling synchronization")
    state["calendar_id"] = request.calendar_id
    state["enabled"] = request.enabled
    if request.calendar_id != google_calendar_sync_store().get("calendar_id"):
        state.update({"sync_token": "", "initial_sync_complete": False, "previewed_at": 0, "preview": {}})
    _google_calendar_sync_save(state)
    return google_calendar_sync_status()


@app.post("/api/calendar/google/sync")
async def run_google_calendar_sync() -> dict[str, Any]:
    if not google_calendar_sync_store()["enabled"]:
        raise HTTPException(status_code=409, detail="Enable Google Calendar synchronization first")
    return {"synchronized": True, "result": await google_calendar_sync_once(), "status": google_calendar_sync_status()}


CALENDAR_REMINDER_TASK: asyncio.Task[Any] | None = None


@app.get("/api/calendar")
async def read_calendar(include_past: bool = False) -> dict[str, Any]:
    result = list_calendar_appointments(include_past)
    settings = notification_store()["settings"]
    result["default_destination"] = str(settings.get("default_channel") or "")
    result["reminder_presets"] = [
        {"offset_minutes": value, "label": label}
        for value, label in sorted(CALENDAR_REMINDER_OFFSETS.items(), reverse=True)
    ]
    return result


@app.post("/api/calendar")
async def create_calendar_appointment(request: CalendarAppointmentRequest) -> dict[str, Any]:
    return await _create_calendar_appointment(request)


@app.put("/api/calendar/{appointment_id}/reminders")
async def update_calendar_reminders(
    appointment_id: str, request: CalendarRemindersUpdateRequest,
) -> dict[str, Any]:
    return await _update_calendar_reminders(appointment_id, request)


@app.delete("/api/calendar/{appointment_id}")
async def cancel_calendar_appointment(appointment_id: str) -> dict[str, Any]:
    return _cancel_calendar_appointment(appointment_id)


NOTIFICATION_WATCH_TASK: asyncio.Task[Any] | None = None


@app.post("/api/notifications/watches")
async def create_notification_watch(request: NotificationWatchRequest) -> dict[str, Any]:
    return await _create_notification_watch(request)


@app.put("/api/notifications/watches/{watch_id}/state")
async def set_notification_watch_state(watch_id: str, request: NotificationWatchStateRequest) -> dict[str, Any]:
    data = automation_store()
    watch = next((item for item in notification_watches(data) if item.get("id") == watch_id), None)
    if not watch:
        raise HTTPException(status_code=404, detail="Notification watch not found")
    watch["enabled"] = request.enabled
    watch["status"] = "armed" if request.enabled else "paused"
    watch["last_observed_state"] = None
    watch["updated_at"] = time.time()
    _automation_event(data, "notification_watch", f"Notification watch {'armed' if request.enabled else 'paused'}: {watch.get('name')}")
    _automation_save(data)
    return {"saved": True, "watch": watch}


@app.delete("/api/notifications/watches/{watch_id}")
async def delete_notification_watch(watch_id: str) -> dict[str, Any]:
    data = automation_store()
    watch = next((item for item in notification_watches(data) if item.get("id") == watch_id), None)
    if not watch:
        raise HTTPException(status_code=404, detail="Notification watch not found")
    data["automations"] = [item for item in data["automations"] if item.get("id") != watch_id]
    _automation_event(data, "notification_watch", f"Notification watch deleted: {watch.get('name')}")
    _automation_save(data)
    return {"deleted": True}


@app.put("/api/chat/{session_id}/voice")
async def update_chat_voice_preference(session_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    enabled = payload.get("auto_speak")
    if not isinstance(enabled, bool):
        raise HTTPException(status_code=400, detail="auto_speak must be a boolean")
    get_chat_history(session_id)
    CHAT_SESSION_META[session_id]["auto_speak"] = enabled
    persist_chat_sessions()
    return {"session_id": session_id, "auto_speak": enabled}


@app.get("/api/tab-activity")
async def read_tab_activity() -> dict[str, Any]:
    return {"revisions": tab_activity_revisions()}


@app.get("/api/notifications/activity")
async def read_notification_activity() -> dict[str, Any]:
    deliveries = notification_store().get("deliveries") or []
    newest = deliveries[0] if deliveries else {}
    return {
        "latest_id": str(newest.get("id") or ""),
        "latest_at": float(newest.get("created_at") or 0.0),
        "count": len(deliveries),
    }


@app.delete("/api/notifications/deliveries")
async def delete_notification_deliveries(request: NotificationDeliveryDeleteRequest) -> dict[str, Any]:
    requested = {item.strip() for item in request.ids if item.strip()}
    if not requested:
        raise HTTPException(status_code=400, detail="Select at least one delivery log")
    data = notification_store()
    original = list(data.get("deliveries") or [])
    data["deliveries"] = [item for item in original if str(item.get("id") or "") not in requested]
    deleted = len(original) - len(data["deliveries"])
    if deleted:
        _notification_save(data)
    return {"deleted": deleted, "remaining": len(data["deliveries"])}


@app.get("/api/notifications")
async def read_notification_center() -> dict[str, Any]:
    data = notification_store()
    channels = await notification_channels()
    configured = data["settings"].get("default_channel")
    if configured and not any(item["entity_id"] == configured for item in channels):
        data["settings"]["default_channel_available"] = False
    else:
        data["settings"]["default_channel_available"] = bool(configured)
    return {
        **data,
        "channels": channels,
        "watches": notification_watches(),
        "telegram_channels": sum(item["platform"] == "telegram" for item in channels),
        "credential_boundary": "Bot tokens remain in Home Assistant and are never returned to ZBRANO.",
    }


@app.put("/api/notifications/settings")
async def update_notification_settings(request: NotificationCenterSettingsRequest) -> dict[str, Any]:
    data = notification_store()
    settings = request.model_dump()
    settings["default_channel"] = settings["default_channel"].strip().lower()
    if settings["default_channel"]:
        channels = await notification_channels()
        if not any(item["entity_id"] == settings["default_channel"] for item in channels):
            raise HTTPException(status_code=400, detail="Selected notification channel is unavailable")
    data["settings"] = settings
    _notification_save(data)
    return {"saved": True, "settings": settings}


@app.post("/api/notifications/test")
async def test_notification_channel(request: NotificationTestRequest) -> dict[str, Any]:
    channels = await notification_channels()
    channel = next((item for item in channels if item["entity_id"] == request.target), None)
    if not channel:
        raise HTTPException(status_code=400, detail="Notification target is not an available Home Assistant notify entity")
    if not SUPERVISOR_TOKEN:
        raise HTTPException(status_code=503, detail="Home Assistant API token unavailable")

    title = request.title.strip() or "ZBRANO notification test"
    data = notification_store()
    message = request.message.strip()
    if channel["platform"] == "telegram":
        # Home Assistant's Telegram notify entity can return HTTP 500 when the
        # generic notify.send_message action includes its optional title key.
        # Match the Home Assistant action that was verified against this bot:
        # send only entity_id and the unmodified message. The title remains in
        # ZBRANO Delivery History but is not part of the Telegram service call.
        body = {
            "entity_id": request.target,
            "message": message,
            # Generated notification text must not be interpreted as Markdown.
            # This prevents Telegram "Can't parse entities" failures.
            "parse_mode": "plain_text",
        }
    else:
        body = {
            "entity_id": request.target,
            "title": title,
            "message": message,
        }
    try:
        # Use Home Assistant's WebSocket action path. The REST endpoint can
        # return HTTP 500 after Telegram has already accepted the message,
        # producing a false failure and risking duplicate retries.
        service_domain = "telegram_bot" if channel["platform"] == "telegram" else "notify"
        await ha_ws.call_service(service_domain, "send_message", body)
        delivery = _notification_delivery(
            data, target=request.target, severity=request.severity,
            title=title, status="delivered",
            detail=(
                "Sent through telegram via Home Assistant WebSocket"
                if channel["platform"] == "telegram"
                else f"Sent through {channel['platform']} via Home Assistant WebSocket"
            ),
        )
        _notification_save(data)
        return {"delivered": True, "delivery": delivery}
    except (RuntimeError, OSError, asyncio.TimeoutError, ConnectionClosed) as exc:
        delivery = _notification_delivery(
            data, target=request.target, severity=request.severity,
            title=title, status="failed", detail=str(exc),
        )
        _notification_save(data)
        raise HTTPException(status_code=502, detail=f"Notification delivery failed: {exc}") from exc


@app.get("/api/telegram-inbound")
async def read_telegram_inbound() -> dict[str, Any]:
    return telegram_public_status()


@app.put("/api/telegram-inbound/settings")
async def update_telegram_inbound_settings(request: TelegramInboundSettingsRequest) -> dict[str, Any]:
    data = telegram_inbound_store()
    settings = request.model_dump()
    settings["reply_channel"] = settings["reply_channel"].strip().lower()
    if settings["reply_channel"]:
        channels = await notification_channels()
        selected = next((item for item in channels if item["entity_id"] == settings["reply_channel"]), None)
        if not selected or selected.get("platform") != "telegram":
            raise HTTPException(status_code=400, detail="Reply channel must be an available Telegram notify entity")
    data["settings"] = settings
    save_telegram_inbound(data)
    return telegram_public_status()


@app.post("/api/telegram-inbound/link-code")
async def create_telegram_link_code() -> dict[str, Any]:
    import secrets

    data = telegram_inbound_store()
    if not data["settings"].get("enabled"):
        raise HTTPException(status_code=400, detail="Enable Telegram Inbox before generating a pairing code")
    code = secrets.token_hex(4).upper()
    expires_at = time.time() + 600
    data["pairing"] = {"code": code, "expires_at": expires_at}
    save_telegram_inbound(data)
    return {"code": code, "expires_at": expires_at, "command": f"/link {code}"}


@app.post("/api/telegram-inbound/unlink")
async def unlink_telegram_chat(request: TelegramInboundUnlinkRequest) -> dict[str, Any]:
    data = telegram_inbound_store()
    before = len(data["linked_chats"])
    data["linked_chats"] = [item for item in data["linked_chats"] if str(item.get("chat_id")) != request.chat_id]
    save_telegram_inbound(data)
    return {"removed": len(data["linked_chats"]) < before, **telegram_public_status()}


@app.on_event("startup")
async def start_telegram_inbound_lifecycle() -> None:
    await start_telegram_inbound_worker()


@app.on_event("shutdown")
async def stop_telegram_inbound_lifecycle() -> None:
    await stop_telegram_inbound_worker()


@app.get("/api/settings")
async def read_settings() -> dict[str, Any]:
    instructions = load_general_instructions()
    voice = load_elevenlabs_voice_settings()
    return {
        "general_instructions": instructions,
        "max_characters": GENERAL_INSTRUCTIONS_MAX_CHARS,
        "elevenlabs_voice_settings": voice,
        "elevenlabs_voice_defaults": ELEVENLABS_VOICE_DEFAULTS,
        "preferences": load_preferences(),
        "elevenlabs_models": sorted(ELEVENLABS_MODELS),
    }


@app.put("/api/settings")
async def update_settings(request: JarvisSettingsUpdate) -> dict[str, Any]:
    if request.elevenlabs_model not in ELEVENLABS_MODELS:
        raise HTTPException(status_code=400, detail="Unsupported ElevenLabs model")
    try:
        instructions = save_general_instructions(request.general_instructions)
        voice = save_elevenlabs_voice_settings(
            {
                "stability": request.elevenlabs_stability,
                "similarity": request.elevenlabs_similarity,
                "style": request.elevenlabs_style,
                "speed": request.elevenlabs_speed,
            }
        )
        preferences = save_preferences(
            {
                "elevenlabs_model": request.elevenlabs_model,
                "elevenlabs_speaker_boost": request.elevenlabs_speaker_boost,
                "agent_model": request.agent_model.strip(),
                "reasoning_effort": request.reasoning_effort,
                "auto_speak": request.auto_speak,
                "proactive_voice_enabled": request.proactive_voice_enabled,
                "voice_approval_enabled": request.voice_approval_enabled,
                "wake_word_enabled": request.wake_word_enabled,
                "wake_phrase": " ".join(request.wake_phrase.lower().split()),
                "response_length": request.response_length,
                "confirmation_strictness": request.confirmation_strictness,
                "context_messages": request.context_messages,
                "retention_days": request.retention_days,
                "preferred_language": request.preferred_language.strip() or "auto",
                "pronunciation_dictionary": request.pronunciation_dictionary.strip(),
                "theme": request.theme,
                "neural_style": request.neural_style,
                "neural_scale": request.neural_scale,
                "neural_node_size": request.neural_node_size,
                "neural_opacity": request.neural_opacity,
                "reduced_motion": request.reduced_motion,
                "text_size": request.text_size,
                "interface_density": request.interface_density,
                "quiet_hours_enabled": request.quiet_hours_enabled,
                "quiet_hours_start": request.quiet_hours_start,
                "quiet_hours_end": request.quiet_hours_end,
                "voice_volume": request.voice_volume,
                "auto_sync_releases_to_workshop_memory": request.auto_sync_releases_to_workshop_memory,
                "web_search_enabled": request.web_search_enabled,
                "web_search_context_size": request.web_search_context_size,
                "fast_memory_enabled": request.fast_memory_enabled,
                "fast_memory_auto_capture": request.fast_memory_auto_capture,
                "fast_memory_context_items": request.fast_memory_context_items,
            }
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if preferences["auto_sync_releases_to_workshop_memory"]:
        schedule_release_sync()
    else:
        cancel_release_sync()
    return {
        "saved": True,
        "general_instructions": instructions,
        "elevenlabs_voice_settings": voice,
        "preferences": preferences,
        "release_sync": release_sync_status(),
    }


@app.get("/api/fast-memory")
async def read_fast_memory(query: str = "", kind: str = "", limit: int = 100) -> dict[str, Any]:
    result = fast_memory_search(query, kind=kind, limit=limit)
    result["status"] = fast_memory_status()
    return result


@app.post("/api/fast-memory")
async def create_fast_memory(request: FastMemoryWriteRequest) -> dict[str, Any]:
    return upsert_fast_memory(request.model_dump(), automatic=False)


@app.put("/api/fast-memory/{memory_id}")
async def update_fast_memory(memory_id: str, request: FastMemoryWriteRequest) -> dict[str, Any]:
    with _fast_memory_connect() as connection:
        existing = connection.execute("SELECT id FROM memory_records WHERE id=?", (memory_id,)).fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="Fast Memory record not found")
    result = upsert_fast_memory(request.model_dump(), automatic=False)
    replacement_id = str((result.get("memory") or {}).get("id") or "")
    if replacement_id and replacement_id != memory_id:
        delete_fast_memory(memory_id)
    return result


@app.delete("/api/fast-memory/{memory_id}")
async def remove_fast_memory(memory_id: str) -> dict[str, Any]:
    return {"deleted": delete_fast_memory(memory_id), "id": memory_id}


@app.post("/api/fast-memory/forget")
async def forget_fast_memory_api(request: FastMemoryForgetRequest) -> dict[str, Any]:
    return forget_fast_memory(request.query)


@app.get("/api/settings/backup")
async def export_settings_backup() -> Response:
    backup = {
        "format": "jarvis-backup-v1",
        "created_at": time.time(),
        "settings": load_settings_payload(),
        "chats": json.loads(CHAT_STORAGE_PATH.read_text(encoding="utf-8"))
        if CHAT_STORAGE_PATH.exists() else {"version": 1, "sessions": {}},
        "entity_policy": json.loads(ENTITY_POLICY_PATH.read_text(encoding="utf-8"))
        if ENTITY_POLICY_PATH.exists() else {"version": 1, "entities": {}},
        "automations": automation_store(),
        "notifications": notification_store(),
        "calendar": calendar_store(),
        "fast_memory": export_fast_memory(),
    }
    # Secrets are environment-backed and are intentionally absent from this file.
    return Response(
        json.dumps(backup, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=zbrano-backup.json"},
    )


@app.post("/api/settings/restore")
async def restore_settings_backup(request: SettingsRestoreRequest) -> dict[str, Any]:
    backup = request.backup
    if backup.get("format") != "jarvis-backup-v1":
        raise HTTPException(status_code=400, detail="Unsupported ZBRANO backup format")
    settings = backup.get("settings")
    chats = backup.get("chats")
    policy = backup.get("entity_policy")
    automations = backup.get("automations")
    notifications = backup.get("notifications")
    calendar = backup.get("calendar")
    fast_memory = backup.get("fast_memory")
    if not isinstance(settings, dict) or not isinstance(chats, dict) or not isinstance(policy, dict):
        raise HTTPException(status_code=400, detail="Backup is missing required sections")
    if not isinstance(chats.get("sessions", {}), dict) or not isinstance(policy.get("entities", {}), dict):
        raise HTTPException(status_code=400, detail="Backup data is malformed")
    if automations is not None and (
        not isinstance(automations, dict)
        or not isinstance(automations.get("settings"), dict)
        or not isinstance(automations.get("automations"), list)
        or not isinstance(automations.get("suggestions", []), list)
        or not isinstance(automations.get("timeline", []), list)
    ):
        raise HTTPException(status_code=400, detail="Automation backup data is malformed")
    if notifications is not None and (
        not isinstance(notifications, dict)
        or not isinstance(notifications.get("settings"), dict)
        or not isinstance(notifications.get("deliveries", []), list)
    ):
        raise HTTPException(status_code=400, detail="Backup notification data is malformed")
    if calendar is not None and (
        not isinstance(calendar, dict)
        or not isinstance(calendar.get("appointments", []), list)
    ):
        raise HTTPException(status_code=400, detail="Backup calendar data is malformed")
    if fast_memory is not None and (
        not isinstance(fast_memory, dict)
        or not isinstance(fast_memory.get("memories", []), list)
    ):
        raise HTTPException(status_code=400, detail="Backup Fast Memory data is malformed")
    save_settings_payload(settings)
    CHAT_STORAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CHAT_STORAGE_PATH.write_text(json.dumps(chats, ensure_ascii=False, indent=2), encoding="utf-8")
    save_entity_policy(policy.get("entities", {}))
    if automations is not None:
        _automation_save(automations)
    if notifications is not None:
        _notification_save(notifications)
    if calendar is not None:
        _calendar_save(calendar)
    if fast_memory is not None:
        restore_fast_memory(fast_memory)
    load_chat_sessions()
    return {"restored": True, "chat_count": len(CHAT_SESSIONS), "automation_count": len(automation_store()["automations"])}


@app.delete("/api/chats")
async def clear_all_chats() -> dict[str, Any]:
    count = len(CHAT_SESSIONS)
    CHAT_SESSIONS.clear()
    CHAT_SESSION_ORDER.clear()
    CHAT_SESSION_META.clear()
    clear_chat_files()
    persist_chat_sessions()
    return {"deleted": count}


@app.post("/api/chats")
async def create_chat(request: ChatSessionCreate) -> dict[str, Any]:
    get_chat_history(request.session_id)
    if not is_internal_chat_session(request.session_id):
        persist_chat_sessions()
    return {"session_id": request.session_id, "title": "New chat"}


@app.get("/api/chat/history/{session_id}")
async def read_chat_history(session_id: str) -> dict[str, Any]:
    history = get_chat_history(session_id)
    return {
        "session_id": session_id,
        "title": CHAT_SESSION_META.get(session_id, {}).get("title") or chat_title(history),
        "auto_speak": CHAT_SESSION_META.get(session_id, {}).get("auto_speak"),
        "messages": [public_chat_message(message) for message in history],
    }


@app.delete("/api/chat/history/{session_id}")
async def delete_chat_history(session_id: str) -> dict[str, Any]:
    clear_chat_history(session_id)
    return {"cleared": True, "session_id": session_id}


@app.post("/api/files/chat/{session_id}")
async def upload_chat_file(session_id:str,file:UploadFile=File(...)): return await store_upload(file,chat_upload_path(session_id),"chat",session_id)
@app.get("/api/files/chat/{session_id}")
async def list_chat_files(session_id:str): return {"files":list_files(chat_upload_path(session_id))}
@app.post("/api/files/shared")
async def upload_shared_file(file:UploadFile=File(...)): return await store_upload(file,SHARED_FILE_ROOT,"shared")
@app.get("/api/files/shared")
async def list_shared_files(sort:str="date",order:str="desc"):
    return {"files":shared_file_records(sort,order)}
@app.delete("/api/files/shared")
async def delete_shared_files(r:SharedFilesDeleteRequest):
    done=delete_shared_file_ids(r.file_ids)
    return {"deleted":done,"count":len(done)}


async def developer_diagnostics() -> dict[str, object]:
    purge_internal_chat_sessions()
    checks: list[dict[str, object]] = []

    def add(name: str, status: str, detail: str, category: str, repair_hint: str = "") -> None:
        normalized = status if status in {"present", "wired", "operational", "degraded", "failed"} else "failed"
        checks.append({
            "name": name,
            "status": normalized,
            "ok": normalized != "failed",
            "detail": detail,
            "category": category,
            "repair_hint": repair_hint,
        })

    async with httpx.AsyncClient(timeout=12.0) as client:
        async def request_json(path: str, method: str = "GET", timeout: float = 12.0, **kwargs):
            response = await client.request(
                method,
                f"http://127.0.0.1:8099{path}",
                timeout=timeout,
                **kwargs,
            )
            try:
                payload = response.json()
            except Exception:
                payload = None
            return response, payload

        async def probe(
            name: str,
            path: str,
            validator,
            category: str,
            timeout: float = 12.0,
            optional: bool = False,
            repair_hint: str = "",
        ) -> None:
            try:
                response, payload = await request_json(path, timeout=timeout)
                if response.is_error:
                    status = "degraded" if optional else "failed"
                    add(name, status, f"HTTP {response.status_code}: {response.text[:180]}", category, repair_hint)
                    return
                status, detail = validator(payload)
                add(name, status, detail, category, repair_hint)
            except Exception as exc:
                add(name, "degraded" if optional else "failed", str(exc), category, repair_hint)

        health_payload: dict[str, object] = {}
        try:
            response, payload = await request_json("/api/health")
            health_payload = payload if isinstance(payload, dict) else {}
            version = str(health_payload.get("version") or "")
            expected_version = str(app.version)
            add(
                "Application health and version",
                "operational" if response.status_code == 200 and version == expected_version else "failed",
                f"HTTP {response.status_code}; runtime version {version or 'missing'}; expected {expected_version}",
                "runtime",
                "Rebuild from the current main branch and verify every version marker.",
            )
            voice_ready = bool(health_payload.get("voice_configured"))
            openai_ready = bool(health_payload.get("openai_configured"))
            add(
                "AI chat readiness",
                "operational" if openai_ready else "degraded",
                f"model={health_payload.get('openai_model')}; configured={openai_ready}; no billable completion generated",
                "chat",
                "Configure the OpenAI API key and verify the selected model before testing a live completion.",
            )
            web_search_enabled = load_preferences().get("web_search_enabled") is not False
            add(
                "Native Web Search configuration",
                "operational" if openai_ready and web_search_enabled else "degraded",
                f"tool=web_search; model={health_payload.get('openai_model')}; enabled={web_search_enabled}; live search not generated by diagnostics",
                "web_search",
                "Configure the OpenAI API key, enable Web Search in Settings, and verify that the selected model supports the hosted web_search tool.",
            )
            add(
                "Voice pipeline readiness",
                "operational" if voice_ready else "degraded",
                f"provider={health_payload.get('speech_provider')}; configured={voice_ready}",
                "voice",
                "Configure an OpenAI key or a complete ElevenLabs key and voice ID.",
            )
        except Exception as exc:
            add("Application health and version", "failed", str(exc), "runtime", "Inspect startup logs and /api/health.")
            add("AI chat readiness", "degraded", "Health payload unavailable", "chat")
            add("Voice pipeline readiness", "degraded", "Health payload unavailable", "voice")

        await probe(
            "Settings API operational",
            "/api/settings",
            lambda payload: (
                "operational" if isinstance(payload, dict) and isinstance(payload.get("preferences"), dict) else "failed",
                "preferences and voice settings readable" if isinstance(payload, dict) else "invalid JSON payload",
            ),
            "settings",
            repair_hint="Inspect /data settings JSON and settings route logs.",
        )
        await probe(
            "Release memory synchronization",
            "/api/release-memory-sync",
            lambda payload: (
                (
                    "operational" if payload.get("state") in {"synchronized", "disabled"}
                    else "degraded" if payload.get("state") in {"pending", "synchronizing", "retrying"}
                    else "failed"
                ) if isinstance(payload, dict) else "failed",
                (
                    f"state={payload.get('state')}; version={payload.get('version') or app.version}; "
                    f"enabled={payload.get('enabled')}; task_active={payload.get('task_active')}; "
                    f"progress={payload.get('note_progress')}; current_note={payload.get('current_note')}; "
                    f"target={payload.get('target')}"
                    if isinstance(payload, dict) else "invalid release synchronization payload"
                ),
            ),
            "workshop_memory",
            repair_hint="Verify Workshop Memory connectivity, the ZBRANO project name, and Release and Change Log.md.",
        )

        await probe(
            "Conversations API operational",
            "/api/chats",
            lambda payload: (
                "operational" if isinstance(payload, dict) and isinstance(payload.get("chats"), list) else "failed",
                f"{len(payload.get('chats', [])) if isinstance(payload, dict) else 0} conversations readable",
            ),
            "chat",
        )
        await probe(
            "Plugins API operational",
            "/api/plugins",
            lambda payload: (
                "operational" if isinstance(payload, dict) and isinstance(payload.get("plugins"), list) else "failed",
                f"{len(payload.get('plugins', [])) if isinstance(payload, dict) else 0} installed plugins",
            ),
            "plugins",
        )
        oauth_records = plugin_oauth_records()
        oauth_task_ready = PLUGIN_OAUTH_REFRESH_TASK is not None and not PLUGIN_OAUTH_REFRESH_TASK.done()
        google_oauth_ready = bool(
            os.getenv("GOOGLE_OAUTH_CLIENT_ID", "").strip()
            and os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "").strip()
        )
        add(
            "Gmail OAuth configuration",
            "operational" if google_oauth_ready else "setup_required",
            "Google OAuth client configured" if google_oauth_ready else "Add the Google OAuth client ID and secret in add-on settings",
            "plugins",
            "Create a Google Web OAuth client and register ZBRANO's exact callback URL.",
        )
        calendar_sync = google_calendar_sync_status()
        add(
            "Google Calendar Direct synchronization",
            "operational" if calendar_sync["connected"] and not calendar_sync["last_error"] else "setup_required" if not calendar_sync["connected"] else "degraded",
            f"connected={calendar_sync['connected']}; enabled={calendar_sync['enabled']}; pending={calendar_sync['pending_local_changes']}; last_success={calendar_sync['last_success_at'] or 'never'}",
            "calendar",
            "Connect Google Calendar Direct, preview the selected calendar, then enable synchronization.",
        )
        add(
            "Plugin OAuth engine operational",
            "operational" if oauth_task_ready else "degraded",
            f"refresh worker={'active' if oauth_task_ready else 'inactive'}; {len(oauth_records)} OAuth connection record(s)",
            "plugins",
            "Restart the add-on if the OAuth refresh worker is inactive.",
        )

        await probe(
            "Autonomous Automations API operational",
            "/api/automations",
            lambda payload: (
                "operational" if isinstance(payload, dict) and isinstance(payload.get("automations"), list) else "failed",
                f"{len(payload.get('automations', [])) if isinstance(payload, dict) else 0} automation definitions; event-driven evaluator={payload.get('engine', {}).get('status', 'unavailable') if isinstance(payload, dict) else 'unavailable'}",
            ),
            "automations",
        )

        await probe(
            "Notification Center API operational",
            "/api/notifications",
            lambda payload: (
                "operational" if isinstance(payload, dict) and isinstance(payload.get("channels"), list) else "failed",
                f"{len(payload.get('channels', [])) if isinstance(payload, dict) else 0} Home Assistant notify channels; {payload.get('telegram_channels', 0) if isinstance(payload, dict) else 0} Telegram; {len(payload.get('watches', [])) if isinstance(payload, dict) else 0} event-driven watches",
            ),
            "automations",
        )

        await probe(
            "Calendar and reminders API operational",
            "/api/calendar",
            lambda payload: (
                "operational" if isinstance(payload, dict) and isinstance(payload.get("appointments"), list) else "failed",
                f"{len(payload.get('appointments', [])) if isinstance(payload, dict) else 0} upcoming appointments; reminder worker configured",
            ),
            "calendar",
        )

        catalog_attempts = []
        catalog_ok = False
        for attempt in (1, 2):
            try:
                response, payload = await request_json("/api/plugin-catalog", timeout=18.0)
                plugins = payload.get("plugins", []) if isinstance(payload, dict) else []
                catalog_attempts.append(f"attempt {attempt}: HTTP {response.status_code}, {len(plugins)} plugins")
                if response.status_code == 200 and isinstance(plugins, list) and plugins:
                    add(
                        "Plugin Catalog operational",
                        "operational" if attempt == 1 else "degraded",
                        "; ".join(catalog_attempts) + ("; cold start required retry" if attempt > 1 else ""),
                        "plugins",
                        "Warm the catalog cache and distinguish registry latency from endpoint failure.",
                    )
                    catalog_ok = True
                    break
            except Exception as exc:
                catalog_attempts.append(f"attempt {attempt}: {exc}")
            if attempt == 1:
                await asyncio.sleep(0.5)
        if not catalog_ok:
            add(
                "Plugin Catalog operational",
                "failed",
                "; ".join(catalog_attempts) or "no response",
                "plugins",
                "Inspect catalog cache, Registry connectivity, and featured fallback handling.",
            )

        await probe(
            "Shared Files list operational",
            "/api/files/shared",
            lambda payload: (
                "operational" if isinstance(payload, dict) and isinstance(payload.get("files"), list) else "failed",
                f"{len(payload.get('files', [])) if isinstance(payload, dict) else 0} shared files readable",
            ),
            "files",
        )
        await probe(
            "Entity inventory operational",
            "/api/ha/entities",
            lambda payload: (
                "operational" if isinstance(payload, dict) and isinstance(payload.get("entities"), list) else "failed",
                f"{len(payload.get('entities', [])) if isinstance(payload, dict) else 0} entities returned",
            ),
            "home_assistant",
            timeout=25.0,
            optional=True,
            repair_hint="Check Supervisor token, Home Assistant connectivity, and WebSocket status.",
        )
        await probe(
            "Home Assistant connection",
            "/api/ha/websocket-status",
            lambda payload: (
                "operational" if isinstance(payload, dict) and payload.get("connected") else "degraded",
                "WebSocket connected" if isinstance(payload, dict) and payload.get("connected") else str((payload or {}).get("last_error") or "WebSocket disconnected; REST fallback available"),
            ),
            "home_assistant",
            timeout=15.0,
            optional=True,
        )
        await probe(
            "Developer API operational",
            "/api/developer/status",
            lambda payload: (
                "operational" if isinstance(payload, dict) and payload.get("repository") == DEVELOPER_REPOSITORY else "failed",
                f"repository={payload.get('repository') if isinstance(payload, dict) else 'invalid'}; deployment={payload.get('deployment') if isinstance(payload, dict) else 'invalid'}",
            ),
            "developer",
        )
        await probe(
            "Connection status API operational",
            "/api/connections/status",
            lambda payload: (
                "operational" if isinstance(payload, dict) and all(key in payload for key in ("home_assistant", "workshop_memory", "openai")) else "failed",
                "Home Assistant, Workshop Memory, and OpenAI states readable" if isinstance(payload, dict) else "invalid JSON payload",
            ),
            "integrations",
        )
        await probe(
            "Workshop Memory operational",
            "/api/memory/status",
            lambda payload: (
                "operational" if isinstance(payload, dict) and payload.get("connected") else "degraded",
                "MCP status call succeeded" if isinstance(payload, dict) and payload.get("connected") else "MCP status did not confirm a connection",
            ),
            "integrations",
            timeout=18.0,
            optional=True,
            repair_hint="Check the configured Workshop Memory endpoint and its MCP status tool.",
        )

        storage_root = Path("/data/.zbrano-diagnostics")
        storage_file = storage_root / f"persistence-{time.time_ns()}.txt"
        try:
            storage_root.mkdir(parents=True, exist_ok=True)
            storage_file.write_text("zbrano persistence diagnostic", encoding="utf-8")
            stored_text = storage_file.read_text(encoding="utf-8")
            add(
                "Persistent storage operational",
                "operational" if stored_text == "zbrano persistence diagnostic" else "failed",
                "temporary /data write/read/delete cycle completed",
                "persistence",
                "Check add-on /data permissions and available storage.",
            )
        except Exception as exc:
            add("Persistent storage operational", "failed", str(exc), "persistence", "Check /data permissions and disk health.")
        finally:
            try:
                storage_file.unlink(missing_ok=True)
                storage_root.rmdir()
            except OSError:
                pass

        chat_session = f"zbrano-diagnostic-{time.time_ns():x}"[-80:]
        try:
            create_response, created = await request_json(
                "/api/chats",
                method="POST",
                json={"session_id": chat_session},
            )
            history_response, history = await request_json(f"/api/chat/history/{chat_session}")
            delete_response, deleted = await request_json(f"/api/chat/history/{chat_session}", method="DELETE")
            ok = (
                create_response.status_code == 200
                and history_response.status_code == 200
                and delete_response.status_code == 200
                and isinstance(created, dict)
                and isinstance(history, dict)
                and isinstance(deleted, dict)
                and deleted.get("cleared") is True
            )
            add(
                "Conversation lifecycle operational",
                "operational" if ok else "failed",
                f"create={create_response.status_code}; read={history_response.status_code}; delete={delete_response.status_code}",
                "chat",
                "Inspect chat persistence and session cleanup.",
            )
        except Exception as exc:
            add("Conversation lifecycle operational", "failed", str(exc), "chat", "Inspect chat persistence and session cleanup.")
        finally:
            # In-process cleanup cannot be interrupted at an HTTP await boundary.
            clear_chat_history(chat_session)

        attachment_session = f"zbrano-attachment-{time.time_ns():x}"[-80:]
        attachment_dir = chat_upload_path(attachment_session)
        try:
            response, payload = await request_json(
                f"/api/files/chat/{attachment_session}",
                method="POST",
                files={"file": ("zbrano-diagnostic.txt", b"attachment diagnostic\n", "text/plain")},
            )
            file_id = payload.get("file_id") if isinstance(payload, dict) else None
            stored = attachment_dir / str(file_id)
            ok = response.status_code == 200 and bool(file_id) and stored.is_dir()
            add(
                "Chat attachment lifecycle operational",
                "operational" if ok else "failed",
                f"HTTP {response.status_code}; upload ID and extracted storage verified",
                "files",
                "Inspect the chat upload endpoint, /data permissions, and attachment controller.",
            )
        except Exception as exc:
            add("Chat attachment lifecycle operational", "failed", str(exc), "files")
        finally:
            shutil.rmtree(attachment_dir, ignore_errors=True)

        shared_file_id = None
        try:
            upload_response, uploaded = await request_json(
                "/api/files/shared",
                method="POST",
                files={"file": ("zbrano-shared-diagnostic.txt", b"shared file diagnostic\n", "text/plain")},
            )
            shared_file_id = uploaded.get("file_id") if isinstance(uploaded, dict) else None
            list_response, listed = await request_json("/api/files/shared")
            listed_ids = {
                str(item.get("file_id"))
                for item in (listed.get("files", []) if isinstance(listed, dict) else [])
                if isinstance(item, dict)
            }
            delete_response, deleted = await request_json(
                "/api/files/shared",
                method="DELETE",
                json={"file_ids": [shared_file_id] if shared_file_id else []},
            )
            removed = bool(shared_file_id) and not (SHARED_FILE_ROOT / str(shared_file_id)).exists()
            ok = (
                upload_response.status_code == 200
                and list_response.status_code == 200
                and shared_file_id in listed_ids
                and delete_response.status_code == 200
                and isinstance(deleted, dict)
                and deleted.get("count") == 1
                and removed
            )
            add(
                "Shared Files create/list/delete operational",
                "operational" if ok else "failed",
                f"upload={upload_response.status_code}; listed={shared_file_id in listed_ids}; delete={delete_response.status_code}; removed={removed}",
                "files",
                "Inspect the Shared Files API and browser action controller.",
            )
        except Exception as exc:
            add("Shared Files create/list/delete operational", "failed", str(exc), "files")
        finally:
            if shared_file_id and FILE_ID_RE.fullmatch(str(shared_file_id)):
                shutil.rmtree(SHARED_FILE_ROOT / str(shared_file_id), ignore_errors=True)

    try:
        memory_health = fast_memory_status()
        add(
            "Fast Memory operational",
            "operational" if memory_health.get("operational") else "failed",
            f"{memory_health.get('total', 0)} organized records; SQLite readable; bounded to {memory_health.get('max_records', 0)}",
            "memory",
            "Inspect /data/zbrano_fast_memory.sqlite3 and the Fast Memory API.",
        )
    except Exception as exc:
        add("Fast Memory operational", "failed", str(exc), "memory", "Inspect Fast Memory SQLite storage.")

    try:
        approved_result = await approved_ha_entities()
        approved_history = sorted(set(approved_result.get("read_entities", [])) | set(approved_result.get("control_entities", [])))
        if not SUPERVISOR_TOKEN:
            add("Home Assistant History API", "failed", "Supervisor token unavailable", "entities", "Enable Home Assistant API access for the add-on.")
        elif not approved_history:
            add("Home Assistant History API", "setup_required", "No read-approved entity available for a bounded probe", "entities", "Enable at least one entity in the Entities inventory.")
        else:
            history_probe = await get_home_assistant_history(approved_history[:1], 1, 10)
            add("Home Assistant History API", "operational", f"Read-only recorder query succeeded for {history_probe.get('entity_count', 0)} entity", "entities", "Inspect Home Assistant Recorder and the Supervisor API.")
    except Exception as exc:
        add("Home Assistant History API", "failed", str(exc), "entities", "Inspect Home Assistant Recorder, entity policy, and Supervisor API logs.")

    frontend_text = ""
    try:
        frontend_text = _developer_frontend_source()
    except OSError as exc:
        add("Frontend source readable", "failed", str(exc), "frontend")
    else:
        add("Frontend source readable", "present", str(DEVELOPER_FRONTEND_PATH), "frontend")
        surfaces = {
            "New Chat frontend wired": ('id="new-chat-button"', "createNewChat", 'newChatButton.addEventListener("click", createNewChat)'),
            "Attachment frontend wired": ('id="zbrano-v0122-attachment-controller"', 'picker.addEventListener("change", uploadSelectedFiles, true)', "window.zbranoAttachmentIds"),
            "Shared Files actions wired": ('id="zbrano-v0123-shared-files-controller"', 'deleteButton.addEventListener("click", deleteSelected, true)', 'useButton.addEventListener("click", attachSelected, true)'),
            "Plugins frontend wired": ('id="plugins-tab"', 'zbrano-v01131-plugin-compact', 'plugin-settings-toggle'),
            "Automations frontend wired": ('id="automations-tab"', 'id="automations-panel"', 'zbrano-v01210-autonomous-automations'),
            "Notification Center frontend wired": ('data-auto-view="notifications"', 'id="notification-settings-form"', 'zbrano-v01243-notification-center'),
            "Calendar frontend wired": ('id="calendar-tab"', 'id="calendar-panel"', 'zbrano-v01271-calendar-center'),
            "Fast Memory frontend wired": ('id="fast-memory-list"', 'id="fast-memory-form"', 'zbrano-v01274-fast-memory'),
            "HA History frontend wired": ('data-entity-view="history"', 'id="ha-timeline-events"', 'zbrano-v01276-ha-history'),
            "Entities frontend wired": ('id="entities-tab"', 'id="entities-panel"', "loadEntities"),
            "Developer frontend wired": ('id="developer-tab"', 'zbrano-v0120-developer-mode', "developer-run-diagnostics"),
            "Settings frontend wired": ('id="settings-tab"', 'id="settings-panel"', "save-settings"),
            "Voice frontend wired": ('id="mic-button"', "startRecording", "stopAudioPlayback"),
        }
        for name, markers in surfaces.items():
            missing = [marker for marker in markers if marker not in frontend_text]
            add(name, "wired" if not missing else "failed", "controller markers present" if not missing else "missing: " + ", ".join(missing), "frontend")

    try:
        registry = plugin_registry()
        add("Plugin registry readable", "operational", f"{len(registry)} installed plugins", "plugins")
    except Exception as exc:
        registry = {}
        add("Plugin registry readable", "failed", str(exc), "plugins")

    github_plugin = next(
        (
            plugin for plugin in registry.values()
            if _is_github_plugin(str(plugin.get("url") or ""), str(plugin.get("name") or ""))
        ),
        None,
    )
    if github_plugin:
        exposed = [
            tool for tool in github_plugin.get("tools", [])
            if tool.get("enabled") and tool.get("permission") in {"read_only", "write"}
        ]
        approvals = [tool for tool in exposed if tool.get("permission") == "write"]
        status = "operational" if github_plugin.get("enabled") and exposed else "degraded"
        add(
            "GitHub MCP readiness",
            status,
            f"{len(exposed)} tools exposed; {len(approvals)} write tools remain approval-required",
            "developer",
            "Connect GitHub, enable reviewed tools, and preserve write approvals.",
        )
    else:
        add("GitHub MCP readiness", "degraded", "GitHub plugin not installed", "developer", "Install and connect the official GitHub MCP plugin.")

    try:
        playwright_tools = await asyncio.wait_for(playwright_mcp_inventory(), timeout=8.0)
        playwright_missing = sorted(PLAYWRIGHT_REQUIRED_TOOLS - playwright_tools)
        add(
            "Playwright MCP readiness",
            "operational" if not playwright_missing else "failed",
            (f"{len(playwright_tools)} browser tools discovered; {playwright_preflight_summary()}" if not playwright_missing else f"missing: {', '.join(playwright_missing)}; {playwright_preflight_summary(include_log=True)}"),
            "developer",
            "Inspect the local Playwright MCP startup log and Chromium installation.",
        )
    except Exception as exc:
        add("Playwright MCP readiness", "failed", str(exc)[:500], "developer", "Inspect the local Playwright MCP startup log and Chromium installation.")

    counts = {
        status: sum(1 for check in checks if check.get("status") == status)
        for status in ("present", "wired", "operational", "degraded", "failed")
    }
    return {
        "developer_mode": developer_mode_enabled(),
        "repository": DEVELOPER_REPOSITORY,
        "passed": len(checks) - counts["failed"],
        "total": len(checks),
        "healthy": counts["failed"] == 0,
        "counts": counts,
        "checks": checks,
        "deployment": "manual",
    }


def developer_mcp_tools() -> list[dict[str, Any]]:
    """Expose only repository-capable GitHub MCP servers in Developer Mode."""
    return [
        tool for tool in active_mcp_tools()
        if _is_github_plugin(
            str(tool.get("server_url") or ""),
            str(tool.get("server_description") or tool.get("server_label") or ""),
        )
    ]


async def _targeted_developer_diagnostics(feature_key: str) -> dict[str, Any]:
    """Run one bounded feature adapter; never invoke the broad diagnostic suite."""
    checks: list[dict[str, Any]] = []

    def add(name: str, status: str, detail: str, category: str, repair_hint: str = "") -> None:
        checks.append({
            "name": name,
            "status": status,
            "ok": status != "failed",
            "detail": detail,
            "category": category,
            "repair_hint": repair_hint,
        })

    health_payload = await health()
    running_version = str(health_payload.get("version") or "")
    expected_version = str(app.version)
    add(
        "Application health and version",
        "operational" if running_version == expected_version else "failed",
        f"runtime version {running_version or 'missing'}; expected {expected_version}",
        "runtime",
        "Make every version check derive its expected value from app.version.",
    )

    route_paths = {str(getattr(route, "path", "")) for route in app.routes}
    feature_routes = {
        "attachments": ("/api/files/chat/{session_id}",),
        "shared_files": ("/api/files/shared",),
        "new_chat": ("/api/chats",),
        "plugin_catalog": ("/api/plugin-catalog",),
        "plugins": ("/api/plugins",),
        "automations": ("/api/automations",),
        "entities": ("/api/ha/entities",),
        "settings": ("/api/settings",),
        "voice": ("/api/voice/transcribe", "/api/voice/speech"),
        "workshop_memory": ("/api/connections/status",),
        "developer": ("/api/developer/status", "/api/developer/investigate"),
    }
    required_routes = feature_routes.get(feature_key, ())
    missing_routes = [path for path in required_routes if path not in route_paths]
    add(
        f"{DEVELOPER_FEATURE_SPECS[feature_key]['title']} routes",
        "wired" if not missing_routes else "failed",
        "all targeted routes registered" if not missing_routes else f"missing: {', '.join(missing_routes)}",
        "api",
        "Inspect route registration in the canonical backend and its regression coverage.",
    )

    async def probe(name: str, operation, validator, category: str) -> None:
        try:
            payload = await asyncio.wait_for(operation(), timeout=8.0)
            ok, detail = validator(payload)
            add(name, "operational" if ok else "failed", detail, category)
        except asyncio.TimeoutError:
            add(name, "degraded", "targeted adapter timed out after 8 seconds", category)
        except Exception as exc:
            add(name, "failed", str(exc)[:500], category)

    if feature_key == "shared_files":
        await probe("Shared Files list operational", list_shared_files, lambda p: (isinstance(p.get("files"), list), f"{len(p.get('files', []))} shared files readable"), "files")
    elif feature_key == "new_chat":
        await probe("Conversations API operational", list_chats, lambda p: (isinstance(p.get("chats"), list), f"{len(p.get('chats', []))} conversations readable"), "chat")
    elif feature_key == "plugin_catalog":
        await probe("Plugin Catalog operational", plugin_catalog, lambda p: (isinstance(p.get("plugins"), list), f"{len(p.get('plugins', []))} catalog entries readable"), "plugins")
    elif feature_key == "plugins":
        await probe("Plugins API operational", list_plugins, lambda p: (isinstance(p.get("plugins"), list), f"{len(p.get('plugins', []))} installed plugins"), "plugins")
        oauth_task_ready = PLUGIN_OAUTH_REFRESH_TASK is not None and not PLUGIN_OAUTH_REFRESH_TASK.done()
        add("Plugin OAuth engine operational", "operational" if oauth_task_ready else "degraded", f"refresh worker={'active' if oauth_task_ready else 'inactive'}; {len(plugin_oauth_records())} OAuth connection record(s)", "plugins")
    elif feature_key == "automations":
        await probe("Autonomous Automations API operational", read_autonomous_automations, lambda p: (isinstance(p.get("automations"), list) and p.get("engine", {}).get("status") in {"active", "waiting_for_home_assistant"}, f"{len(p.get('automations', []))} definitions; evaluator={p.get('engine', {}).get('status', 'unavailable')}"), "automations")
    elif feature_key == "entities":
        await probe("Entity inventory operational", list_ha_entities, lambda p: (isinstance(p.get("entities"), list), f"{len(p.get('entities', []))} entities returned"), "home_assistant")
    elif feature_key == "settings":
        await probe("Settings API operational", read_settings, lambda p: (isinstance(p.get("preferences"), dict), "preferences readable"), "settings")
    elif feature_key == "developer":
        await probe("Developer API operational", developer_status, lambda p: (p.get("repository") == DEVELOPER_REPOSITORY, f"repository={p.get('repository')}; deployment={p.get('deployment')}"), "developer")
        github_tools = developer_mcp_tools()
        add("Developer GitHub tools", "operational" if github_tools else "degraded", f"{len(github_tools)} GitHub MCP server(s) exposed; Workshop Memory tools excluded", "developer")
        try:
            playwright_tools = await asyncio.wait_for(playwright_mcp_inventory(), timeout=5.0)
            playwright_missing = sorted(PLAYWRIGHT_REQUIRED_TOOLS - playwright_tools)
            add(
                "Developer Playwright tools",
                "operational" if not playwright_missing else "failed",
                (f"{len(playwright_tools)} local browser tools discovered; {playwright_preflight_summary()}" if not playwright_missing else f"missing: {', '.join(playwright_missing)}; {playwright_preflight_summary(include_log=True)}"),
                "developer",
            )
        except Exception as exc:
            add("Developer Playwright tools", "failed", str(exc)[:500], "developer")
    elif feature_key == "workshop_memory":
        add("Workshop Memory configuration", "present" if WORKSHOP_MEMORY_URL else "degraded", "configuration inspected without calling Workshop Memory MCP tools", "integrations")
    elif feature_key == "voice":
        add("Voice configuration", "operational" if health_payload.get("voice_configured") else "degraded", f"provider={health_payload.get('speech_provider')}; configured={bool(health_payload.get('voice_configured'))}", "voice")

    return {"checks": checks, "scope": feature_key, "broad_diagnostics_run": False}


async def investigate_zbrano_feature(
    feature: str,
    symptom: str,
    browser_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not developer_mode_enabled():
        raise RuntimeError("Developer Mode must be enabled before investigating ZBRANO itself")

    feature_key = _resolve_developer_feature(feature, symptom)
    spec = DEVELOPER_FEATURE_SPECS[feature_key]
    diagnostics = await asyncio.wait_for(_targeted_developer_diagnostics(feature_key), timeout=20.0)
    evidence = []
    terms = tuple(str(term).lower() for term in spec["terms"])
    for check in diagnostics.get("checks", []):
        name = str(check.get("name") or "")
        if any(term in name.lower() for term in terms):
            evidence.append({
                "source": "server_diagnostic",
                "name": name,
                "status": check.get("status") or ("operational" if check.get("ok") else "failed"),
                "detail": check.get("detail") or "",
                "category": check.get("category") or "",
                "repair_hint": check.get("repair_hint") or "",
            })

    runtime = browser_evidence if isinstance(browser_evidence, dict) else {}
    browser_errors = [str(item)[:500] for item in runtime.get("errors", []) if str(item).strip()][:10]
    controller = runtime.get("controller") if isinstance(runtime.get("controller"), dict) else {}
    controls = runtime.get("controls") if isinstance(runtime.get("controls"), dict) else {}
    if runtime:
        evidence.append({
            "source": "browser_runtime",
            "name": f"{spec['title']} browser evidence",
            "status": "failed" if browser_errors or controller.get("lastActionOk") is False or controller.get("lastUploadOk") is False else "wired",
            "detail": json.dumps({
                "errors": browser_errors,
                "controller": controller,
                "controls": controls,
                "location": str(runtime.get("location") or "")[:300],
            }, ensure_ascii=False),
            "category": "browser",
            "repair_hint": "Trace the captured controller error and the last failed action through its API request and response.",
        })

    failed = [item for item in evidence if item.get("status") == "failed"]
    degraded = [item for item in evidence if item.get("status") == "degraded"]
    runtime_failure = bool(browser_errors or controller.get("lastActionOk") is False or controller.get("lastUploadOk") is False)
    general_checks_healthy = not failed and not degraded

    if failed or runtime_failure:
        status = "failed"
        fault_layers = sorted({str(item.get("category") or item.get("source")) for item in failed})
        likely_fault_boundary = ", ".join(fault_layers) or "browser runtime/controller"
        summary = f"Targeted evidence reproduced or detected a failure in {spec['title']}."
    elif degraded:
        status = "degraded"
        likely_fault_boundary = ", ".join(sorted({str(item.get("category") or "integration") for item in degraded}))
        summary = f"{spec['title']} is available but targeted evidence found degraded dependencies."
    else:
        status = "inconclusive"
        likely_fault_boundary = "unreproduced browser sequence, transient state, or behavior not covered by the current adapter"
        summary = (
            f"Targeted checks for {spec['title']} passed, but the reported symptom remains valid and was not reproduced. "
            "Do not close the issue from green diagnostics alone."
        )

    repair_plan = [
        f"Reproduce exactly: {symptom.strip()}",
        f"Trace layers in order: {' -> '.join(spec['layers'])}",
        "Inspect the relevant canonical runtime source and regression coverage before editing.",
        "Add a regression test that fails for the reported behavior, then implement the smallest repair.",
        "Build an isolated candidate and rerun targeted plus full diagnostics before requesting repository approval.",
    ]
    if not runtime:
        repair_plan.insert(1, "Collect browser controller state, console errors, and the failing request/response during reproduction.")

    return {
        "feature": feature_key,
        "title": spec["title"],
        "reported_symptom": symptom.strip(),
        "status": status,
        "summary": summary,
        "general_checks_healthy": general_checks_healthy,
        "likely_fault_boundary": likely_fault_boundary,
        "evidence": evidence,
        "relevant_files": list(spec["files"]),
        "repair_plan": repair_plan,
        "automatic_changes_made": False,
        "repository_writes_require_approval": True,
        "deployment": "manual",
    }


@app.get("/api/developer/features")
async def developer_features():
    return {
        "features": [
            {"id": key, "title": spec["title"], "layers": list(spec["layers"])}
            for key, spec in DEVELOPER_FEATURE_SPECS.items()
        ]
    }


@app.post("/api/developer/investigate")
async def developer_investigate(request: DeveloperInvestigationRequest):
    if not developer_mode_enabled():
        raise HTTPException(status_code=403, detail="Enable Developer Mode before running an investigation")
    return await investigate_zbrano_feature(
        request.feature,
        request.symptom,
        request.browser_evidence,
    )


@app.get("/api/developer/status")
async def developer_status():
    return {
        "enabled": developer_mode_enabled(),
        "repository": DEVELOPER_REPOSITORY,
        "deployment": "manual",
    }


@app.put("/api/developer/mode")
async def update_developer_mode(request: DeveloperModeRequest):
    set_developer_mode(request.enabled)
    return {
        "enabled": developer_mode_enabled(),
        "repository": DEVELOPER_REPOSITORY,
        "deployment": "manual",
    }


@app.get("/api/developer/diagnostics")
async def get_developer_diagnostics():
    return await developer_diagnostics()


@app.get("/api/ha/websocket-status")
async def ha_websocket_status() -> dict[str, Any]:
    status = ha_ws.status()
    if not status["connected"] and SUPERVISOR_TOKEN:
        try:
            await ha_ws.connect()
        except RuntimeError:
            pass
        status = ha_ws.status()
    return {
        **status,
        "url": HA_WS_URL,
        "rest_fallback": True,
    }


@app.get("/api/ha/approved")
async def approved_ha_entities() -> dict[str, Any]:
    policy = load_entity_policy()
    enabled = {
        entity_id: record
        for entity_id, record in policy.items()
        if record.get("enabled")
    }
    read_entities = sorted(
        entity_id for entity_id, record in enabled.items()
        if record.get("access") in {"read_only", "state_only"}
    )
    control_entities = sorted(
        entity_id for entity_id, record in enabled.items()
        if record.get("access") == "low_risk_control_proposed"
    )
    return {
        "read_entities": sorted(set(read_entities) | HA_READ_ENTITIES),
        "control_entities": sorted(set(control_entities) | HA_CONTROL_ENTITIES),
        "safe_control_domains": sorted(SAFE_CONTROL_DOMAINS),
        # Return the complete policy so aliases on disabled/unapproved entities
        # are restored when the Entities tab is opened again. Approval lists
        # above remain derived only from enabled records.
        "policy": policy,
        "policy_path": str(ENTITY_POLICY_PATH),
    }


@app.put("/api/ha/entity-policy/{entity_id:path}")
async def update_entity_policy(
    entity_id: str,
    request: EntityPolicyUpdate,
) -> dict[str, Any]:
    if "." not in entity_id:
        raise HTTPException(status_code=400, detail="Invalid entity ID")

    actual_domain = entity_domain(entity_id)
    if request.domain != actual_domain:
        raise HTTPException(status_code=400, detail="Entity domain mismatch")

    if request.enabled and request.access == "low_risk_control_proposed":
        if actual_domain not in SAFE_CONTROL_DOMAINS:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Control cannot be approved for domain '{actual_domain}'. "
                    f"Allowed domains: {', '.join(sorted(SAFE_CONTROL_DOMAINS))}"
                ),
            )

    clean_aliases = []
    seen = set()
    for alias in request.aliases:
        cleaned = " ".join(alias.strip().split())
        key = cleaned.lower()
        if cleaned and key not in seen:
            clean_aliases.append(cleaned)
            seen.add(key)

    policy = load_entity_policy()
    policy[entity_id] = {
        "enabled": request.enabled,
        "friendly_name": request.friendly_name,
        "domain": request.domain,
        "device_class": request.device_class,
        "unit": request.unit,
        "access": request.access,
        "aliases": clean_aliases,
    }
    save_entity_policy(policy)

    return {
        "saved": True,
        "entity_id": entity_id,
        "effective_access": effective_entity_access(entity_id),
        "record": policy[entity_id],
        "persistent_path": str(ENTITY_POLICY_PATH),
    }


@app.get("/api/ha/history")
async def api_home_assistant_history(entity_ids: str, hours: int = 24, max_points: int = 80) -> dict[str, Any]:
    try:
        return await get_home_assistant_history(entity_ids, hours, max_points)
    except (RuntimeError, PermissionError, ValueError, httpx.HTTPError) as exc:
        raise HTTPException(status_code=400 if isinstance(exc, (PermissionError, ValueError)) else 502, detail=str(exc)) from exc


@app.get("/api/ha/timeline")
async def api_home_assistant_timeline(entity_ids: str, hours: int = 24, query: str = "", limit: int = 160) -> dict[str, Any]:
    try:
        return await correlate_home_assistant_timeline(entity_ids, hours, query, limit)
    except (RuntimeError, PermissionError, ValueError, httpx.HTTPError) as exc:
        raise HTTPException(status_code=400 if isinstance(exc, (PermissionError, ValueError)) else 502, detail=str(exc)) from exc


@app.get("/api/ha/logbook")
async def api_home_assistant_logbook(entity_ids: str, hours: int = 24, query: str = "", limit: int = 160) -> dict[str, Any]:
    try:
        return await search_home_assistant_logbook(entity_ids, hours, query, limit)
    except (RuntimeError, PermissionError, ValueError, httpx.HTTPError) as exc:
        raise HTTPException(status_code=400 if isinstance(exc, (PermissionError, ValueError)) else 502, detail=str(exc)) from exc


@app.get("/api/ha/entities")
async def list_ha_entities(refresh: bool = False) -> dict[str, Any]:
    """Return normalized Home Assistant entity inventory with WS-first discovery."""
    if not SUPERVISOR_TOKEN:
        raise HTTPException(status_code=503, detail="Home Assistant API token unavailable")

    raw_states: list[dict[str, Any]] = []
    inventory_source = "none"
    diagnostics: dict[str, Any] = {
        "websocket_connected": ha_ws.connected,
        "websocket_cached_entities": len(ha_ws.state_cache),
        "websocket_error": ha_ws.last_error,
        "rest_error": None,
    }

    try:
        if not ha_ws.connected:
            await ha_ws.connect()
        if ha_ws.state_cache:
            raw_states = list(ha_ws.state_cache.values())
            inventory_source = "websocket"
    except Exception as exc:
        diagnostics["websocket_error"] = str(exc)

    if not raw_states:
        headers = {
            "Authorization": f"Bearer {SUPERVISOR_TOKEN}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(f"{HA_API_BASE}/states", headers=headers)
            if response.is_error:
                diagnostics["rest_error"] = f"HTTP {response.status_code}"
            else:
                payload = response.json()
                if isinstance(payload, list):
                    raw_states = [item for item in payload if isinstance(item, dict)]
                    inventory_source = "rest"
                else:
                    diagnostics["rest_error"] = "Home Assistant states response was not a list"
        except Exception as exc:
            diagnostics["rest_error"] = str(exc)

    if not raw_states:
        detail = "Home Assistant returned no entity inventory"
        errors = [
            value for value in (diagnostics.get("websocket_error"), diagnostics.get("rest_error"))
            if value
        ]
        if errors:
            detail += ": " + " | ".join(errors)
        raise HTTPException(status_code=502, detail=detail)

    try:
        area_context = await _automation_refresh_area_context(force=bool(refresh))
    except (RuntimeError, OSError, asyncio.TimeoutError):
        area_context = automation_store().get("area_context") or {}
    area_entities = {
        str(item.get("entity_id") or ""): item
        for item in area_context.get("entities", []) if isinstance(item, dict)
    }

    entities: list[dict[str, Any]] = []
    for item in raw_states:
        entity_id = item.get("entity_id", "")
        if "." not in entity_id:
            continue
        domain = entity_id.split(".", 1)[0]
        attributes = item.get("attributes") or {}
        state = item.get("state")
        device_class = attributes.get("device_class")
        friendly_name = attributes.get("friendly_name") or entity_id
        risk = classify_entity_risk(
            domain,
            device_class,
            entity_id=entity_id,
            friendly_name=friendly_name,
        )
        area = area_entities.get(entity_id) or {}
        entities.append({
            "entity_id": entity_id,
            "friendly_name": friendly_name,
            "domain": domain,
            "state": state,
            "available": state not in {"unavailable", "unknown", None},
            "device_class": device_class,
            "unit": attributes.get("unit_of_measurement"),
            "icon": attributes.get("icon"),
            "risk": risk,
            "auto_approved": risk == "low_risk_control_proposed",
            "last_changed": item.get("last_changed"),
            "last_updated": item.get("last_updated"),
            "area_id": area.get("area_id") or "",
            "area_name": area.get("area_name") or "",
            "area_source": area.get("area_source") or "unassigned",
            "zbrano_role": area.get("role") or _automation_entity_role(entity_id, attributes),
            "labels": area.get("labels") or [],
            "site_label": area.get("site_label") or "",
            "site_name": area.get("site_name") or "",
            "zone_entity_id": area.get("zone_entity_id") or "",
        })

    policy = load_entity_policy()
    policy_changed = False
    for entity in entities:
        if not entity["auto_approved"]:
            continue
        existing = policy.get(entity["entity_id"], {})
        updated = {
            **existing,
            "enabled": True,
            "friendly_name": entity["friendly_name"],
            "domain": entity["domain"],
            "device_class": entity["device_class"],
            "unit": entity["unit"],
            "access": "low_risk_control_proposed",
            "aliases": existing.get("aliases", []),
            "auto_approved": True,
        }
        if existing != updated:
            policy[entity["entity_id"]] = updated
            policy_changed = True
    if policy_changed:
        save_entity_policy(policy)

    entities.sort(key=lambda entity: (
        str(entity.get("domain", "")).lower(),
        str(entity.get("friendly_name", "")).lower(),
        str(entity.get("entity_id", "")).lower(),
    ))
    domains = sorted({entity["domain"] for entity in entities})
    diagnostics["websocket_connected"] = ha_ws.connected
    diagnostics["websocket_cached_entities"] = len(ha_ws.state_cache)
    diagnostics["websocket_error"] = ha_ws.last_error or diagnostics.get("websocket_error")
    return {
        "count": len(entities),
        "domains": domains,
        "entities": entities,
        "source": inventory_source,
        "diagnostics": diagnostics,
        "note": "States are live Home Assistant data. Only stable metadata should later be proposed for Workshop Memory.",
    }

@app.post("/api/memory/entity-catalog-draft")
async def prepare_entity_catalog_draft(
    request: EntityCatalogDraftRequest,
) -> dict[str, Any]:
    """Prepare a reviewable inventory without bypassing Workshop Memory approval."""
    markdown = entity_catalog_markdown(request.entities)
    return {
        "prepared": True,
        "saved": False,
        "project": request.project,
        "entity_count": len(request.entities),
        "catalog_markdown": markdown,
        "filename": "HA OS Entities Update Draft.md",
        "permanent_project_notes_changed": False,
        "review_required": True,
        "next_step": "Attach this draft in chat and ask ZBRANO to reconcile it with the existing Workshop Memory entity note.",
    }


@app.get("/api/ha/states/{entity_id}")
async def get_ha_state(entity_id: str) -> dict[str, Any]:
    if not SUPERVISOR_TOKEN:
        raise HTTPException(status_code=503, detail="Home Assistant API token unavailable")

    headers = {
        "Authorization": f"Bearer {SUPERVISOR_TOKEN}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{HA_API_BASE}/states/{entity_id}", headers=headers)

    if response.status_code == 404:
        raise HTTPException(status_code=404, detail="Entity not found")
    if response.is_error:
        raise HTTPException(
            status_code=502,
            detail=f"Home Assistant returned HTTP {response.status_code}",
        )
    return response.json()


async def _transcribe_voice_upload(audio: UploadFile, *, wake: bool = False) -> dict[str, str]:
    """Transcribe one bounded browser recording without retaining audio or exposing the API key."""
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="OpenAI API key is not configured")

    content_type = (audio.content_type or "application/octet-stream").lower()
    if not (content_type.startswith("audio/") or content_type == "video/webm"):
        raise HTTPException(status_code=415, detail="Unsupported microphone recording format")

    audio_bytes = await audio.read(VOICE_UPLOAD_MAX_BYTES + 1)
    await audio.close()
    minimum_bytes = 2500 if wake else 1
    if len(audio_bytes) < minimum_bytes:
        raise HTTPException(status_code=422 if wake else 400, detail="No clear speech was detected")
    if len(audio_bytes) > VOICE_UPLOAD_MAX_BYTES:
        raise HTTPException(status_code=413, detail="Microphone recording is too large")

    filename = audio.filename or ("zbrano-wake.webm" if wake else "zbrano-recording.webm")
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    files = {"file": (filename, audio_bytes, content_type)}
    data = {"model": OPENAI_TRANSCRIPTION_MODEL, "response_format": "json", "temperature": "0"}
    if not wake:
        data["prompt"] = "ZBRANO workshop assistant. Preserve Home Assistant entity names and commands."
    async with httpx.AsyncClient(timeout=httpx.Timeout(90.0, connect=10.0)) as client:
        response = await client.post(OPENAI_TRANSCRIPTIONS_URL, headers=headers, data=data, files=files)
    if response.is_error:
        raise HTTPException(status_code=502, detail=f"Voice transcription failed: {openai_error_message(response)}")

    text = str(response.json().get("text") or "").strip()
    normalized = " ".join(re.sub(r"[^a-z0-9]+", " ", text.lower()).split())
    wake_characters = re.sub(r"[^a-z0-9\u0370-\u03ff]+", "", text.lower())
    silence_hallucinations = {
        "zbrano workshop intelligence core assistant", "zbrano workshop assistant",
        "jarvis workshop assistant", "workshop intelligence core assistant",
        "thank you", "thanks for watching",
    }
    if not text or (wake and (not wake_characters or normalized in silence_hallucinations)):
        raise HTTPException(status_code=422, detail="No clear speech was detected")
    return {"text": text, "model": OPENAI_TRANSCRIPTION_MODEL}


@app.post("/api/voice/transcribe")
async def transcribe_voice(audio: UploadFile = File(...)) -> dict[str, str]:
    """Transcribe a deliberate Talk-button recording."""
    return await _transcribe_voice_upload(audio)


@app.post("/api/voice/wake-transcribe")
async def transcribe_wake_voice(audio: UploadFile = File(...)) -> dict[str, str]:
    """Transcribe a voice-activity-gated wake utterance without assistant-name prompting."""
    return await _transcribe_voice_upload(audio, wake=True)


@app.websocket("/api/voice/wake-shadow")
async def wake_shadow_websocket(websocket: WebSocket) -> None:
    """Score transient 16 kHz PCM frames locally; never retain audio; browser activation is explicitly optional."""
    await websocket.accept()
    try:
        model, np, verifier_enabled = await asyncio.to_thread(_new_wake_shadow_model)
        model_name = next(iter(model.models.keys()), "hey_zbrano")
        await websocket.send_json({"type": "ready", "model": model_name, "verifier": verifier_enabled})
        while True:
            packet = await websocket.receive_bytes()
            if not packet or len(packet) > 32768 or len(packet) % 2:
                continue
            samples = np.frombuffer(packet, dtype=np.int16)
            prediction = await asyncio.to_thread(model.predict, samples)
            score = max((float(value) for value in prediction.values()), default=0.0)
            await websocket.send_json({"type": "score", "score": max(0.0, min(1.0, score))})
    except WebSocketDisconnect:
        return
    except Exception as exc:
        with contextlib.suppress(Exception):
            await websocket.send_json({"type": "error", "message": str(exc)})
    finally:
        with contextlib.suppress(Exception):
            await websocket.close()


@app.get("/api/voice/wake-calibration")
async def get_wake_calibration() -> dict[str, Any]:
    return _wake_calibration_status()


@app.post("/api/voice/wake-calibration/samples/{label}")
async def save_wake_calibration(label: str, audio: UploadFile = File(...)) -> dict[str, Any]:
    """Save one explicitly requested local calibration clip as bounded PCM WAV."""
    import io
    import time
    import wave

    destination = {"positive": WAKE_POSITIVE_DIR, "negative": WAKE_NEGATIVE_DIR}.get(label)
    if destination is None:
        raise HTTPException(status_code=400, detail="Calibration label must be positive or negative")
    content = await audio.read(256001)
    await audio.close()
    if len(content) > 256000:
        raise HTTPException(status_code=413, detail="Wake calibration clip is too large")
    try:
        with wave.open(io.BytesIO(content), "rb") as clip:
            valid = (
                clip.getnchannels() == 1
                and clip.getsampwidth() == 2
                and clip.getframerate() == 16000
                and 16000 <= clip.getnframes() <= 80000
                and clip.getcomptype() == "NONE"
            )
    except (EOFError, wave.Error):
        valid = False
    if not valid:
        raise HTTPException(status_code=422, detail="Expected 1–5 seconds of mono 16 kHz 16-bit PCM WAV audio")
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / f"{time.time_ns()}.wav"
    target.write_bytes(content)
    quality = _wake_clip_quality(target)
    if not quality.get("valid"):
        target.unlink(missing_ok=True)
        raise HTTPException(
            status_code=422,
            detail=f"Recording rejected: RMS {quality.get('rms', 0):.4f}, peak {quality.get('peak', 0):.4f}. Speak once after the recorder says it is armed.",
        )
    return {"saved": True, "quality": quality, **_wake_calibration_status()}


@app.post("/api/voice/wake-calibration/train")
async def train_wake_calibration() -> dict[str, Any]:
    async with WAKE_VERIFIER_TRAIN_LOCK:
        try:
            await asyncio.to_thread(_train_personal_wake_verifier)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Personal wake verifier training failed: {exc}") from exc
    return {"trained": True, **_wake_calibration_status()}


@app.delete("/api/voice/wake-calibration/invalid")
async def delete_invalid_wake_calibration() -> dict[str, Any]:
    removed = 0
    for directory in (WAKE_POSITIVE_DIR, WAKE_NEGATIVE_DIR):
        if not directory.is_dir():
            continue
        for clip in directory.glob("*.wav"):
            if not _wake_clip_quality(clip).get("valid"):
                clip.unlink(missing_ok=True)
                removed += 1
    return {"removed": removed, **_wake_calibration_status()}


@app.get("/api/voice/wake-calibration/export")
async def export_wake_calibration() -> Response:
    """Export only operator-recorded wake calibration WAV files for offline retraining."""
    import io
    import json
    import zipfile

    archive_buffer = io.BytesIO()
    counts = {"positive": 0, "negative": 0}
    with zipfile.ZipFile(archive_buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for label, directory in (("positive", WAKE_POSITIVE_DIR), ("negative", WAKE_NEGATIVE_DIR)):
            if not directory.is_dir():
                continue
            valid_index = 0
            for clip in sorted(directory.glob("*.wav")):
                if not _wake_clip_quality(clip).get("valid"):
                    continue
                valid_index += 1
                archive.write(clip, f"{label}/{label}_{valid_index:03d}.wav")
                counts[label] += 1
        archive.writestr(
            "manifest.json",
            json.dumps({"wake_phrase": "Hey ZBRANO", "sample_rate_hz": 16000, "format": "mono PCM WAV", "counts": counts}, indent=2),
        )
    return Response(
        content=archive_buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="zbrano-wake-calibration.zip"'},
    )


@app.put("/api/voice/wake-calibration/verifier")
async def set_wake_verifier_enabled(enabled: bool) -> dict[str, Any]:
    if enabled and not WAKE_VERIFIER_PATH.is_file():
        raise HTTPException(status_code=409, detail="Train the personal verifier before enabling it")
    WAKE_CALIBRATION_DIR.mkdir(parents=True, exist_ok=True)
    if enabled:
        WAKE_VERIFIER_ENABLED_PATH.write_text("enabled\n", encoding="utf-8")
    else:
        WAKE_VERIFIER_ENABLED_PATH.unlink(missing_ok=True)
    return _wake_calibration_status()


@app.delete("/api/voice/wake-calibration/verifier")
async def delete_wake_verifier() -> dict[str, Any]:
    WAKE_VERIFIER_ENABLED_PATH.unlink(missing_ok=True)
    WAKE_VERIFIER_PATH.unlink(missing_ok=True)
    return {"deleted": True, **_wake_calibration_status()}


@app.delete("/api/voice/wake-calibration")
async def reset_wake_calibration() -> dict[str, Any]:
    """Delete only ZBRANO-owned calibration clips and verifier after UI confirmation."""
    for directory in (WAKE_POSITIVE_DIR, WAKE_NEGATIVE_DIR):
        if directory.is_dir():
            for clip in directory.glob("*.wav"):
                clip.unlink(missing_ok=True)
    WAKE_VERIFIER_ENABLED_PATH.unlink(missing_ok=True)
    WAKE_VERIFIER_PATH.unlink(missing_ok=True)
    return {"reset": True, **_wake_calibration_status()}


@app.post("/api/voice/speech")
async def generate_speech(request: SpeechRequest) -> Response:
    """Generate AI speech for playback on the browser device that requested it."""
    provider = SPEECH_PROVIDER if request.provider == "default" else request.provider
    preferences = load_preferences()
    speech_text = apply_pronunciation_dictionary(request.text)
    if provider not in {"openai", "elevenlabs"}:
        provider = "openai"

    if provider == "elevenlabs":
        if not ELEVENLABS_API_KEY or not ELEVENLABS_VOICE_ID:
            raise HTTPException(
                status_code=503,
                detail="ElevenLabs API key and voice ID are not configured",
            )
        headers = {
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }
        voice_settings = load_elevenlabs_voice_settings()
        payload = {
            "text": speech_text,
            "model_id": preferences["elevenlabs_model"],
            "voice_settings": {
                "stability": voice_settings["stability"],
                "similarity_boost": voice_settings["similarity"],
                "style": voice_settings["style"],
                "use_speaker_boost": preferences["elevenlabs_speaker_boost"],
                "speed": voice_settings["speed"],
            },
        }
        response = None
        client = httpx.AsyncClient(timeout=httpx.Timeout(90.0, connect=10.0))
        try:
            upstream_request = client.build_request(
                "POST",
                f"{ELEVENLABS_SPEECH_URL}/{ELEVENLABS_VOICE_ID}/stream",
                params={"output_format": "mp3_22050_32", "optimize_streaming_latency": "4"},
                headers=headers,
                json=payload,
            )
            response = await client.send(upstream_request, stream=True)
        except httpx.HTTPError:
            await client.aclose()
        if response is not None and not response.is_error:
            async def relay_elevenlabs_audio() -> AsyncIterator[bytes]:
                try:
                    async for chunk in response.aiter_bytes():
                        if chunk:
                            yield chunk
                finally:
                    await response.aclose()
                    await client.aclose()

            return StreamingResponse(
                relay_elevenlabs_audio(),
                media_type="audio/mpeg",
                headers={
                    "Cache-Control": "no-store",
                    "X-ZBRANO-Voice": ELEVENLABS_VOICE_NAME,
                    "X-ZBRANO-Speech-Provider": "elevenlabs",
                },
            )
        if response is not None:
            await response.aread()
            await response.aclose()
            await client.aclose()
        if not (SPEECH_FALLBACK_TO_OPENAI and OPENAI_API_KEY):
            detail = "ElevenLabs speech generation failed"
            with contextlib.suppress(ValueError, TypeError, AttributeError):
                error_data = response.json()
                provider_detail = error_data.get("detail")
                if isinstance(provider_detail, dict):
                    detail = str(provider_detail.get("message") or detail)
                elif provider_detail:
                    detail = str(provider_detail)
            raise HTTPException(status_code=502, detail=detail)

    if not OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="OpenAI API key is not configured")
    voice = request.voice.lower().strip()
    if voice not in TTS_VOICES:
        voice = "cedar" if provider == "elevenlabs" else voice
    if voice not in TTS_VOICES:
        raise HTTPException(status_code=400, detail="Unsupported ZBRANO voice")

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": OPENAI_TTS_MODEL,
        "voice": voice,
        "input": speech_text,
        "instructions": (
            "Speak as a calm, concise workshop AI assistant. Use a measured pace "
            "and clear pronunciation. Do not add words that are not in the input."
        ),
        "response_format": "mp3",
    }
    response = None
    client = httpx.AsyncClient(timeout=httpx.Timeout(90.0, connect=10.0))
    try:
        upstream_request = client.build_request(
            "POST",
            OPENAI_SPEECH_URL,
            headers=headers,
            json=payload,
        )
        response = await client.send(upstream_request, stream=True)
    except httpx.HTTPError:
        await client.aclose()
        raise
    if response.is_error:
        await response.aread()
        await response.aclose()
        await client.aclose()
        raise HTTPException(
            status_code=502,
            detail=f"Speech generation failed: {openai_error_message(response)}",
        )

    async def relay_openai_audio() -> AsyncIterator[bytes]:
        try:
            async for chunk in response.aiter_bytes():
                if chunk:
                    yield chunk
        finally:
            await response.aclose()
            await client.aclose()

    return StreamingResponse(
        relay_openai_audio(),
        media_type="audio/mpeg",
        headers={
            "Cache-Control": "no-store",
            "X-ZBRANO-Voice": voice,
            "X-ZBRANO-Speech-Provider": "openai",
        },
    )


@app.post("/api/chat")
async def chat(request: ChatRequest) -> dict[str, Any]:
    try:
        return await run_jarvis(request.message, request.session_id)
    except (OpenAIError, MCPError, httpx.HTTPError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/{path:path}", include_in_schema=False)
async def frontend(path: str = "") -> FileResponse:
    candidate = STATIC_DIR / path
    if path and candidate.is_file():
        return FileResponse(
            candidate,
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )
    return FileResponse(
        STATIC_DIR / "index.html",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
            "X-ZBRANO-Frontend-Version": "0.12.76",
        },
    )


async def _install_github_device_plugin(name: str, url: str, bearer_token: str) -> dict[str, Any]:
    return await install_plugin(PluginInstallRequest(name=name, url=url, bearer_token=bearer_token))


configure_automation_intents(
    workshop_tools=WORKSHOP_TOOLS,
    entity_memory_context_fn=automation_entity_memory_context,
    brain_memory_context_fn=automation_brain_memory_context,
)
configure_home_assistant_intents(
    workshop_tools=WORKSHOP_TOOLS,
)
configure_calendar_intents(
    workshop_tools=WORKSHOP_TOOLS,
)
configure_grinder_intents(
    grinder_monitor_tools=GRINDER_MONITOR_TOOLS,
)
configure_fast_memory_intents(
    workshop_tools=WORKSHOP_TOOLS,
)
configure_developer_tools(
    developer_mode_enabled_fn=developer_mode_enabled,
)
configure_runtime_routing(
    developer_mode_enabled_fn=developer_mode_enabled,
    developer_system_instructions_fn=developer_system_instructions,
    is_ha_history_fn=is_home_assistant_history_intent,
    ha_history_instructions_fn=home_assistant_history_system_instructions,
    is_automation_fn=is_automation_intent,
    automation_instructions_fn=automation_system_instructions,
    calendar_instructions_fn=calendar_system_instructions,
    is_grinder_fn=is_grinder_diagnostic_intent,
    grinder_instructions_fn=grinder_system_instructions,
    is_ha_priority_fn=is_home_assistant_priority_intent,
    developer_tools_fn=developer_runtime_tools,
    developer_mcp_tools_fn=developer_mcp_tools,
    grinder_tools_fn=grinder_priority_tools,
    is_fast_memory_fn=is_fast_memory_intent,
    fast_memory_tools_fn=fast_memory_priority_tools,
    automation_tools_fn=automation_priority_tools,
    is_calendar_fn=is_calendar_intent,
    calendar_tools_fn=calendar_priority_tools,
    ha_history_tools_fn=home_assistant_history_tools,
    ha_priority_tools_fn=home_assistant_priority_tools,
    default_tools_fn=lambda: WORKSHOP_TOOLS + GRINDER_MONITOR_TOOLS + workshop_memory_function_tools() + gmail_direct_function_tools() + active_mcp_tools(),
    native_web_search_tool_fn=native_web_search_tool,
)
configure_workshop_approvals(
    tool_permission_fn=workshop_memory_tool_permission,
    gmail_write_calls_fn=gmail_direct_write_calls,
)
configure_mcp_approvals(
    plugin_registry_fn=plugin_registry,
)
configure_tool_progress(
    gmail_direct_tool_names=GMAIL_DIRECT_TOOL_NAMES,
    gmail_plugin_id_fn=_gmail_plugin_id,
)
configure_plugin_presentation(
    plugin_secrets_fn=plugin_secrets,
    plugin_oauth_records_fn=plugin_oauth_records,
    oauth_scope_set_fn=_oauth_scope_set,
)
configure_plugin_discovery(
    timeout=PLUGIN_TIMEOUT,
)
configure_plugin_catalog_service(
    plugin_load_fn=_plugin_load,
    plugin_save_fn=_plugin_save,
    validate_plugin_url_fn=validate_plugin_url,
    plugin_icon_url_fn=plugin_icon_url,
    plugin_registry_fn=plugin_registry,
    plugin_url_key_fn=_plugin_url_key,
    gmail_plugin_id_fn=_gmail_plugin_id,
    google_calendar_plugin_id_fn=_google_calendar_plugin_id,
    github_oauth_client_id_fn=_github_oauth_client_id,
)
configure_github_device_oauth(
    timeout=PLUGIN_TIMEOUT,
    catalog_entry_fn=_catalog_entry,
    install_plugin_fn=_install_github_device_plugin,
)
configure_plugin_oauth_service(
    plugin_load_fn=_plugin_load,
    validate_plugin_url_fn=validate_plugin_url,
    timeout=PLUGIN_TIMEOUT,
    runtime_version=app.version,
)
configure_google_oauth_service(
    timeout=PLUGIN_TIMEOUT,
    gmail_scopes=GMAIL_MCP_OAUTH_SCOPES,
    calendar_scopes=GOOGLE_CALENDAR_OAUTH_SCOPES,
    gmail_plugin_id_fn=_gmail_plugin_id,
    oauth_records_fn=plugin_oauth_records,
    oauth_scope_set_fn=_oauth_scope_set,
    oauth_safe_json_fn=_oauth_safe_json,
    oauth_validate_url_fn=_oauth_validate_https_url,
    plugin_registry_fn=plugin_registry,
    plugin_secrets_fn=plugin_secrets,
    plugin_save_fn=_plugin_save,
    gmail_tool_records_fn=gmail_direct_tool_records,
    registry_path=PLUGIN_REGISTRY_PATH,
    secrets_path=PLUGIN_SECRETS_PATH,
    oauth_path=PLUGIN_OAUTH_PATH,
)
configure_agent_runtime(
    openai_model=OPENAI_MODEL,
    chat_context_max_messages=CHAT_CONTEXT_MAX_MESSAGES,
    base_system_instructions=BASE_SYSTEM_INSTRUCTIONS,
    load_preferences_fn=load_preferences,
    load_general_instructions_fn=load_general_instructions,
)
configure_tab_activity_service(
    automation_store_fn=automation_store,
    list_files_fn=list_files,
    shared_file_root=SHARED_FILE_ROOT,
    revision_paths={
        "chat": CHAT_STORAGE_PATH,
        "plugins": PLUGIN_REGISTRY_PATH,
        "oauth": PLUGIN_OAUTH_PATH,
        "notifications": NOTIFICATION_STORAGE_PATH,
        "calendar": CALENDAR_STORAGE_PATH,
        "settings": SETTINGS_STORAGE_PATH,
        "developer": DEVELOPER_STATE_PATH,
    },
)
configure_conversations_domain(
    load_preferences_fn=load_preferences,
    chat_context_limit_fn=chat_context_limit,
    schedule_fast_memory_extraction_fn=schedule_fast_memory_extraction,
    clear_chat_files_fn=clear_chat_files,
)
configure_playwright_bridge(
    developer_mode_enabled_fn=developer_mode_enabled,
    mcp_response_json_fn=_mcp_response_json,
    runtime_version=app.version,
)
configure_web_search_service(
    developer_mode_enabled_fn=developer_mode_enabled,
    load_preferences_fn=load_preferences,
)
configure_openai_responses(
    api_key=OPENAI_API_KEY,
    responses_url=OPENAI_RESPONSES_URL,
)
configure_gmail_direct_domain(
    plugin_registry_fn=plugin_registry,
    plugin_secrets_fn=plugin_secrets,
    plugin_oauth_records_fn=plugin_oauth_records,
    oauth_scope_set_fn=_oauth_scope_set,
    refresh_plugin_oauth_token_fn=_refresh_plugin_oauth_token,
)
configure_telegram_inbound_domain(
    plugin_load_fn=_plugin_load,
    plugin_save_fn=_plugin_save,
    ha_client=ha_ws,
    notification_store_fn=notification_store,
    notification_test_fn=test_notification_channel,
    run_jarvis_fn=run_jarvis,
    supervisor_token=SUPERVISOR_TOKEN,
    ha_ws_url=HA_WS_URL,
)
configure_release_sync_domain(
    runtime_version=app.version,
    load_preferences_fn=load_preferences,
    call_tool_fn=call_workshop_memory_tool,
    call_uncached_fn=call_workshop_memory_tool_uncached,
    workshop_result_error_fn=workshop_result_error,
)
configure_google_calendar_domain(
    plugin_load=_plugin_load,
    plugin_save=_plugin_save,
    calendar_store_fn=calendar_store,
    calendar_save_fn=_calendar_save,
    oauth_records_fn=plugin_oauth_records,
    plugin_secrets_fn=plugin_secrets,
    oauth_scope_set_fn=_oauth_scope_set,
    refresh_oauth_token_fn=_refresh_plugin_oauth_token,
    plugin_registry_fn=plugin_registry,
    sync_task_provider=lambda: GOOGLE_CALENDAR_SYNC_TASK,
)
configure_fast_memory_domain(
    load_preferences_fn=load_preferences,
    is_internal_chat_session_fn=is_internal_chat_session,
    active_agent_model_fn=active_agent_model,
    create_openai_response_fn=create_openai_response,
    function_calls_fn=function_calls,
)
configure_workshop_memory_domain(
    internal_url=WORKSHOP_MEMORY_INTERNAL_URL,
    external_url=WORKSHOP_MEMORY_URL,
    static_tool_names={str(tool.get("name") or "") for tool in WORKSHOP_TOOLS},
    direct_tool_names=GMAIL_DIRECT_TOOL_NAMES,
    direct_write_tools=GMAIL_DIRECT_WRITE_TOOLS,
)
configure_calendar_domain(
    plugin_load=_plugin_load,
    plugin_save=_plugin_save,
    notification_store_fn=notification_store,
    notification_channels_fn=notification_channels,
    google_sync_store_fn=google_calendar_sync_store,
    notification_quiet_now_fn=_notification_quiet_now,
    notification_test_fn=test_notification_channel,
)
configure_notification_domain(
    plugin_load=_plugin_load,
    plugin_save=_plugin_save,
    entity_lister=list_ha_entities,
    ha_client=ha_ws,
    automation_store_fn=automation_store,
    automation_event_fn=_automation_event,
    automation_save_fn=_automation_save,
    notification_test_fn=test_notification_channel,
    supervisor_token=SUPERVISOR_TOKEN,
)
configure_entity_policy_service(
    automation_store_fn=automation_store,
)
configure_ha_control_service(
    ha_client=ha_ws,
    supervisor_token=SUPERVISOR_TOKEN,
    ha_api_base=HA_API_BASE,
    ensure_read_allowed_fn=ensure_read_allowed,
    ensure_control_allowed_fn=ensure_control_allowed,
)
configure_ha_history_service(
    supervisor_token=SUPERVISOR_TOKEN,
    ha_api_base=HA_API_BASE,
    ensure_read_allowed_fn=ensure_read_allowed,
    effective_entity_access_fn=effective_entity_access,
    ha_get_state_fn=ha_get_state,
    automation_evaluate_fn=_automation_evaluate_state_change,
    automation_learn_fn=_automation_brain_state_change,
)
configure_automation_domain(
    plugin_load=_plugin_load,
    plugin_save=_plugin_save,
    search_tokens=_search_tokens,
    live_events=HA_LIVE_EVENTS,
    pending_confirmations=PENDING_AUTOMATION_CONFIRMATIONS,
    entity_domain_fn=entity_domain,
    effective_entity_access_fn=effective_entity_access,
    ensure_control_allowed_fn=ensure_control_allowed,
    ensure_read_allowed_fn=ensure_read_allowed,
    ha_client=ha_ws,
    entity_policy_loader=load_entity_policy,
    notification_store_fn=notification_store,
    notification_quiet_now_fn=_notification_quiet_now,
    notification_test_fn=test_notification_channel,
)
