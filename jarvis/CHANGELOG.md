# Change log

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
