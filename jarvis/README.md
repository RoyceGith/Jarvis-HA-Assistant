# ZBRANO

![ZBRANO](logo.png)

**Conversation, home intelligence, and visual automation—with permissions you control.**

ZBRANO is a private Home Assistant intelligence assistant. It combines natural
conversation, live home context, voice, useful memory, notifications, organization,
and automation in one interface without granting itself access to every device.

Version 0.13.213 preserves automatic memory-note structure, upgrades older
list-wrapped entries, and keeps bold numbered instructions in ordered lists.

Version 0.13.212 updates About into a polished multilingual showcase of ZBRANO's
complete feature set, with direct shortcuts into Memory and Shared Files.

Version 0.13.211 refreshes Shared Files with a refined private-library layout,
clear action hierarchy, polished file rows, and responsive controls.

Version 0.13.210 organizes Shared Files into navigable folders, supports uploads
to the open folder, and moves existing files safely between folders.

Version 0.13.209 gives the My Memory front page a compact top section and brings
saved spaces upward with smaller, clearer labels and cards.

Version 0.13.208 renders memory notes with chat-style headings, bold text, and
lists, adds visible last-updated dates, and prints the same formatted content.

Version 0.13.207 prints the memory space name as a smaller clean heading without
the interface's decorative greater-than sign.

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

The in-app **About** tab provides a visual overview of ZBRANO's complete feature set.
