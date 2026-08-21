ZBRANO v0.12.110 removes the full-screen horizontal scanline overlay from every theme while preserving the neural background and functional component borders.

ZBRANO v0.12.109 installs the real-room-trained Hey ZBRANO v2 wake model for silent shadow evaluation, improving validated personal wake-phrase detection from 10/21 to 20/21 while retaining non-activation safety.

ZBRANO v0.12.108 repairs the validated wake-calibration image build by replacing a punctuation-dependent legacy source match with an encoding-independent patch boundary.

ZBRANO v0.12.107 waits for actual speech during wake calibration, validates recording quality before saving, audits existing samples, and removes or excludes silence, weak audio, and clipping without deleting valid recordings.

ZBRANO v0.12.106 separates microphone delivery from model recognition with live RMS/peak measurements and bounded phrase tests, and exports preserved calibration recordings as a structured ZIP for Hey ZBRANO v2 training.

ZBRANO v0.12.105 restores the broader base wake model by default, makes the trained personal verifier an explicit opt-in filter, and allows deleting only the verifier while preserving every recorded calibration clip.

ZBRANO v0.12.104 separates wake-sample uploads from the static verifier-training endpoint so Train personal verifier cannot be misrouted as an audio label, and renders structured API failures as readable messages instead of `[object Object]`. Existing private calibration samples are preserved.

ZBRANO v0.12.103 adds explicit personal wake calibration: 20 user-triggered Hey ZBRANO recordings, 20 user-triggered ordinary-speech recordings, optional false-trigger evidence, local verifier training, persistent private add-on storage, and verifier-aware shadow evaluation. No calibration audio is saved unless its recording or false-trigger button is pressed.

ZBRANO v0.12.102 bundles OpenWakeWord's shared ONNX mel-spectrogram and embedding models and loads them from explicit local paths, repairing the v0.12.101 shadow detector startup failure without adding network inference or audio retention.

ZBRANO v0.12.101 adds calibrated RMS-plus-peak voice detection, an independent recording hard stop, explicit audio finalization, non-speech transcript rejection, and a silent local OpenWakeWord shadow test with live confidence and false-detection statistics. Shadow mode never activates chat, retains no audio, and makes no OpenAI transcription request.

ZBRANO v0.12.100 makes the bounded reliable wake listener Chrome's primary path, exposes voice-detection stages, and prevents noise-triggered transcription bursts through an unbiased wake endpoint, stronger speech gating, hallucination rejection, and cooldown controls.

ZBRANO v0.12.99 creates and finalizes a fresh browser audio container for each detected wake utterance, preventing corrupt transcription uploads, and removes the obsolete voice/history helper label to reclaim composer width.

ZBRANO v0.12.98 adds a bounded reliable wake fallback: local browser voice activity detection transcribes only short detected utterances when Chrome returns no speech result, with an hourly safety limit and no retained audio.

ZBRANO v0.12.97 repairs Chrome wake activation by matching interim recognition, the configured phrase, and conservative phonetic forms of ZBRANO while displaying what Chrome heard.

ZBRANO v0.12.96 presents an animated, accessible listening overlay after the wake phrase is detected, including recognized-command feedback, timeout progress, and cancellation.

ZBRANO v0.12.95 repairs Entities scrolling, replaces the obsolete Workshop Memory session-draft write with an approval-safe downloadable entity-inventory update draft, and stops unsupported Brave wake recognition from cycling continuously.

ZBRANO v0.12.94 speaks newly generated autonomous suggestions, accepts a short spoken approve-or-decline response, and adds an optional browser wake phrase for hands-free commands while ZBRANO remains open.

ZBRANO v0.12.93 makes History reliably populate from approved current-state evidence as well as live changes, and correctly confirms climate activation when Home Assistant reports an HVAC mode such as `cool` instead of generic `on`.

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
