# Change log

## 0.13.152

- Sensor devices now offer Monitor silently or Notify me.
- Control devices now offer Ask me first or Do it automatically.
- Removed overlapping suggestion and approval wording from the common editor.
- Safely normalize older authority selections when the device type changes.

## 0.13.151

- Replaced four abstract risk categories with Sensor device and Control device.
- Kept older saved risk values compatible when reopening automations.
- Hid action-count and completion settings for rules that cannot control devices.
- Limited the reversible-action setting to automatic Control device rules.

## 0.13.150

- Added Require presence and its entity picker to each automation's Setup & safety step.
- Replaced the optional-results question with direct IF / ELSE IF paths and visible fork arrows.
- Kept existing And checks and Then tasks connected in the first IF path when branching begins.
- Limited the inspector to the selected path, check, or task and renamed the save activation option.

## 0.13.149

- Added dedicated Sensor, Power on, Power off, Time, Sun, Repeat, and One time choices for When blocks.
- Changed the inspector to show only the selected When block's settings.
- Removed Say cards and message controls from automatic flows so the canvas contains only connected behavior.

## 0.13.148

- Made the aarch64 Automation Studio Undo check independent of intermediate navigation history.
- Replaced a fixed recovery delay with an observed persisted-state condition.
- Preserved all v0.13.147 application behavior and per-automation safety controls.

## 0.13.147

- Moved authority, impact, hourly limits, reversibility, and notification choices into Step 1 of each automation.
- Defaulted new rules to an explicit Suggest it to me authority while preserving existing rules.
- Removed the global authority tab from normal navigation while retaining hard built-in safety ceilings.

## 0.13.146

- Aligned guided name and purpose validation with the server's save requirements.
- Replaced `[object Object]` save failures with readable field-specific messages.
- Added browser and release regression coverage for the failed-save path.

## 0.13.145

- Replaced the technical Outcomes step with an optional Different results question.
- Presented each result with plain When / Then language and a clearly explained fallback.
- Preserved the interactive flow, branching engine, advanced settings, and saved automations.

## 0.13.144

- Removed a builder-speed race from the ARM Chromium Undo validation.
- Waited for the persisted debounced history state instead of a fixed delay.
- Preserved all v0.13.143 application behavior.

## 0.13.143

- Made new Then steps start with icon-based, ready-made task choices.
- Moved custom Home Assistant commands behind a clear Advanced disclosure.
- Replaced raw command names in flow cards, saved summaries, and activation confirmation.

## 0.13.142

- Started every new Automation Studio draft at Step 1: Name it.
- Added clear Back, Next, progress, and final review controls to the five-step guide.
- Explained incomplete required information before advancing while preserving direct flow editing.

## 0.13.141

- Added live Ready, Needs attention, Optional, and item-count states to the numbered Studio guide.
- Added discreet blue completion checks and clear attention styling.
- Replaced technical validation, saved-automation, and activation wording with everyday language.

## 0.13.140

- Labelled every repeatable trigger, check, and task field in everyday language.
- Grouped confidence tuning and safety controls into discreet expandable sections while preserving every setting.
- Used Outcome terminology consistently and renamed toolbar actions to explain what they do.

## 0.13.139

- Kept the interactive Automation Studio flow and added a numbered step-by-step guide.
- Added device-aware icons, friendly names, and compact comparison symbols to flow cards.
- Replaced technical settings and Decision branches with plain-language questions and IF / OTHERWISE outcomes.

## 0.13.138

- Fixed Home Assistant entities not loading when a second or later Trigger card was selected.
- Focused each selected Trigger's own entity field so its picker opens immediately.
- Focused the relevant time, sun, interval, or one-time field for schedule triggers.

## 0.13.137

- Removed circular rings and halos from neural signal arrival flashes.
- Replaced them with a brief four-point electrical sparkle at the destination neuron.
- Preserved neutral resting neuron interiors and blue connection activity.

## 0.13.136

- Removed the remaining blue tint from resting neuron interiors.
- Used equal RGB channels for neuron cores in dark, light, and gray themes.
- Preserved blue connections, outlines, moving signals, and arrival halos.

## 0.13.135

- Added a compact warm-white flash inside each destination neuron.
- Added a discreet expanding blue halo so arrivals read separately from moving signals.
- Preserved subdued resting neuron interiors and existing animation pause behavior.

## 0.13.134

- Moved neural firing impulses above neuron bodies so they remain visible.
- Increased signal cadence and arrival-flash clarity while keeping the effect bounded.
- Shifted neuron interiors toward neutral charcoal to reduce their blue tint.

## 0.13.133

- Added sparse, faint impulses that travel along neural connections.
- Added a discreet arrival flash inside each impulse's destination node.
- Kept neural firing effects disabled whenever backdrop animation is paused.

## 0.13.132

- Stopped neural animation after a chat begins while retaining the configured static backdrop.
- Paused neural rendering during chat-text selection and while the chat workspace is hidden.
- Retained ambient animation on an empty new-chat screen.

## 0.13.131

- Unified the interface around the Talk button's theme-aware blue.
- Replaced remaining green accents, glows, surface tints, and neural backdrop colors.
- Preserved red and amber warning/error semantics across dark, light, and gray themes.

## 0.13.130

- Reframed trigger cards as the watcher events that wake an automation.
- Added explicit IF, ELSE IF, and ELSE presentation to decision paths.
- Added state-or-attribute, operator, value/entity comparison, and duration fields to conditions.
- Preserved compatibility with existing automation definitions and legacy presence gates.

## 0.13.129

- Hid textbox placeholder explanations while their field is focused.
- Restored explanations when empty fields lose focus.
- Preserved all entered and stored field values.

## 0.13.128

- Stabilized the Automation Studio browser gate on slower ARM builders.
- Restored publication of the Home Assistant image after the v0.13.127 timeout.
- Kept application behavior and stored data unchanged.

## 0.13.127

- Replaced the separate Upcoming Birthday tab with one People directory.
- Added the nearest birthdays at the top and colored month sections below.
- Defaulted chat-created birthdays to reminders one week and one day before.
- Preserved reminder schedules already selected by the user.

## 0.13.126

- Preserved recurring Birthday cards after reminder delivery.
- Merged delivery status into the latest birthday storage state.
- Recovered missing Birthday records from linked Contacts.

## 0.13.125

- Stopped displaying the automation Objective as a Do This task.
- Added a clear placeholder until a real suggestion or task is configured.

## 0.13.124

- Renamed the visible Automation Studio Context block to Condition.
- Simplified flow wording to direct Check, If, Do, and And steps.
- Displayed complete friendly names and entity IDs on flow cards.
- Removed confidence and operating-mode descriptions from process cards.

## 0.13.123

- Restored searchable entity loading for Context presence and signal fields.
- Restored searchable entity loading for Action entity fields.
- Positioned Contacts immediately to the right of Calendar.

## 0.13.122

- Restored independent vertical scrolling in the Contacts workspace.
- Added remembered Cards, List, and Compact contact arrangements.

## 0.13.121

- Made notification read-state validation deterministic in the container browser gate.
- Preserved application behavior and stored data.

## 0.13.120

- Replaced generic Google Contacts HTTP 500 failures with actionable setup errors.
- Skipped malformed individual Google records without aborting the full import.
- Preserved existing local contact details when Google omits those fields.
- Added created, updated, and skipped result counts.

## 0.13.119

- Added a private Contacts tab for rich person and company records.
- Added CSV, vCard, and read-only Google Contacts import options.
- Linked contact birthdays to the existing Birthday reminder system.
- Added numbered chat choices for ambiguous contacts and all other clarifications.
- Kept sensitive bank fields out of ordinary contact search results.

## 0.13.118

- Showed only settings relevant to the selected Automation Studio trigger type.
- Hid the unused target-value field for Any state change triggers.
- Refreshed contextual controls immediately after trigger type or operator changes.
- Preserved existing automation definitions and stored data.

## 0.13.117

- Moved My Automations and Automation Memory into the Automation Studio left navigation.
- Replaced the nested create/library switcher with dedicated full-page destinations.
- Made saved automations compact by default with an independent flow expand control.
- Preserved existing automation definitions, controls, memory, and stored data.

## 0.13.116

- Added a distinct suggestion message to each Automation Studio decision path.
- Added live entity-state comparisons against another entity's state or attribute.
- Added a Compare entities building block and visual condition summary.
- Preserved existing automation definitions and first-match branch behavior.

## 0.13.115

- Restored the searchable Home Assistant entity picker in the WHEN-card inspector.
- Synchronized picker selections into the canonical trigger field and saved workflow.
- Added real-browser regression coverage for loading and selecting a trigger entity.

## 0.13.114

- Displayed climate HVAC mode and configured target temperature together in Entity Inventory.
- Added current temperature and active HVAC action as concise climate detail.
- Preserved existing entity state, control permissions, and stored data.

## 0.13.113

- Added a discreet delete control that appears when a top-bar notification is hovered.
- Added Approve action, Not now, and applicable Never suggest controls to Automation suggestion notifications.
- Kept the inbox open and reconciled its persistent unread badge immediately after deletion.
- Synchronized Notification Center delivery logs and added browser coverage for the workflow.

## 0.13.112

- Fixed the container-only complete-backup integration contract to include birthdays.
- Added birthday export, clearing, restore, and identity verification to the build gate.
- Preserved the Birthday center and top-bar notification inbox introduced in v0.13.111.

## 0.13.111

- Added dedicated Upcoming, People, and Add Birthday views inside Calendar.
- Added annual local birthday records with optional ages, relationships, notes, and gift ideas.
- Added configurable Notification Center reminders plus chat save, lookup, and gift-detail workflows.
- Included birthdays in backup, restore, activity tracking, and browser validation.
- Added a top-bar notification bell with an unread badge and in-place recent-delivery dropdown.
- Added persistent mark-read state, Mark all read, and a shortcut to full delivery logs.

## 0.13.110

- Removed synchronous textarea measurement from every typed character.
- Added native content sizing with a frame-batched fallback for older browsers.
- Preserved multiline composer growth and its existing maximum height.

## 0.13.109

- Added direct duplicate, reorder, and delete controls for complete decision paths.
- Kept a trailing ELSE fallback fixed at the end of first-match evaluation.
- Copied ELSE paths become configurable conditional paths, preserving one fallback.

## 0.13.108

- Added direct decision-path creation on the visual canvas.
- Added Entity State, Time Window, Weekdays, and Sun State branch condition presets.
- Kept new paths before a trailing ELSE fallback and focused each new condition's settings.

## 0.13.107

- Added direct IF condition controls inside every decision path.
- Added branch-local Power, Climate, Lighting, Notification, Delay, Wait Until, and Custom Service task presets.
- Added selected-position insertion and automatic focus on each new branch block's settings.

## 0.13.106

- Rendered branch conditions as visible IF cards with direct AND/OR controls.
- Added exact Context insertion and condition ordering within or between paths.
- Added direct branch-condition selection, duplication, deletion, and Undo/Redo recovery.

## 0.13.105

- Rendered every decision branch as a visible lane containing its actual tasks.
- Added drag assignment from linear actions and direct toolbox insertion into branches.
- Added in-branch reordering and clearly marked unassigned tasks as not executed.

## 0.13.104

- Added exact-position insertion when toolbox blocks are dropped between cards.
- Added same-stage drag reordering while preserving trigger and action configuration.
- Added discreet card duplication beside delete with Undo/Redo recovery.

## 0.13.103

- Added discreet hover and keyboard-focus delete controls to real flow cards.
- Mapped deletion to exact triggers, context items, branches, and tasks with Undo recovery.
- Kept dense card groups and their controls inside the responsive canvas.

## 0.13.102

- Added installation-aware Set Temperature and Set Brightness task blocks.
- Added focused target controls backed by real Home Assistant service data.
- Preserved preset identity and visual editing behavior after save and reopen.

## 0.13.101

- Added an AppSheet-style ready-made task palette to the Action inspector.
- Added executable Power On, Power Off, Toggle, Notification, Delay, Wait Until, and Custom Service blocks.
- Made notification tasks installation-aware and routed them through Home Assistant notify channels.

## 0.13.100

- Automatically compacted flow stages containing more than two cards.
- Kept larger same-category groups within the Automation Studio canvas.
- Widened OR/AND selectors so their selected value is fully visible.

## 0.13.99

- Rebuilt Automation Studio as an AppSheet-style staged event and process canvas.
- Kept every trigger, condition, branch, and action visible as a separate card.
- Added persisted OR/AND trigger controls with dry-run and runtime enforcement.

## 0.13.98

- Added build-gated end-to-end Automation Studio workflow lifecycle coverage.
- Verified persistence, safe dry-run, activation, reload, event evaluation, and suggestion output together.
- Confirmed the lifecycle test never executes its proposed Home Assistant action.

## 0.13.97

- Removed an asynchronous browser-test timing race on slower ARM image builders.
- Preserved the functional Automation Studio drag-and-drop behavior from v0.13.96.

## 0.13.96

- Made toolbox drag-and-drop create real automation draft blocks.
- Rendered dropped Trigger, Context, Decision, and Action blocks immediately in the visual flow.
- Kept incomplete blocks inside existing validation, undo, reset, and safety limits.

## 0.13.95

- Made Automation drafts open My Automations with the matching filter.
- Made Pending suggestions focus the Suggestion Inbox directly.
- Aligned shortcut counts, hover states, focus behavior, and accessible labels.

## 0.13.94

- Exposed known Home Assistant Area-to-Zone links to conversational automation creation.
- Reused approved person or device-tracker presence candidates for site-aware rules.
- Stopped asking for Zone IDs already known by Rooms & Learning.

## 0.13.93

- Hid the owner-specific Grinder HUD when its Home Assistant option is disabled.
- Removed disabled Grinder chat routing and AI tools from normal product behavior.
- Guarded owner-only incident APIs while preserving explicitly enabled owner installations.

## 0.13.92

- Added a build-gated complete backup export and restore round trip.
- Verified Settings, chats, entity policy, automations, notifications, calendar, and Fast Memory together.
- Isolated integration-test Fast Memory storage and confirmed secrets remain outside backups.

## 0.13.91

- Added build-gated restore and upgrade coverage for pre-Studio simple automations.
- Verified legacy rule identity, creation time, trigger semantics, and suggestion wording remain intact.
- Verified current workflow collections are added safely when an older rule is edited and saved.

## 0.13.90

- Added confirmed Pause controls that stop live automation evaluation immediately.
- Preserved each paused rule's complete definition and history.
- Added Resume controls that reuse existing activation permission and authority checks.

## 0.13.89

- Added a Duplicate action that copies a saved automation into a new Studio draft.
- Cleared the source identity and disabled the copy so the original cannot be overwritten.
- Required explicit review and Save, with existing unsaved-work protection retained.

## 0.13.88

- Added Detailed and responsive Compact card layouts to My Automations.
- Kept names, objectives, state tags, and editing actions visible in Compact mode.
- Remembered the chosen layout locally and safely defaulted invalid data to Detailed.

## 0.13.87

- Added live graphical counts for all, active, attention-needed, draft or disabled,
  and automatic automations.
- Made each summary an accessible one-click filter synchronized with the state selector.
- Kept quick-filter selection synchronized with locally remembered library preferences.

## 0.13.86

- Added My Automations sorting by recent update, name, active state, and attention
  priority with deterministic fallback ordering.
- Remembered the selected Studio library view, state filter, and sort order locally.
- Validated restored preferences and safely ignored missing or invalid local data.

## 0.13.85

- Added compact My Automations search across names, objectives, entities, services,
  triggers, conditions, actions, and branches.
- Added active, attention-needed, disabled, automatic, and notification-watch filters
  with live result counts.
- Added clear no-match feedback without modifying stored automation definitions.

## 0.13.84

- Added an explicit Unsaved changes badge to Automation Studio.
- Protected dirty flows before New Flow, template loading, opening another rule, or
  Cancel replaces the current editor state.
- Preserved every current field and workflow step when replacement confirmation is
  dismissed, without interrupting clean flows or ordinary navigation.

## 0.13.83

- Added continuous validation for visual automation details, triggers, conditions,
  actions, branches, and service-data JSON.
- Added clickable issue chips and amber canvas markers that open the relevant block
  inspector and focus a known field.
- Guarded Test Flow and Save Draft against incomplete structures while retaining
  valid suggestion-only workflows.

## 0.13.82

- Recovered the current unsaved Automation Studio flow after an accidental refresh.
- Kept recovery local to the Home Assistant browser origin with a seven-day expiry
  and 100 KB ceiling.
- Flushed pending edits during page hide and discarded recovery after save or when
  another flow is started, templated, or opened.

## 0.13.81

- Added visible Undo and Redo controls to Automation Studio with standard keyboard
  shortcuts.
- Retained up to 50 local edit states covering fields, workflow steps, branches,
  and selected block context.
- Restored the underlying advanced-editor values together with the visual flow and
  reset history cleanly for new, templated, and existing drafts.

## 0.13.80

- Capped wide Settings and Automation controls and sliders at practical reading
  widths with responsive single-column fallbacks.
- Added a Settings-style icon-led sidebar and independently scrolling content views
  to Automations.
- Restored verified vertical scrolling for Voice Settings and other full-height
  workspaces.

## 0.13.79

- Moved the graphical Automation Studio above Create with ZBRANO.
- Added a GitHub-inspired Settings sidebar with expandable groups, icons, keyboard
  navigation, and colored section accents.
- Replaced visible primary-navigation button chrome with hover targets and an active
  underline, retaining a compact responsive mobile layout.

## 0.13.78

- Added a bounded 30-record decision journal to each automation with outcome,
  reason, evidence, authority, branch, and timestamp.
- Recorded context suppressions, Not now and learned deferrals, rate limits,
  permission blocks, suggestions, observations, and action results.
- Added an expandable Automation Studio journal showing the latest five decisions.

## 0.13.77

- Added live readiness checks for trigger, condition, presence, wait, and action
  entity permissions plus Home Assistant control-blocking safety labels.
- Blocked stale approvals and autonomous execution when current access is unsafe,
  while preserving observe and suggestion-only behavior.
- Added exact readiness explanations in Automation Studio with automatic recovery
  when permissions or labels are restored.

## 0.13.76

- Added configurable per-automation failure limits and rolling failure windows.
- Paused approval-required and autonomous execution when the failure circuit opens,
  while preserving observe and suggestion-only evaluation.
- Added visible circuit reasoning and an explicit Reset recovery control that
  acknowledges recovery without erasing failure history or changing authority.

## 0.13.75

- Added configurable per-automation response windows so unanswered suggestions
  expire instead of blocking future evaluation indefinitely.
- Recovered persisted interrupted executions as visible failures without retrying
  actions or changing authority.
- Added Automation Studio outcome health for expirations, automatic successes,
  and action failures while keeping expired items out of the active inbox.

## 0.13.74

- Applied repeated Not now feedback to gradually postpone future suggestions for
  the same automation until its condition becomes more significant.
- Cleared learned restraint after approval or matching manual action and retained
  a bounded 20-outcome evidence history.
- Added visible feedback reasoning and a per-rule Reset learning control without
  changing permissions, autonomy, or episode history.

## 0.13.73

- Tracked numeric threshold conditions as bounded episodes with direction,
  current and worst values, sample count, and retained episode history.
- Added per-automation worsening and reset margins with compatible automatic defaults.
- Remembered dismissal, approval, and manual-resolution outcomes and surfaced live
  episode reasoning in Automation Studio.

## 0.13.72

- Made Not now persist the declined trigger value and direction for each rule.
- Suppressed repeated numeric suggestions while conditions improve or have not
  worsened meaningfully, and re-armed rules after their trigger clears.
- Prevented duplicate pending suggestions and proposals for configured actions
  already satisfied by current Home Assistant device state.

## 0.13.71

- Added graphical local-time, weekday, sunrise/sunset-offset, interval, and
  one-time schedule triggers to Automation Studio.
- Added time-window, weekday, sun-state, and sustained entity-state conditions.
- Added persistent schedule markers and a resilient background evaluator to
  prevent duplicate scheduled runs while preserving entity-event automations.

## 0.13.70

- Added a zero-action Test Flow evaluator for unsaved Automation Studio drafts.
- Added graphical Trigger, Context, Decision, and Planned Actions test traces using
  current Home Assistant state and the effective safety policy.

## 0.13.69

- Added per-automation operating modes and delivery channels under the global
  safety ceiling.
- Promoted Automation Studio into a full-window workspace and renamed the saved
  rule view to My Automations.
- Prevented suggestion-only rules from being executed through approval controls.

## 0.13.68

- Added dedicated Delay and Wait Until steps to linear and branching action
  sequences.
- Added bounded wait timeouts, state operators, typed validation, and preserved
  compatibility for existing service actions.

## 0.13.67

- Added first-match IF/ELSE branches with per-branch ALL/ANY conditions and
  ordered action sequences.
- Preserved the selected branch actions through suggestion, approval, autonomous
  execution, and audit history.

## 0.13.66

- Added repeatable OR triggers and grouped ALL/ANY state conditions to Automation
  Studio while preserving existing single-trigger rules.
- Added ordered Home Assistant action sequences with per-step permission and
  safety checks.

## 0.13.65

- Repaired visual block selection and the container browser release gate by
  separating decorative connector arrows from workflow pointer handling.

## 0.13.64

- Rebuilt Automation Studio as a three-panel visual editor with a building-block
  toolbox, dotted node canvas, and contextual settings inspector.
- Added click, keyboard, and drag-to-canvas block selection while retaining the
  compatible Advanced editor and existing automation definitions.

## 0.13.63

- Added responsive graphical WHEN, IF, DECIDE, and THEN flows for saved
  automations.
- Added a live visual preview for templates and manual drafts while preserving
  the existing automation engine and stored definitions.

## 0.13.62

- Added a resumable guided Setup sequence with Back, Continue, and optional-step
  skipping.
- Added required-step progression gates, focused remediation guidance, and a
  concise setup summary without changing existing installations.

## 0.13.61

- Stored bounded verification results and timestamps for each setup check.
- Required new installations to explicitly verify Home Assistant and the AI model
  before finishing setup, while preserving existing installations unchanged.

## 0.13.60

- Added explicit setup checks for Home Assistant, model credentials, entity
  permissions, voice configuration, memory, plugins, and notification channels.
- Added direct guided actions from each setup item without running paid checks
  automatically.

## 0.13.59

- Added a backward-compatible first-run setup checklist with readiness detection,
  preserved existing installations, and optional guided links.
- Classified Grinder monitoring as an owner-only private extension and excluded it
  from onboarding and general product scope.

## 0.13.58

- Aligned the Docker-only ASGI and browser build fixtures with the release version
  so the compatibility release can publish successfully.

## 0.13.57

- Joined both public repository transition histories so Home Assistant Supervisor
  can update whether it cached the legacy source branch or the first thin branch.
- Kept the current public tree limited to the five installer files.

## 0.13.56

- Connected the thin installer tree to the last previously public commit so cached
  Home Assistant repository clones can fast-forward and discover updates.
- Kept all post-split source and build commits private.

## 0.13.55

- Restored the original public `jarvis/` add-on folder so existing Home Assistant
  installations discover updates without uninstalling or losing stored data.

## 0.13.54

- Split private application source and build history from the clean public Home
  Assistant installation repository.
- Preserved the existing add-on slug, configuration schema, persistent data, and
  GHCR image path for upgrade continuity.
