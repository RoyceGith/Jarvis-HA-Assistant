# Change log

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
