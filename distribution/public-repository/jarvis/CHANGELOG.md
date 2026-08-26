# Change log

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
