# ZBRANO for Home Assistant

**A private, permission-aware assistant for conversation, home intelligence, and visual automation.**

Current release: **0.13.183**
Platform: **Home Assistant · aarch64**

ZBRANO brings the parts of an intelligent home into one understandable workspace.
Talk naturally, inspect live Home Assistant context, build visual automations, keep
useful local memory, and decide exactly which devices the assistant may read or
control.

## What ZBRANO brings together

| Capability | What it means in everyday use |
| --- | --- |
| **Conversation and voice** | Separate saved conversations, file attachments, optional web sources, speech replies, wake phrase, and follow-up listening. |
| **Home awareness** | Live sensor readings, device states, rooms, labels, history, and event timelines from explicitly permitted Home Assistant entities. |
| **Visual automations** | Automation Studio uses understandable WHEN, IF, ELSE IF, message, and action paths with safe testing before saving. |
| **Memory and organization** | Private Fast Memory, optional Workshop Memory, shared files, contacts, birthdays, appointments, and reminders. |
| **Connected services** | Optional plugins and integrations for services such as Google Calendar, Contacts, Gmail, GitHub, and Telegram. |
| **Safety and ownership** | Sensor or Control access per entity, branch-level authority, presence checks, quiet hours, approvals, audit history, backups, and recovery tools. |

Every capability is optional beyond the required AI connection. Start with chat and
a few Sensor devices, then add control, automation, voice, memory, or connected
services only when they are useful.

## From installation to useful action

1. **Install ZBRANO** in Home Assistant.
2. **Connect the AI service** with your own OpenAI API key.
3. **Choose device access** one entity at a time as Sensor device, Control device,
   or Do not allow.
4. **Start a conversation** or build a visual automation and try it safely before
   enabling it.

The in-app **About** page presents the complete experience, while guided **Setup**
checks each required connection and explains anything that still needs attention.

## Installation

1. In Home Assistant, open **Settings → Apps → App store**.
2. Open the repository menu and add:
   `https://github.com/RoyceGith/ZBRANO_HA_Assistant`
3. Select **ZBRANO**, install it, and add the required OpenAI API key.
4. Open **Settings → Apps → ZBRANO → Configuration**.
5. Enter your own OpenAI API key in **OpenAI API key** (`openai_api_key`), save, and restart ZBRANO.
6. Open ZBRANO, follow **Setup**, and choose Sensor or Control access only for the
   Home Assistant devices you want it to use.

ZBRANO currently publishes an `aarch64` image, intended for systems such as a
Raspberry Pi 5 running Home Assistant OS. Optional provider fields may remain blank.

## Permission model

Newly discovered Home Assistant entities receive no access automatically. You choose:

- **Sensor device** — ZBRANO may read its state but cannot control it.
- **Control device** — ZBRANO may read it and use explicitly configured actions.
- **Do not allow** — the entity remains unavailable to ZBRANO.

Automation authority is also selected where an executable branch is created. A path
may notify, ask before acting, or run automatically beneath built-in safety limits.
Test Flow evaluates current conditions without performing real actions.

## Data and connected services

ZBRANO runs as a Home Assistant app. Persistent assistant data stays in its
Supervisor-managed data area, and credentials stay in protected app configuration.
External providers are contacted only for capabilities you configure and use.

The public repository is intentionally a thin installer and update channel. The
application is delivered as the prebuilt
`ghcr.io/roycegith/jarvis-ha-assistant` image; this tree contains only Home Assistant
metadata, configuration presentation, and documentation.

## Updates and existing installations

Existing installations keep the same app slug, configuration, persistent `/data`
storage, and image path. Updating does not require uninstalling ZBRANO.

Version 0.13.183 replaces the former release-diary landing page with this concise
product and installation guide. The complete release history remains available in
the [app changelog](jarvis/CHANGELOG.md).

## Support and troubleshooting

- Open **Setup** to recheck required connections and follow focused recovery steps.
- Use **Settings → Installation Report** for a sanitized status summary that can be
  copied or downloaded without credentials or personal entity values.
- Check the Home Assistant app log when ZBRANO cannot start or connect.
- Report reproducible product problems through
  [GitHub Issues](https://github.com/RoyceGith/ZBRANO_HA_Assistant/issues).

When reporting a problem, include the ZBRANO version, Home Assistant version,
architecture, the relevant log section, and the sanitized Installation Report.
