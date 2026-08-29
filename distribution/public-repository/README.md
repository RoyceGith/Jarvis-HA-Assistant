# ZBRANO for Home Assistant

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

Version 0.13.81 includes a full-window Automation Studio with a building-block
toolbox, interactive flow canvas, and focused settings inspector. Existing
automation definitions and Home Assistant data remain compatible across updates.
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
