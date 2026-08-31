# ZBRANO

ZBRANO is a Home Assistant intelligence assistant with chat, voice, entity control,
automations, notifications, calendar integration, local memory, and optional plugin
connections.

## Automation Studio

Version 0.13.109 adds direct duplicate, reorder, and delete controls for complete
decision paths while protecting trailing-ELSE order. The full Advanced editor remains available, existing stored automations are preserved, and
repeatable OR triggers, grouped conditions, ordered actions, and IF/ELSE branches
are supported, together with dedicated Delay and bounded Wait Until steps. Each
automation can use the global operating default or select its own lower authority,
plus voice, Studio inbox, and Home Assistant push delivery.
Build-gated upgrade coverage now proves that pre-Studio simple rules retain their
identity, creation history, trigger behavior, and suggestion wording when restored
and saved through the current workflow schema.
A complete backup gate now exports and restores all supported user-data domains
together while keeping secrets and plugin credentials outside the backup.
The owner-specific Grinder diagnostic extension remains invisible and unavailable
unless its explicit Home Assistant option is enabled.
Conversational creation now reads known Home Assistant Area-to-Zone links and uses
approved person or device-tracker presence sources for site-aware automation drafts.
Automation Overview draft and pending-suggestion metrics now open their matching
filtered destinations directly with accessible keyboard focus.
Studio also checks live read and control permissions plus Home Assistant safety
labels before approval or autonomous execution and explains any blocked entity.
Its bounded per-automation decision journal shows why recent evaluations observed,
suppressed, deferred, suggested, blocked, or executed.
The visual Studio is presented before conversational creation, with a modern
collapsible Settings sidebar and a quiet hover-driven primary top bar.
Controls use compact readable widths, Automations shares the icon-led sidebar, and
long Voice and full-height workspace pages scroll independently and reliably.
Visible Undo and Redo controls plus standard keyboard shortcuts restore field,
workflow-step, branch, and selected-block edits from a bounded local history.
Unsaved work recovers after an accidental refresh from a seven-day, 100 KB maximum
browser-local record that is discarded after save or when another flow is opened.
Live validation marks incomplete canvas blocks, links each issue to its inspector,
and guards Test and Save until the visual workflow is structurally complete.
Studio exposes unsaved state and confirms before New, template, edit, or cancel
actions replace a dirty flow; dismissing the confirmation preserves the draft.
My Automations can be searched by rule or workflow content and filtered by state,
with live result counts and no-match feedback that do not alter saved definitions.
Sorting by recency, name, active state, or attention priority is available, and the
chosen Studio library view, filter, and sort are remembered locally.
Live status summaries for all, active, attention-needed, draft, and automatic rules
also work as accessible one-click filters synchronized with the state selector.
The library can switch between full Detailed workflows and a remembered Compact
card grid while keeping rule names, states, and editing actions available.
Saved rules can be duplicated into independent disabled drafts without overwriting
their source; the copy is only stored after explicit review and Save.
Confirmed Pause and Resume controls stop or restart live evaluation while preserving
definitions and history and retaining existing activation safety checks.
The Test Flow control checks an unsaved draft against current Home Assistant state,
renders a four-stage trace, and performs no service calls.
Graphical triggers now include selected local times and weekdays, sunrise or sunset
offsets, intervals, and one-time events. Context blocks can check time windows,
weekdays, sun state, and sustained entity states without breaking older rules.
Dismissed suggestions retain their trigger value and direction, preventing repeated
prompts while a numeric condition improves. The engine re-arms after reset and
checks whether configured Home Assistant actions are already satisfied.
Numeric conditions are now tracked as bounded episodes with live improving or
worsening direction, and each rule can optionally tune its reconsideration and
reset margins while retaining backward-compatible defaults.
Repeated Not now responses now adjust suggestion timing for only that automation.
The learned feedback is visible and resettable, while permissions and operating
authority remain unchanged.
Per-rule response windows now expire unanswered suggestions and recover interrupted
executions as visible failures. Outcome health reports expirations, automatic
successes, and action failures without retrying or increasing authority.
Repeated action failures now pause approval and autonomous execution behind a
configurable circuit. Reset recovery acknowledges the fault without erasing its
audit history or changing permissions.

After installation, configure your own service credentials and explicitly approve
the Home Assistant entities ZBRANO may read or control. Personal data and runtime
configuration remain in your Home Assistant installation.
