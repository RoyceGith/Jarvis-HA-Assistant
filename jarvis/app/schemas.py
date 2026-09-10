from __future__ import annotations

import os
from typing import Any

from pydantic import BaseModel, Field


GENERAL_INSTRUCTIONS_MAX_CHARS = 12000
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")


class ChatRequest(BaseModel):
    session_id: str = Field(default="default", min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=4000)
    attachment_ids: list[str] = Field(default_factory=list, max_length=20)
    search_mode: str = Field(default="auto", pattern="^(auto|search|off)$")

class ChatSessionCreate(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)

class ChatRenameRequest(BaseModel):
    title: str = Field(min_length=1, max_length=100)

class JarvisSettingsUpdate(BaseModel):
    general_instructions: str = Field(default="", max_length=GENERAL_INSTRUCTIONS_MAX_CHARS)
    elevenlabs_stability: float = Field(default=0.55, ge=0.0, le=1.0)
    elevenlabs_similarity: float = Field(default=0.75, ge=0.0, le=1.0)
    elevenlabs_style: float = Field(default=0.15, ge=0.0, le=1.0)
    elevenlabs_speed: float = Field(default=0.96, ge=0.7, le=1.2)
    elevenlabs_model: str = Field(default="eleven_flash_v2_5")
    elevenlabs_speaker_boost: bool = False
    agent_model: str = Field(default=OPENAI_MODEL, min_length=1, max_length=120)
    reasoning_effort: str = Field(default="medium", pattern="^(none|minimal|low|medium|high|xhigh)$")
    auto_speak: bool = True
    proactive_voice_enabled: bool = True
    voice_approval_enabled: bool = True
    wake_word_enabled: bool = False
    wake_phrase: str = Field(default="hey zbrano", min_length=2, max_length=40)
    response_length: str = Field(default="balanced", pattern="^(brief|balanced|detailed)$")
    confirmation_strictness: str = Field(default="standard", pattern="^(standard|cautious)$")
    context_messages: int = Field(default=20, ge=4, le=50)
    retention_days: int = Field(default=90, ge=0, le=365)
    preferred_language: str = Field(default="auto", min_length=2, max_length=40)
    pronunciation_dictionary: str = Field(default="", max_length=8000)
    theme: str = Field(default="dark", pattern="^(dark|light|gray)$")
    neural_style: str = Field(default="constellation", pattern="^(constellation|mesh|orbital|minimal)$")
    neural_scale: float = Field(default=1.0, ge=0.7, le=1.4)
    neural_node_size: float = Field(default=1.0, ge=0.6, le=1.6)
    neural_opacity: float = Field(default=0.38, ge=0.05, le=0.8)
    reduced_motion: bool = False
    text_size: str = Field(default="medium", pattern="^(small|medium|large)$")
    interface_density: str = Field(default="comfortable", pattern="^(compact|comfortable)$")
    quiet_hours_enabled: bool = False
    quiet_hours_start: str = Field(default="22:00", pattern="^([01]\\d|2[0-3]):[0-5]\\d$")
    quiet_hours_end: str = Field(default="07:00", pattern="^([01]\\d|2[0-3]):[0-5]\\d$")
    voice_volume: float = Field(default=0.9, ge=0.0, le=1.0)
    auto_sync_releases_to_workshop_memory: bool = True
    web_search_enabled: bool = True
    web_search_context_size: str = Field(default="medium", pattern="^(low|medium|high)$")
    fast_memory_enabled: bool = True
    fast_memory_auto_capture: bool = True
    fast_memory_context_items: int = Field(default=10, ge=2, le=20)

class InterfaceLanguageUpdate(BaseModel):
    interface_language: str = Field(pattern="^(auto|English|Greek|Italian|French)$")

class OnboardingStateUpdate(BaseModel):
    action: str = Field(pattern="^(complete|dismiss)$")

class OnboardingProgressUpdate(BaseModel):
    step_id: str = Field(pattern="^(home_assistant|model|entities|voice|memory|plugins|notifications)$")
    skipped_step: str | None = Field(
        default=None,
        pattern="^(entities|voice|memory|plugins|notifications)$",
    )

class AgentSettingsUpdate(BaseModel):
    agent_model: str = Field(min_length=1, max_length=120)
    reasoning_effort: str = Field(default="medium", pattern="^(none|minimal|low|medium|high|xhigh)$")

class CatalogInstallRequest(BaseModel):
    bearer_token: str = Field(default="", max_length=4000)

class PluginOAuthStartRequest(BaseModel):
    redirect_uri: str = Field(min_length=12, max_length=1000)

class PluginInstallRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    url: str = Field(min_length=8, max_length=500)
    bearer_token: str = Field(default="", max_length=4000)

class PluginToolUpdate(BaseModel):
    enabled: bool = False
    permission: str = Field(default="blocked", pattern="^(blocked|read_only|write)$")

class AutonomySettingsRequest(BaseModel):
    operating_mode: str = Field(default="suggest_only", pattern="^(observe_only|suggest_only|approval_gated|selective_autonomy)$")
    presence_entity: str = Field(default="", max_length=255)
    require_presence: bool = True
    respect_quiet_hours: bool = True
    minimum_confidence: float = Field(default=0.75, ge=0.5, le=0.99)
    default_cooldown_minutes: int = Field(default=30, ge=1, le=1440)
    autonomous_risk_ceiling: str = Field(default="low", pattern="^(informational|low|controlled)$")
    notify_after_autonomous_action: bool = True
    passive_learning_enabled: bool = True

class AutomationTriggerRequest(BaseModel):
    kind: str = Field(default="entity", pattern="^(entity|time|sun|interval|one_time)$")
    entity_id: str = Field(default="", max_length=255, pattern=r"^(|[a-z0-9_]+\.[a-z0-9_]+)$")
    operator: str = Field(default="changes_to", pattern="^(any_change|changes_to|equals|not_equals|above|below)$")
    value: str = Field(default="", max_length=255)
    for_seconds: int = Field(default=0, ge=0, le=86400)
    at: str = Field(default="", pattern=r"^(|([01]\d|2[0-3]):[0-5]\d)$")
    weekdays: list[int] = Field(default_factory=list, max_length=7)
    sun_event: str = Field(default="sunrise", pattern="^(sunrise|sunset)$")
    offset_minutes: int = Field(default=0, ge=-180, le=180)
    interval_minutes: int = Field(default=5, ge=1, le=10080)
    one_time_at: str = Field(default="", max_length=64)

class AutomationConditionRequest(BaseModel):
    kind: str = Field(default="entity", pattern="^(entity|entity_compare|time_window|weekday|sun)$")
    entity_id: str = Field(default="", max_length=255, pattern=r"^(|[a-z0-9_]+\.[a-z0-9_]+)$")
    attribute: str = Field(default="", max_length=120, pattern=r"^[a-zA-Z0-9_.-]*$")
    operator: str = Field(default="equals", pattern="^(equals|not_equals|above|below)$")
    value: str = Field(default="", max_length=255)
    compare_entity_id: str = Field(default="", max_length=255, pattern=r"^(|[a-z0-9_]+\.[a-z0-9_]+)$")
    compare_attribute: str = Field(default="", max_length=120, pattern=r"^[a-zA-Z0-9_.-]*$")
    for_seconds: int = Field(default=0, ge=0, le=86400)
    start_time: str = Field(default="", pattern=r"^(|([01]\d|2[0-3]):[0-5]\d)$")
    end_time: str = Field(default="", pattern=r"^(|([01]\d|2[0-3]):[0-5]\d)$")
    weekdays: list[int] = Field(default_factory=list, max_length=7)
    sun_state: str = Field(default="below_horizon", pattern="^(above_horizon|below_horizon)$")

class AutomationActionRequest(BaseModel):
    kind: str = Field(default="service", pattern="^(service|notification|delay|wait_state)$")
    task_template: str = Field(default="service", pattern="^(service|turn_on|turn_off|toggle|set_temperature|set_brightness|notification|delay|wait)$")
    entity_id: str = Field(default="", max_length=255, pattern=r"^(|[a-z0-9_]+\.[a-z0-9_]+)$")
    service: str = Field(default="", max_length=120, pattern=r"^(|[a-z0-9_]+\.[a-z0-9_]+)$")
    service_data: dict[str, Any] = Field(default_factory=dict)
    delay_seconds: int = Field(default=0, ge=0, le=300)
    wait_operator: str = Field(default="equals", pattern="^(equals|not_equals|above|below)$")
    wait_value: str = Field(default="", max_length=255)
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    notification_title: str = Field(default="ZBRANO automation", max_length=120)
    notification_message: str = Field(default="", max_length=1000)
    notification_severity: str = Field(default="suggestion", pattern="^(information|suggestion|warning|critical)$")

class AutomationBranchRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    execution_policy: str | None = Field(default=None, pattern="^(approval_required|autonomous)$")
    suggestion: str = Field(default="", max_length=1000)
    message_enabled: bool | None = None
    delivery_voice: bool | None = None
    delivery_notification_center: bool | None = None
    delivery_ha_push: bool | None = None
    conditions: list[AutomationConditionRequest] = Field(default_factory=list, max_length=20)
    condition_mode: str = Field(default="all", pattern="^(all|any)$")
    actions: list[AutomationActionRequest] = Field(default_factory=list, max_length=20)

class AutonomousAutomationRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    objective: str = Field(min_length=3, max_length=1000)
    presence_entity: str = Field(default="", max_length=255)
    signal_entities: list[str] = Field(default_factory=list, max_length=20)
    context_notes: str = Field(default="", max_length=3000)
    proposal_template: str = Field(default="", max_length=1000)
    action_entity: str = Field(default="", max_length=255)
    action_service: str = Field(default="", max_length=120)
    cooldown_minutes: int = Field(default=30, ge=1, le=1440)
    suggestion_timeout_minutes: int = Field(default=30, ge=1, le=1440)
    reoffer_delta: float = Field(default=0, ge=0, le=100000)
    reset_delta: float = Field(default=0, ge=0, le=100000)
    confidence_threshold: float = Field(default=0.75, ge=0.5, le=0.99)
    risk_level: str = Field(default="controlled", pattern="^(informational|low|controlled|high)$")
    execution_policy: str = Field(default="inherit", pattern="^(inherit|observe|suggest|approval_required|autonomous)$")
    delivery_voice: bool = True
    delivery_notification_center: bool = True
    delivery_ha_push: bool = True
    notify_on_action: bool = True
    reversible_only: bool = True
    max_actions_per_hour: int = Field(default=2, ge=1, le=60)
    failure_limit: int = Field(default=3, ge=1, le=10)
    failure_window_minutes: int = Field(default=60, ge=5, le=1440)
    sleep_hours_enabled: bool = False
    sleep_hours_start: str = Field(default="22:00", pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    sleep_hours_end: str = Field(default="07:00", pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    run_during_sleep_hours: bool = False
    enabled: bool = False
    trigger_entity: str = Field(default="", max_length=255, pattern=r"^(|[a-z0-9_]+\.[a-z0-9_]+)$")
    trigger_operator: str = Field(default="changes_to", pattern="^(any_change|changes_to|equals|not_equals|above|below)$")
    trigger_value: str = Field(default="", max_length=255)
    trigger_for_seconds: int = Field(default=0, ge=0, le=86400)
    action_service_data: dict[str, Any] = Field(default_factory=dict)
    triggers: list[AutomationTriggerRequest] = Field(default_factory=list, max_length=10)
    trigger_mode: str = Field(default="any", pattern="^(any|all)$")
    conditions: list[AutomationConditionRequest] = Field(default_factory=list, max_length=20)
    condition_mode: str = Field(default="all", pattern="^(all|any)$")
    actions: list[AutomationActionRequest] = Field(default_factory=list, max_length=20)
    branches: list[AutomationBranchRequest] = Field(default_factory=list, max_length=10)

class AutomationChatDraftRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    objective: str = Field(min_length=3, max_length=1000)
    trigger_alias: str = Field(default="", max_length=255)
    trigger_entity: str = Field(min_length=3, max_length=255, pattern=r"^[a-z0-9_]+\.[a-z0-9_]+$")
    trigger_operator: str = Field(pattern="^(any_change|changes_to|equals|not_equals|above|below)$")
    trigger_value: str = Field(default="", max_length=255)
    trigger_for_seconds: int = Field(default=0, ge=0, le=86400)
    presence_alias: str = Field(default="", max_length=255)
    presence_entity: str = Field(default="", max_length=255, pattern=r"^(|[a-z0-9_]+\.[a-z0-9_]+)$")
    signal_entities: list[str] = Field(default_factory=list, max_length=20)
    suggestion: str = Field(min_length=3, max_length=1000)
    action_alias: str = Field(default="", max_length=255)
    action_entity: str = Field(default="", max_length=255, pattern=r"^(|[a-z0-9_]+\.[a-z0-9_]+)$")
    action_service: str = Field(default="", max_length=120, pattern=r"^(|[a-z0-9_]+\.[a-z0-9_]+)$")
    action_service_data: dict[str, Any] = Field(default_factory=dict)
    execution_policy: str = Field(default="approval_required", pattern="^(observe|suggest|approval_required|autonomous)$")
    cooldown_minutes: int = Field(default=30, ge=1, le=1440)
    risk_level: str = Field(default="controlled", pattern="^(informational|low|controlled|high)$")
    reversible_only: bool = True
    max_actions_per_hour: int = Field(default=2, ge=1, le=60)
    notify_on_action: bool = True

class AutomationDiscoveryFeedbackRequest(BaseModel):
    feedback: str = Field(pattern="^(helpful|not_helpful|always_suggest|never_suggest)$")

class NotificationCenterSettingsRequest(BaseModel):
    default_channel: str = Field(default="", max_length=255)
    suggestion_notifications: bool = True
    autonomous_action_notifications: bool = True
    quiet_hours_enabled: bool = False
    quiet_hours_start: str = Field(default="22:00", pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    quiet_hours_end: str = Field(default="07:00", pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    critical_override: bool = True
    repeat_critical_minutes: int = Field(default=15, ge=0, le=1440)

class NotificationTestRequest(BaseModel):
    target: str = Field(min_length=3, max_length=255, pattern=r"^notify\.[a-z0-9_]+$")
    severity: str = Field(default="information", pattern="^(information|suggestion|warning|critical)$")
    title: str = Field(default="ZBRANO notification test", max_length=120)
    message: str = Field(min_length=1, max_length=2000)
    suggestion_id: str = Field(default="", max_length=64, pattern=r"^(|[a-f0-9]{20})$")

class NotificationWatchRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    entity_id: str = Field(min_length=3, max_length=255, pattern=r"^[a-z0-9_]+\.[a-z0-9_]+$")
    trigger_state: str = Field(min_length=1, max_length=255)
    destination: str = Field(default="", max_length=255, pattern=r"^(|notify\.[a-z0-9_]+)$")
    severity: str = Field(default="information", pattern="^(information|suggestion|warning|critical)$")
    title: str = Field(default="ZBRANO notification", max_length=120)
    message: str = Field(min_length=1, max_length=2000)
    active_start: str = Field(default="", pattern=r"^(|([01]\d|2[0-3]):[0-5]\d)$")
    active_end: str = Field(default="", pattern=r"^(|([01]\d|2[0-3]):[0-5]\d)$")
    one_shot: bool = False
    expires_at: float = Field(default=0, ge=0)
    cooldown_minutes: int = Field(default=5, ge=0, le=10080)
    enabled: bool = True

class NotificationWatchStateRequest(BaseModel):
    enabled: bool

class CalendarAppointmentRequest(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    start_at: str = Field(min_length=10, max_length=64)
    duration_minutes: int = Field(default=60, ge=5, le=10080)
    location: str = Field(default="", max_length=300)
    notes: str = Field(default="", max_length=3000)
    destination: str = Field(default="", max_length=255, pattern=r"^(|notify\.[a-z0-9_]+)$")
    reminder_offsets_minutes: list[int] = Field(default_factory=list, max_length=8)

class CalendarRemindersUpdateRequest(BaseModel):
    destination: str = Field(default="", max_length=255, pattern=r"^(|notify\.[a-z0-9_]+)$")
    reminder_offsets_minutes: list[int] = Field(default_factory=list, max_length=8)

class BirthdayRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    birthday: str = Field(pattern=r"^(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$")
    birth_year: int | None = Field(default=None, ge=1900, le=2200)
    relationship: str = Field(default="", max_length=100)
    reminder_days_before: list[int] = Field(default_factory=lambda: [7, 1, 0], max_length=8)
    destination: str = Field(default="", max_length=255, pattern=r"^(|notify\.[a-z0-9_]+)$")
    notes: str = Field(default="", max_length=3000)
    gift_ideas: str = Field(default="", max_length=3000)

class BirthdayUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    birthday: str | None = Field(default=None, pattern=r"^(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$")
    birth_year: int | None = Field(default=None, ge=1900, le=2200)
    relationship: str | None = Field(default=None, max_length=100)
    reminder_days_before: list[int] | None = Field(default=None, max_length=8)
    destination: str | None = Field(default=None, max_length=255, pattern=r"^(|notify\.[a-z0-9_]+)$")
    notes: str | None = Field(default=None, max_length=3000)
    gift_ideas: str | None = Field(default=None, max_length=3000)

class ContactBankAccount(BaseModel):
    label: str = Field(default="", max_length=100)
    bank_name: str = Field(default="", max_length=160)
    account_name: str = Field(default="", max_length=160)
    iban: str = Field(default="", max_length=64)
    account_number: str = Field(default="", max_length=100)
    swift: str = Field(default="", max_length=32)

class ContactRequest(BaseModel):
    kind: str = Field(default="person", pattern="^(person|company)$")
    display_name: str = Field(default="", max_length=160)
    given_name: str = Field(default="", max_length=100)
    family_name: str = Field(default="", max_length=100)
    company_name: str = Field(default="", max_length=160)
    job_title: str = Field(default="", max_length=160)
    phone_numbers: list[str] = Field(default_factory=list, max_length=20)
    emails: list[str] = Field(default_factory=list, max_length=20)
    birthday: str = Field(default="", pattern=r"^(|(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01]))$")
    birth_year: int | None = Field(default=None, ge=1800, le=2200)
    relationship: str = Field(default="", max_length=100)
    address: str = Field(default="", max_length=1000)
    website: str = Field(default="", max_length=500)
    notes: str = Field(default="", max_length=5000)
    bank_accounts: list[ContactBankAccount] = Field(default_factory=list, max_length=10)

class ContactUpdateRequest(BaseModel):
    kind: str | None = Field(default=None, pattern="^(person|company)$")
    display_name: str | None = Field(default=None, max_length=160)
    given_name: str | None = Field(default=None, max_length=100)
    family_name: str | None = Field(default=None, max_length=100)
    company_name: str | None = Field(default=None, max_length=160)
    job_title: str | None = Field(default=None, max_length=160)
    phone_numbers: list[str] | None = Field(default=None, max_length=20)
    emails: list[str] | None = Field(default=None, max_length=20)
    birthday: str | None = Field(default=None, pattern=r"^(|(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01]))$")
    birth_year: int | None = Field(default=None, ge=1800, le=2200)
    relationship: str | None = Field(default=None, max_length=100)
    address: str | None = Field(default=None, max_length=1000)
    website: str | None = Field(default=None, max_length=500)
    notes: str | None = Field(default=None, max_length=5000)
    bank_accounts: list[ContactBankAccount] | None = Field(default=None, max_length=10)

class GoogleCalendarSyncSettingsRequest(BaseModel):
    calendar_id: str = Field(default="primary", min_length=1, max_length=1024)
    enabled: bool = False

class FastMemoryWriteRequest(BaseModel):
    kind: str = Field(pattern="^(profile|preference|project|decision|fact|follow_up|session_summary|temporary)$")
    subject: str = Field(min_length=1, max_length=160)
    key: str = Field(min_length=1, max_length=120)
    value: str = Field(min_length=1, max_length=1600)
    summary: str = Field(default="", max_length=500)
    keywords: list[str] = Field(default_factory=list, max_length=20)
    importance: int = Field(default=3, ge=1, le=5)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    pinned: bool = False
    expires_at: float = Field(default=0, ge=0)

class FastMemoryForgetRequest(BaseModel):
    query: str = Field(min_length=2, max_length=300)

class KnowledgeSpaceCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    purpose: str = Field(default="", max_length=1000)
    template: str = Field(default="blank", min_length=1, max_length=100)
    category: str = Field(default="Personal", min_length=1, max_length=100)

class KnowledgeRememberRequest(BaseModel):
    content: str = Field(min_length=1, max_length=50000)
    title: str = Field(default="", max_length=160)
    preferred_area: str = Field(default="auto", max_length=100)
    organization: str = Field(default="auto", pattern="^(auto|append_existing|create_new)$")
    destination_note: str = Field(default="", max_length=180)

class KnowledgeCategoryCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    icon: str = Field(default="custom", min_length=1, max_length=30)
    description: str = Field(default="", max_length=300)

class KnowledgeTemplateNoteRequest(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    purpose: str = Field(default="", max_length=300)
    content: str = Field(default="", max_length=200000)

class KnowledgeTemplateWriteRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    original_name: str = Field(default="", max_length=100)
    description: str = Field(default="", max_length=500)
    category: str = Field(default="Personal", min_length=1, max_length=100)
    icon: str = Field(default="template", min_length=1, max_length=30)
    notes: list[KnowledgeTemplateNoteRequest] = Field(default_factory=list, max_length=30)

class KnowledgeNoteWriteRequest(BaseModel):
    note: str = Field(min_length=1, max_length=300)
    content: str = Field(default="", max_length=1000000)
    mode: str = Field(default="create", pattern="^(create|replace)$")

class TelegramInboundSettingsRequest(BaseModel):
    enabled: bool = False
    reply_channel: str = Field(default="", max_length=255, pattern=r"^(|notify\.[a-z0-9_]+)$")
    remote_approvals_enabled: bool = False

class TelegramInboundUnlinkRequest(BaseModel):
    chat_id: str = Field(min_length=1, max_length=64, pattern=r"^-?[0-9]+$")

class SettingsRestoreRequest(BaseModel):
    backup: dict[str, Any]

class SpeechRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    provider: str = Field(default="default", pattern="^(default|openai|elevenlabs)$")
    voice: str = Field(default="cedar", min_length=1, max_length=100)

class EntityCatalogItem(BaseModel):
    entity_id: str = Field(min_length=3, max_length=255)
    friendly_name: str = Field(min_length=1, max_length=255)
    domain: str = Field(min_length=1, max_length=64)
    device_class: str | None = Field(default=None, max_length=100)
    unit: str | None = Field(default=None, max_length=64)
    access: str = Field(
        pattern="^(read_only|state_only|low_risk_control_proposed|confirmation_required|restricted)$"
    )
    aliases: list[str] = Field(default_factory=list, max_length=20)

class EntityCatalogDraftRequest(BaseModel):
    project: str = Field(default="ZBRANO", min_length=1, max_length=255)
    entities: list[EntityCatalogItem] = Field(min_length=1, max_length=500)

class EntityPolicyUpdate(BaseModel):
    enabled: bool
    friendly_name: str = Field(min_length=1, max_length=255)
    domain: str = Field(min_length=1, max_length=64)
    device_class: str | None = Field(default=None, max_length=100)
    unit: str | None = Field(default=None, max_length=64)
    access: str = Field(
        pattern="^(read_only|state_only|low_risk_control_proposed|confirmation_required|restricted)$"
    )
    aliases: list[str] = Field(default_factory=list, max_length=20)

class NotificationDeliveryDeleteRequest(BaseModel):
    ids: list[str] = Field(min_length=1, max_length=100)

class NotificationReadRequest(BaseModel):
    ids: list[str] = Field(default_factory=list, max_length=100)
    all: bool = False

class SharedFilesDeleteRequest(BaseModel): file_ids:list[str]=Field(default_factory=list,max_length=100)

class DeveloperModeRequest(BaseModel):
    enabled: bool

class DeveloperInvestigationRequest(BaseModel):
    feature: str = Field(default="auto", max_length=80)
    symptom: str = Field(min_length=3, max_length=2000)
    browser_evidence: dict[str, Any] = Field(default_factory=dict)
