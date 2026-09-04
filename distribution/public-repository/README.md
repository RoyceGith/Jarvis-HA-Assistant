# ZBRANO for Home Assistant

Current release: **0.13.145**

This is the public Home Assistant installation and update repository for ZBRANO.
The application is delivered as a prebuilt container image. The current repository
tree contains no application source. Legacy commits that were already public and
the initial thin-distribution branch remain as merge ancestry for Home Assistant
update compatibility; post-split source and build history remain private.

## Installation

1. In Home Assistant, open **Settings → Apps → App store**.
2. Open the repository menu and add:
   `https://github.com/RoyceGith/ZBRANO_HA_Assistant`
3. Select **ZBRANO**, install it, configure the required credentials and entity
   permissions, then start the app.

Existing ZBRANO installations retain the same add-on slug, configuration, `/data`
storage, and `ghcr.io/roycegith/jarvis-ha-assistant` update image.

## Current experience

Version 0.13.138 fixes Automation Studio entity loading when a second or later Trigger
card is selected by focusing and opening the correct trigger-specific field.

Version 0.13.137 replaces circular neural arrival effects with tiny electrical
sparkles, so signals flash at destination neurons without producing rings.

Version 0.13.136 removes the remaining blue tint from resting neuron interiors while
retaining blue connections, signal motion, outlines, and arrival halos.

Version 0.13.135 makes each neural signal visibly flash inside its destination node
with a compact bright core and discreet halo.

Version 0.13.134 makes neural firing clearly visible above the node bodies while
keeping it discreet, and reduces the blue tint inside neurons with a more neutral
charcoal center.

Version 0.13.133 adds sparse, discreet neural firing signals that travel along active
connections and briefly illuminate destination nodes without running during paused
chat states.

Version 0.13.132 stops the neural backdrop animation after a chat begins, while chat
text is selected, and when the chat is hidden. The configured static backdrop remains
visible and empty new-chat screens retain their ambient animation.

Version 0.13.131 unifies the interface around the Talk button's theme-aware blue,
replacing the remaining green accents, glows, surface tints, and neural backdrop
colors across all themes.

Version 0.13.130 clarifies Automation Studio as watcher events followed by executable
IF, ELSE IF, and ELSE paths, with complete value, attribute, comparison, and
duration controls on every condition.

Version 0.13.128 repairs the slower ARM container browser gate so the Home
Assistant image can publish. Runtime behavior and stored data are unchanged.

Version 0.13.127 shows the nearest birthdays above a colored month-by-month People
directory. Birthdays saved through chat default to reminders one week and one day
before while existing reminder choices remain unchanged.

Version 0.13.126 preserves recurring Birthday cards after notifications and repairs
a missing Birthday record from its linked Contact.

Version 0.13.125 keeps the Objective out of the Do This process card and clearly
prompts for an actual suggestion or task in new flows.

Version 0.13.124 simplifies Automation Studio flows into direct Check, If, and Do
steps, renames the visible Context block to Condition, and shows complete entity
names and IDs on cards.

Version 0.13.123 restores entity loading in Automation Studio's Context and Action
inspectors and places Contacts immediately after Calendar.

Version 0.13.122 restores Contacts scrolling and adds remembered Cards, List,
and Compact directory arrangements.

Version 0.13.121 repairs a timing-sensitive container browser validation so the
multi-architecture image build can complete reliably. Runtime behavior is unchanged.

Version 0.13.120 repairs Google Contacts imports with actionable Google People
API errors and resilient per-contact handling.

Version 0.13.117 moves My Automations and Automation Memory into dedicated,
indented Studio navigation entries. Saved automations stay compact and expose
their visual flow only through an independent expand control.

Version 0.13.115 restores the searchable Home Assistant entity picker in
Automation Studio's WHEN-card inspector while preserving existing workflow data.

Version 0.13.114 makes climate entities more informative in Entity Inventory by
showing the HVAC mode and configured target temperature together, such as
`cool · set to 25 °C`. Current temperature and active HVAC action are retained as
detail without changing Home Assistant control or stored-data behavior.
Incomplete blocks remain protected by validation, and existing automation
definitions and Home Assistant data remain compatible across updates.
Conversational creation now reuses known Home Assistant Area-to-Zone links and
approved person or device-tracker presence sources for location-aware rules.
Studio now reports live entity-permission and Home Assistant safety-label readiness,
blocking unsafe approval or autonomous execution until access is restored.
Each automation also exposes a bounded decision journal explaining its latest
observations, suppressions, deferrals, suggestions, and action outcomes.
The graphical Studio now appears first, Settings uses a collapsible icon-led left
navigation with color accents, and the primary top bar uses quiet hover targets.
Form controls remain compact on wide screens, Automations shares the sidebar style,
and Voice plus other full-height workspaces scroll reliably.
Studio edits can now be undone and redone from visible controls or standard keyboard
shortcuts, with bounded history that never changes saved automation authority.
An unsaved flow also recovers after an accidental refresh using an expiring,
size-bounded record local to the Home Assistant browser origin.
Live issue chips and canvas markers now identify incomplete blocks, navigate to the
correct inspector, and prevent incomplete drafts from being tested or saved.
An Unsaved changes badge and replacement confirmation protect the current flow from
accidental New, template, edit, or cancel actions.
My Automations now has compact search across rule and workflow content, practical
state filters, live result counts, and clear no-match feedback for larger libraries.
Rules can be sorted by recency, name, active state, or attention priority, and the
selected Studio library view, filter, and sort are remembered locally.
Live visual summaries show all, active, attention-needed, draft, and automatic rule
counts and act as one-click filters synchronized with the state selector.
My Automations can switch between the full Detailed workflow view and a remembered
responsive Compact card grid that keeps names, states, and editing actions visible.
Any saved rule can be duplicated into an independent disabled Studio draft. The
original identity is removed and nothing is stored until the copy is reviewed and saved.
Active rules can be paused directly without losing their definition or history, and
paused rules resume through the existing guarded activation checks.
Pre-Studio simple automations are now exercised by a build-gated restore, load, and
current-schema save path that verifies their original identity and behavior remain intact.
A complete build-gated backup round trip also verifies Settings, chats, entity policy,
automations, notifications, calendar, and Fast Memory restore together without secrets.
The owner-specific Grinder extension is hidden from UI, chat routing, AI tools, and
incident APIs unless its existing Home Assistant option is explicitly enabled.
Visual workflows can use OR triggers, grouped conditions, ordered actions, and
first-match IF/ELSE branches, Delay steps, and bounded Wait Until steps. Every
automation can independently observe, suggest, ask approval, or act automatically
beneath the global safety ceiling, with per-rule delivery choices.
Test Flow evaluates an unsaved draft against current Home Assistant context and
shows a four-stage trace without executing any action.
Visual workflows can run at selected local times and weekdays, sunrise or sunset
offsets, repeating intervals, or a one-time date and time. Time windows, weekdays,
sun state, and sustained entity states are available as graphical conditions.
Selecting Not now remembers the observed trigger context: improving or nearly unchanged
numeric conditions do not repeat the same suggestion. Rules re-arm after the
configured reset boundary, while active episodes show their direction, current
and worst readings, and sample count. Optional per-rule worsening and reset margins
allow tuning without changing existing automation defaults.
Configured actions already satisfied in Home Assistant are not proposed again.
Repeated Not now feedback now gradually postpones future suggestions for that
specific automation. Approvals and matching manual actions clear the added
restraint, and Automation Studio explains or resets the learned feedback without
changing permissions, authority, or episode history.
Each rule also has a response window so unanswered suggestions expire rather than
blocking future evaluation. Interrupted executions recover as visible failures,
and Studio reports expirations, automatic successes, and action failures without
automatically retrying actions.
Repeated action failures now open a configurable per-rule circuit that pauses
approval and autonomous execution. Studio explains the circuit and requires an
explicit recovery reset while retaining historical failures and existing safety
boundaries.
