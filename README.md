## ZBRANO v0.13.160

ZBRANO combines Home Assistant chat, voice, entity control, memory, notifications,
calendar and contact tools, plugins, and evidence-based automations. Automation Studio now uses
a visual building-block toolbox, interactive node canvas, and contextual inspector;
the established automation engine and stored definitions remain compatible.

Version 0.13.160 fixes nested task device selection so choosing a Home Assistant
entity replaces the partial search text and the flow card displays its complete
friendly name. Partial queries can no longer be saved as configured devices.

Version 0.13.159 moves message delivery into each IF and ELSE IF branch. Every
branch can independently say its message aloud, show it in ZBRANO notifications,
or send it through Home Assistant notifications. The redundant This path runs
when selector is removed; all checks inside a branch are joined with AND.

Version 0.13.158 removes the duplicate editable IF and ELSE IF title cards, so
each branch begins directly with its own device or sensor condition. Speaking
branches now keep separate required messages, Monitor silently removes messages,
and task menus open upward when they are near the bottom of the Studio window.

Version 0.13.157 restores current readings in every Automation Studio device
dropdown. Results show the entity name and ID beside a clear state or measured
value badge, including sensor units and current climate temperatures.

Version 0.13.156 makes IF and ELSE IF device checks use the selected entity's
state by default. Optional Home Assistant attributes are preserved in a collapsed
advanced section instead of showing a confusing Which value field.

Version 0.13.155 makes Automation Studio more spacious by moving Setup & safety
and the guided-step progress into a slim line above the block palette. The top
palette now contains only real flow blocks, and its main action buttons are smaller.

Version 0.13.154 keeps Power turns on and Power turns off selected for every
entity that reports an on/off state. Power events now show only the device and
optional duration, without redundant action and comparison fields.

Version 0.13.153 moves Automation Studio's block toolbox above the canvas and
groups shortcuts into WHEN Events, IF Conditions, THEN Actions, and ELSE IF
Paths. IF starts a condition group; AND/OR connects additional conditions.

Version 0.13.152 adapts response choices to the selected device type. Sensor
devices offer Monitor silently or Notify me; Control devices offer Ask me first
or Do it automatically, removing overlapping authority wording.

Version 0.13.151 replaces abstract device-risk levels with two direct choices:
Sensor device for read-only observation and Control device for automations that
can change something. Action-only safety settings now appear only when relevant.

Version 0.13.150 adds a per-automation Require presence gate to Setup & safety
and replaces the optional-results prompt with direct IF / ELSE IF paths. Adding
the first ELSE IF keeps existing And checks and Then tasks connected in the
first path, while each new path has its own check, message, and task.

Version 0.13.149 gives every When block a clear event type: Sensor, Power on,
Power off, Time, Sun, Repeat, or One time. Selecting a flow card now shows only
that block's settings. Automatic automations no longer display disconnected Say
cards or message controls.

Version 0.13.148 stabilizes the aarch64 image build by testing Undo against a
deliberately committed edit and waiting for persisted recovery state instead
of CPU-dependent timing. Application behavior is unchanged from v0.13.147.

Version 0.13.147 puts safety and authority directly in Step 1 of every
automation. Each rule now clearly chooses whether ZBRANO watches, suggests,
asks first, or acts automatically, together with its impact and safety limits.
The global authority screen is removed from normal navigation while built-in
protections remain underneath as a hard ceiling.

Version 0.13.146 repairs Automation Studio save feedback. Name and purpose
validation now matches the server before submission, and any structured server
validation response is translated into readable field-specific messages instead
of `[object Object]`.

Version 0.13.145 makes the optional final Automation Studio step understandable
without removing the visual flow. It asks whether another situation needs a
different result, then presents each result as plain When / Then content with an
explicit fallback. The branching engine and existing saved automations remain
compatible.

Version 0.13.144 stabilizes the ARM image browser gate by waiting for the
debounced Automation Studio history snapshot itself before testing Undo. This
removes a builder-speed race without changing application behavior.

Version 0.13.143 makes Then task-first for new automations. Common users choose
icon-based actions such as Turn on, Set temperature, Notify, or Wait without
seeing raw Home Assistant commands. Custom commands remain available through an
Advanced disclosure, and flow cards and confirmations use friendly action names.

Version 0.13.142 turns the Studio guide into a true guided setup. New automations
begin at Name it, Back and Next controls lead through all five steps, and required
information is explained before the user can continue. The final step points to
safe testing or saving while direct canvas and drag-and-drop editing remain intact.

Version 0.13.141 turns the numbered Automation Studio steps into a live guide.
Required steps show Ready or Needs attention, while optional steps show their
current check, task, or outcome count. Validation, saved-automation summaries,
and activation confirmation now use everyday language instead of internal terms.

Version 0.13.140 continues the Automation Studio usability reconstruction. Every
additional When, Only if, and Then card now explains each field in everyday
language. Confidence tuning and safety limits stay available inside discreet
expandable sections, alternate paths are consistently called Outcomes, and the
main actions now say New automation, Try it safely, and Save automation.

Version 0.13.139 begins the Automation Studio usability reconstruction without
removing its flow. A numbered Name → When → Only if → Then → Outcomes guide now
sits beside the interactive canvas. Flow cards use device-aware icons, friendly
names, and concise symbols such as `> 26 °C`; advanced behavior remains available
under plain-language labels and existing automation definitions stay compatible.

Version 0.13.138 fixes entity selection for additional Automation Studio triggers.
Clicking a second or later Trigger card now focuses that trigger's relevant field
and loads its Home Assistant entity picker instead of focusing the generic type selector.

Version 0.13.137 replaces circular arrival halos with brief electrical sparkles.
Signals now finish as a tiny four-point flash centered on the destination neuron,
without drawing extra circles or rings around it.

Version 0.13.136 removes the remaining blue tint from resting neuron interiors.
Every theme now uses an equal-channel neutral grayscale core, while blue remains
limited to connections, outlines, moving signals, and their arrival halos.

Version 0.13.135 gives each arriving neural signal a distinct destination flash.
The neuron briefly lights with a compact warm-white core and a small blue halo,
making the firing event readable without brightening the resting node interior.

Version 0.13.134 makes neural firing visible without making the backdrop noisy.
Connection impulses now render above the neuron bodies, arrive more regularly, and
produce a clearer inner-node flash. Neuron centers use a more neutral charcoal to
slightly reduce their blue tint.

Version 0.13.133 adds discreet neural firing signals to the active backdrop. A small
number of faint impulses travel along existing connections and briefly illuminate
their destination nodes, while the v0.13.132 pause rules keep active chats and text
selection free from animation work.

Version 0.13.132 stops the neural backdrop animation as soon as a chat begins and
the nodes return to their configured visibility. It also pauses the animation while
chat text is selected and whenever the chat is hidden, eliminating competing canvas
work without removing the static neural image.

Version 0.13.131 replaces the remaining green interface palette with the same
theme-aware blue used by the Talk button. Primary accents, glows, controls,
background tints, status highlights, and the animated neural backdrop now use one
consistent blue family across dark, light, and gray themes.

Version 0.13.130 makes the visual workflow match its real logic: a compact watcher
stage wakes the automation, followed by explicit IF, ELSE IF, and ELSE paths.
Every condition now exposes its entity, state or attribute, operator, required or
comparison value, and sustained duration. Existing saved automations remain compatible.

Version 0.13.128 repairs the container browser gate on slower ARM builders by
making an Automation Studio delete interaction deterministic. Application behavior
and stored data are unchanged from v0.13.127.

Version 0.13.127 turns Birthdays into a single People directory with the next
birthdays at the top and colored month sections below. Birthdays saved through
chat now default to reminders one week and one day before, including saves made
through a linked Contact; existing reminder choices are preserved.

Version 0.13.126 keeps recurring Birthday cards intact when reminder notifications
are delivered. Reminder results now merge into current storage, and a linked Contact
can safely restore a missing Birthday record without losing the Contact.

Version 0.13.125 keeps an automation's Objective separate from its process task.
New flows now ask for an actual suggestion or task in the Do This card instead of
incorrectly repeating the Objective.

Version 0.13.124 simplifies Automation Studio into plain Check, If, and Do steps,
renames the visible Context block to Condition, removes explanatory clutter from
process cards, and shows each entity's complete friendly name and entity ID.

Version 0.13.123 restores searchable Home Assistant entity pickers for Context
presence, Context signals, and Action entities in Automation Studio. Contacts now
appears immediately to the right of Calendar in primary navigation.

Version 0.13.122 restores independent Contacts scrolling and adds remembered
Cards, List, and Compact directory arrangements without changing contact data.

Version 0.13.121 makes the container browser gate deterministic by explicitly
marking the exercised notification as read before asserting the unread badge.
Application behavior and stored data are unchanged.

Version 0.13.120 repairs Google Contacts import failures. Google People API or
permission problems now return an actionable message instead of HTTP 500, malformed
individual records are skipped without cancelling the whole import, and fields
already stored locally are preserved when Google does not provide replacements.

Version 0.13.119 adds the Contacts directory, CSV/vCard and read-only Google imports,
Birthday synchronization, and numbered chat disambiguation.

The application source and post-split build history are maintained in the private
core repository. Public Home Assistant repositories contain only the five-file
installer and update metadata needed to deliver the prebuilt image.

ZBRANO v0.13.56 reconnects the thin public installer branch to the last previously public source commit so Home Assistant Supervisor can fast-forward its cached repository checkout and detect updates without uninstalling.

ZBRANO v0.13.18 prevents Release Memory synchronization from remaining indefinitely in a non-terminal state by adding worker timeout recovery, note progress, task-health reporting, and automatic interface polling.

ZBRANO v0.13.17 separates local appointments/reminders and Google Calendar synchronization into explicit backend domains while preserving routes, OAuth state, sync tokens, reminder delivery, worker lifecycle, and stored calendar data.

ZBRANO v0.13.16 moves the stateful Automation Brain and Notification Center engines into explicit backend domain modules while preserving their routes, shared watch storage, lifecycle, and persisted data formats.

ZBRANO v0.13.15 begins the canonical architecture split by extracting ordered frontend assets, API schemas, the Home Assistant transport, and low-coupling backend services while preserving `app.main:app`, API routes, stored data formats, and existing behavior.

ZBRANO v0.13.14 correctly decodes structured MCP results and tool errors, compacts only ZBRANO-managed v0.13 release blocks into concise descriptions, and prevents Release History from exceeding Workshop Memory's note-size limit.

ZBRANO v0.13.13 verifies ambiguous Workshop Memory release-note writes by reading the saved note back, preventing successful reconciliation from being reported as a missing-status failure.

ZBRANO v0.13.12 refreshes the application navigation, nested menus, cards, forms, and data tables with a cleaner modern visual system while preserving the established chat experience and all existing behavior.

ZBRANO v0.13.11 links Home Assistant Areas to geographic Zones through site Labels, applies label-defined entity roles and safety boundaries, and keeps learned room context aligned when HA organization changes.

ZBRANO v0.13.10 adds Home Assistant Area awareness and a local passive-learning loop that discovers room-level opportunities, suggests safe actions from evidence, and learns from approval, dismissal, and explicit preferences.

ZBRANO v0.13.9 adds an Automation Brain workflow that turns natural-language requests into reviewable structured drafts, remembers confirmed entity mappings, separates Create New from Library, and speaks only the configured suggestion wording.

ZBRANO v0.13.8 restores independent vertical and horizontal scrolling in the Entities inventory and keeps the History view bounded inside the panel.

ZBRANO v0.13.7 lets either Talk or the opted-in local “Hey ZBRANO” detector interrupt response generation and playback, then safely opens microphone capture for a replacement prompt.

ZBRANO v0.13.6 prevents cancelled microphone starts from reinstalling stale listeners, re-arms short or failed captures, and actively reconnects conversation listening when any browser audio component stops responding.

ZBRANO v0.13.5 prepares the first natural phrase while response text is still arriving, prefetches later speech, and starts adjusted-rate audio once an adaptive safety buffer and sustainable download rate are available.

ZBRANO v0.13.4 keeps adjusted-rate speech stable by fully buffering it before playback, locking the chosen rate when audio metadata loads, and avoiding speed changes in the middle of a spoken segment.

ZBRANO v0.13.3 verifies and recovers the live microphone path before showing conversation follow-up listening, prevents stale noise calibration from suppressing speech capture, and adds an adjustable 0.80×–1.40× speech playback speed.

ZBRANO v0.13.2 preserves the beginning of each spoken command, reliably re-arms follow-up conversation capture, cleans up expired listening windows, and centers compact microphone-RMS-responsive sound bars above the prompt without adding a visual frame.

ZBRANO v0.13.1 keeps voice interaction inside the chat workspace with a compact listening animation, recognizes configured conversation-closing phrases across common transcription variants, and finalizes spoken commands promptly after real post-speech silence without allowing steady room noise to prolong capture.

ZBRANO v0.13.0 promotes the complete generated application into canonical source. The image now builds directly from the reviewed backend and frontend instead of reconstructing the product through 147 historical patch scripts, while preserving the validated v0.12.112 behavior.

ZBRANO v0.12.112 captures spoken commands after local wake activation and groups the always-listening, local-model activation, and conversation controls together in the hands-free settings.

ZBRANO v0.12.111 optionally lets the local Hey ZBRANO model open the command interface and provides a bounded hands-free follow-up conversation window after voice-originated replies.

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
