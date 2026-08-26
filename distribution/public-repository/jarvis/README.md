# ZBRANO

ZBRANO is a Home Assistant intelligence assistant with chat, voice, entity control,
automations, notifications, calendar integration, local memory, and optional plugin
connections.

## Automation Studio

Version 0.13.74 provides a full-window visual automation builder with Trigger, Context,
Decision, and Action blocks, a node canvas, and block-specific settings. The full
Advanced editor remains available, existing stored automations are preserved, and
repeatable OR triggers, grouped conditions, ordered actions, and IF/ELSE branches
are supported, together with dedicated Delay and bounded Wait Until steps. Each
automation can use the global operating default or select its own lower authority,
plus voice, Studio inbox, and Home Assistant push delivery.
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

After installation, configure your own service credentials and explicitly approve
the Home Assistant entities ZBRANO may read or control. Personal data and runtime
configuration remain in your Home Assistant installation.
