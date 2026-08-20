ZBRANO v0.12.92 fixes an empty History and Event Timeline after device control by always prioritizing entities from the live state-change journal, merging them with the current selection, and displaying live-capture connection and journal counts.

ZBRANO v0.12.91 migrates two-way Telegram replies from the deprecated `target` field to `chat_id` and adds consistent searchable Home Assistant entity pickers throughout Automations, including multi-entity signal selection.

ZBRANO v0.12.90 activates the event-driven Real Automation Engine with structured triggers, presence checks, cooldowns, rate limits, evidence-backed suggestions, approval controls, and selectively autonomous reversible actions. It also repairs History and Event Timeline with an immediate live-event journal, resilient Recorder/Logbook merging, correct entity-ID mapping, automatic recent-activity loading, adds appointment deletion to the Month view, and uses dark-green completed reminders in the light theme.

ZBRANO v0.12.88 carries reminder state into the Month view: each appointment inside a day shows Pending, Completed, Attention, or No reminder, while selected-day cards show aggregate status and individual reminder badges.

ZBRANO v0.12.89 adds a secure two-way Telegram Inbox using Home Assistant event subscriptions, one-time chat pairing, persistent Telegram conversations, deterministic remote commands, and a separate remote-approval policy. Home Assistant continues to own the bot token, and idle monitoring never calls the AI model. It also includes v0.12.88 Month-view reminder status indicators and the v0.12.87 reminder history improvements.

ZBRANO v0.12.86 adds preview-first two-way Google Calendar synchronization through the standard Calendar API. Google events appear in ZBRANO's visual calendar, future ZBRANO appointments can be uploaded, linked cancellations propagate, and local Notification Center or Telegram reminders remain independent. Gmail and Calendar use separate OAuth grants and least-privilege scope sets.

ZBRANO v0.12.76 adds bounded, read-only Home Assistant History and Event Timeline intelligence: Recorder trends, Logbook search, multi-entity correlation, deterministic anomaly summaries, a visual timeline workspace, real diagnostics, and isolated chat routing for approved entities. v0.12.75 compacts the header, navigation, and chat composer to give conversations more space.

ZBRANO v0.12.72 improves natural voice prosody by preserving real punctuation, combining short phrases, and avoiding artificial TTS request boundaries at ordinary spaces while retaining streamed playback and next-segment prefetch.

ZBRANO v0.12.71 adds a dedicated Calendar with conversational appointment creation, upcoming and reminder views, a compact header shortcut, and scheduled Notification Center delivery through configured channels such as Telegram.

ZBRANO v0.12.70 keeps voice playback starting while response text is still streaming and pre-generates the next spoken segment during current playback, removing the multi-second pause between sentence-sized TTS requests.

ZBRANO v0.12.69 routes grinder freeze, reboot, telemetry, and incident prompts exclusively to the local read-only grinder diagnostic tools. It retrieves the stored pre-failure window instead of asking for an export and treats a later manual POWER ON reset as operator-caused when the user identifies it that way.
