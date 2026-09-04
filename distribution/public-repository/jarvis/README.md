# ZBRANO

ZBRANO is a Home Assistant intelligence assistant with chat, voice, entity control,
automations, notifications, calendar integration, local memory, and optional plugin
connections.

## Automation Studio

Version 0.13.139 keeps the interactive flow and adds a numbered, icon-led,
plain-language building experience for common users.

Version 0.13.138 fixes additional Automation Studio Trigger cards so selecting one
loads its own Home Assistant entity picker or focuses its relevant schedule field.

Version 0.13.137 removes circular arrival rings and uses a brief four-point electrical
sparkle when a moving signal reaches its destination neuron.

Version 0.13.136 makes resting neuron interiors fully neutral grayscale in every
theme while retaining the blue neural network and firing effects.

Version 0.13.135 adds a compact bright destination flash and discreet expanding halo
when a neural signal reaches a neuron.

Version 0.13.134 makes connection impulses and arrival flashes clearly visible above
the neuron bodies and slightly neutralizes the blue tint inside each node.

Version 0.13.133 adds subtle connection impulses and destination-node flashes to the
active neural backdrop while preserving all animation pause rules.

Version 0.13.132 keeps the configured neural backdrop visible but pauses its animation
after chat begins, during chat-text selection, and whenever the chat workspace is
hidden.

Version 0.13.131 replaces the remaining green interface palette with the Talk
button's theme-aware blue across controls, accents, glows, surfaces, and the neural
backdrop.

Version 0.13.130 separates watcher events from IF / ELSE IF decisions and gives
each condition complete, clearly labelled value, attribute, comparison, and
duration controls.

Version 0.13.128 stabilizes the container browser validation on slower ARM builders
and restores image publication without changing application behavior.

Version 0.13.127 unifies Birthdays into one People view with the nearest birthdays
first and colored monthly sections below. Chat saves default to seven-day and
one-day reminders without replacing existing reminder choices.

Version 0.13.126 prevents reminder delivery from losing Birthday data and repairs
missing Birthday records from linked Contacts.

Version 0.13.125 keeps automation Objectives separate from Do This tasks and uses
a clear placeholder until a suggestion or task is configured.

Version 0.13.124 makes Automation Studio read as Check, If, and Do, renames the
visible Context block to Condition, and displays complete entity names and IDs.

Version 0.13.123 restores searchable Home Assistant entity choices for Context
presence, Context signals, and Action entities, and moves Contacts after Calendar.

Version 0.13.122 restores Contacts scrolling and adds Cards, List, and Compact
directory arrangements that are remembered in the browser.

Version 0.13.121 repairs a timing-sensitive notification assertion in the
container browser gate. Runtime behavior and stored data are unchanged.

Version 0.13.120 repairs Google Contacts imports with actionable Google People API
errors, per-record resilience, and preservation of local contact details.

Version 0.13.119 adds the private Contacts directory, file and read-only Google
imports, Birthday linking, and numbered chat disambiguation.

Version 0.13.117 moves My Automations and Automation Memory into dedicated,
indented Studio navigation entries. Saved automations stay compact and expose
their visual flow only through an independent expand control.

Version 0.13.116 adds branch-specific suggestions and live entity-to-attribute
conditions so multi-outcome behavior can remain in one Automation Studio flow.

Version 0.13.115 restores entity loading in Automation Studio's WHEN-card
inspector and synchronizes the selected Home Assistant entity into the workflow.

Version 0.13.114 shows a climate entity's HVAC mode and configured target temperature
together in Entity Inventory, such as `cool · set to 25 °C`. Current temperature and
active HVAC action remain available as detail without changing entity controls or
stored data. The full Advanced editor remains available, existing stored automations are preserved, and
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
