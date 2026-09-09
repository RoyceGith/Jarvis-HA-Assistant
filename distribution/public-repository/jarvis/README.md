# ZBRANO

![ZBRANO](logo.png)

**Conversation, home intelligence, and visual automation—with permissions you control.**

ZBRANO is a private Home Assistant intelligence assistant. It combines natural
conversation, live home context, voice, useful memory, notifications, organization,
and automation in one interface without granting itself access to every device.

The multilingual interface supports English, Greek, Italian, and French with
automatic device-language detection or an explicit saved selection. Core and
advanced workspaces, the About showcase, and displayed dates follow the selected
language while conversations, voice recognition, and personal content remain independent.

## Highlights

- **Talk naturally:** use text or voice, maintain separate conversations, attach
  files, use voice-independent browser wake recognition, and optionally search the
  web with visible sources.
- **Understand the home:** inspect permitted sensors, devices, areas, history, and
  live state changes.
- **Build visual automations:** create WHEN, IF, ELSE IF, message, and action paths
  with readable cards and a zero-action Test Flow.
- **Stay organized:** use private Fast Memory and built-in Knowledge Memory spaces
  for Home, Work, Study, Recipes, Projects, or any custom purpose, alongside shared
  files, contacts, birthdays, appointments, and reminders.
- **Connect deliberately:** add optional plugins and services only when needed.
- **Remain in control:** choose Sensor, Control, or no access for each entity and
  select authority independently for executable automation branches.

## Before installation

ZBRANO supports `aarch64` and `amd64` Home Assistant systems and requires your own
OpenAI or OpenRouter API key for its core AI connection. Home Assistant provides
the local API connection automatically. ZBRANO does not resell or operate a managed
AI service; usage and billing stay with the provider account you select.

## First setup

1. Install ZBRANO from its Home Assistant repository.
2. Open **Settings → Apps → ZBRANO → Configuration**.
3. Choose **Chat AI provider**, enter its API key, save, and restart the app.
4. Open the ZBRANO interface and follow the guided **Setup**.
5. In **Device access**, explicitly select the entities ZBRANO may use.
6. Start with Sensor access and ask-first automations until the behavior matches
   your home.

The Setup wizard verifies required connections, keeps optional features skippable,
and provides direct recovery guidance when a check fails.

## Device access

| Choice | Access granted |
| --- | --- |
| **Sensor device** | Read state and context only |
| **Control device** | Read state and perform explicitly configured actions |
| **Do not allow** | No ZBRANO access |

Discovery never grants permission automatically. Existing access can be reviewed or
revoked at any time.

## Automation safety

Automation Studio keeps the complete visual flow visible while showing settings only
for the selected block. Conditional branches can independently notify, ask before
acting, or—when deliberately configured—run automatically beneath safety limits.

Use **Try it safely** before saving. The test evaluates live conditions and explains
the selected path without sending notifications or controlling devices.

## Privacy and recovery

Persistent ZBRANO data remains in the Home Assistant app data area. Credentials stay
in protected configuration and are excluded from backups and Installation Reports.
The app includes guarded backups, permission audits, activity history, diagnostics,
and plain-language recovery guidance.

## Need help?

- Open **Setup** to recheck Home Assistant and AI connectivity.
- Create a sanitized report in **Settings → Installation Report**.
- Review the Home Assistant app log for startup or connection errors.
- See the [full changelog](CHANGELOG.md) for release details.
- Report reproducible issues at
  [RoyceGith/ZBRANO_HA_Assistant](https://github.com/RoyceGith/ZBRANO_HA_Assistant/issues).

Version 0.13.193 makes Knowledge Memory local and built in, with user-created spaces,
searchable Markdown notes, write approvals, backup and restore, and one-time legacy
import without an ongoing server, domain, or tunnel dependency.
Version 0.13.192 adds direct OpenAI or user-owned OpenRouter chat provider selection,
live model discovery, protected provider keys, and verified capability boundaries.
Version 0.13.186 introduced the four-language foundation and localized Home
Assistant configuration. Version 0.13.185 added `amd64` while preserving `aarch64`
and the existing update path.
The in-app **About** tab provides a visual overview of ZBRANO's complete feature set.

Version 0.13.196 restores reliable scrolling throughout Memory Database and
Template Studio on desktop and compact screens.

Version 0.13.195 makes category and layout choices distinct in Memory Studio and
shows only the organizational layouts relevant to the selected category.

Version 0.13.194 adds Memory Studio with a visual Memory Database, custom categories,
reusable note-card templates, and guided local note management.
