# ZBRANO v0.13.153

Automation Studio provides a graphical, step-by-step workflow for Home Assistant
automations. Use Setup &amp; safety, When, Only if, Then, and optional Outcomes beside the
interactive flow canvas. Natural-language creation, templates, drag-and-drop,
saved automation compatibility, and the full Advanced editor remain available.

Version 0.13.153 replaces the left toolbox with a categorized top block bar,
giving the flow canvas more horizontal room. Event, condition, and action chips
insert typed blocks directly, including into a selected ELSE IF path.

Version 0.13.152 gives Sensor devices the Monitor silently and Notify me choices,
while Control devices show Ask me first and Do it automatically. Older saved
authority choices are safely normalized when reopened.

Version 0.13.151 uses only Sensor device and Control device in each automation's
setup. Action limits, completion notices, and reversible-action restrictions
are shown only when that automation can actually control a device.

Version 0.13.150 adds Require presence and its entity picker directly to the
first step. The final step is now a direct IF / ELSE IF path builder with a
visible canvas fork. Existing And checks and Then tasks automatically become
the first connected IF path when a second path is added.

Version 0.13.149 adds dedicated Sensor, Power on, Power off, Time, Sun, Repeat,
and One time cards to the When step. The inspector edits only the selected When
block, and automatic flows omit Say cards and message controls because those
elements are not connected to an automatic action path.

Version 0.13.148 makes the aarch64 image browser gate deterministic by applying
and persisting a dedicated edit before testing Undo and Redo. Recovery now
waits for observed persisted state rather than a fixed CPU-speed delay.
Application behavior remains the same as v0.13.147.

Version 0.13.147 moves authority and safety into the first step of each
automation. Watch, suggest, approval, or automatic behavior is selected for
that rule together with its impact, hourly limit, reversibility, and action
notification. The global authority screen no longer appears in normal
navigation, while built-in safety protections remain enforced underneath.

Version 0.13.146 aligns the guided name and purpose checks with the server's
save requirements and translates structured validation failures into readable,
field-specific explanations instead of `[object Object]`.

Version 0.13.145 replaces the technical Outcomes setup with an optional
Different results question. When enabled, each result is edited with direct
When / Then language, readable all/any choices, and a clearly explained
fallback while the graphical flow and stored branch schema stay intact.

Version 0.13.144 makes ARM image validation deterministic by waiting until the
debounced Studio edit is present in persisted history before exercising Undo.
Application behavior is unchanged from v0.13.143.

Version 0.13.143 replaces blank raw action fields in new flows with an icon-based
task chooser. Ready-made tasks expose only useful settings, custom Home Assistant
commands live under an Advanced disclosure, and cards, summaries, and activation
confirmation translate known commands into readable actions.

Version 0.13.142 adds a guided Back and Next path through the five Studio steps.
New drafts start with Name it, required information blocks progression with a
plain explanation, optional steps remain optional, and Review and finish points
the user to safe testing or saving. The visual flow remains fully interactive.

Version 0.13.141 adds a live completion guide to the five Studio steps. Each step
shows whether it is ready, needs attention, remains optional, or contains saved
items. Common validation, library, and activation messages now avoid internal
automation terminology while the full editor remains available.

Version 0.13.140 gives repeatable triggers, checks, and tasks complete
plain-language labels. Fine-tuning and safety controls are collapsed until
needed, outcome terminology is consistent, and toolbar actions describe their
effect. The full visual flow and every advanced setting remain available.

Version 0.13.139 keeps the visual flow central while making it easier to read.
Cards now use device-aware icons, friendly entity names, comparison symbols, and
IF / OTHERWISE outcomes. Technical settings use questions and everyday language.

Version 0.13.138 makes second and later Trigger cards open their own populated entity
picker when selected, with schedule triggers focusing their relevant schedule field.

Version 0.13.137 replaces circular signal-arrival effects with a brief four-point
electrical sparkle inside the destination neuron, eliminating extra rings.

Version 0.13.136 removes blue tint from resting neuron interiors across every theme.
Blue remains on the connection network, moving signals, outlines, and arrival halos.

Version 0.13.135 adds a distinct compact flash and expanding halo at the destination
neuron when a moving neural signal arrives, while leaving resting nodes subdued.

Version 0.13.134 renders neural impulses above the nodes with a clearer destination
flash and slightly more regular timing. Neuron interiors now use a more neutral
charcoal, reducing their blue tint while connections remain blue.

Version 0.13.133 adds sparse, faint impulses that travel along active neural
connections and produce a small arrival flash inside the destination node. The
effect remains off whenever neural animation is paused.

Version 0.13.132 keeps the configured neural backdrop visible but stops its animation
after chat begins, while chat text is selected, and while the chat workspace is
hidden. Empty new-chat screens retain the ambient animation.

Version 0.13.131 unifies the interface around the Talk button's theme-aware blue,
removing the remaining green accents, glows, tints, and neural-network colors in
dark, light, and gray themes.

Version 0.13.130 separates event watchers from executable conditions in the visual
flow. IF and ELSE IF cards now provide labelled state, attribute, operator, value,
entity-comparison, and duration controls while preserving existing definitions.

Version 0.13.128 makes the Automation Studio browser validation deterministic on
slower ARM container builders, restoring image publication without changing
runtime behavior or stored data.

Version 0.13.127 replaces the separate Upcoming Birthday view with a unified
People directory: the next birthdays appear first, followed by colored monthly
sections. Chat-created birthdays now default to reminders seven and one days
before without replacing reminder choices already saved by the user.

Version 0.13.126 preserves recurring Birthday cards through reminder delivery,
merges delivery status into the latest saved data, and repairs missing birthdays
from their linked Contacts.

Version 0.13.125 stops the Do This card from treating the Objective as an
executable task. An unconfigured new flow now clearly asks for a suggestion or
task.

Version 0.13.124 gives Automation Studio a simpler Check → If → Do reading order,
shows complete friendly names and entity IDs, and keeps process cards focused on
the task instead of implementation details.

Version 0.13.123 restores searchable entity pickers for Automation Studio Context
presence, Context signals, and Action entities, and places Contacts after Calendar.

Version 0.13.122 restores independent scrolling throughout Contacts and adds
remembered Cards, List, and Compact directory arrangements.

Version 0.13.121 repairs the container browser gate by making its notification
read-state check deterministic. Runtime behavior and stored data are unchanged.

Version 0.13.120 repairs Google Contacts imports with actionable Google People
API errors, isolated malformed-record handling, and preservation of local details.

The visual editor supports linear and branching workflows without silently changing
the behavior of existing stored rules.

## Earlier releases

### v0.12.14

Version 0.8.5 added clean Markdown rendering for ZBRANO chat replies and guides
assistant responses toward readable sections, spacing, bullets, and concise
paragraphs.

Version 0.8.4 starts text-to-speech from streamed response chunks instead of
waiting for the full assistant response to finish, so ZBRANO can begin speaking
much sooner.

Version 0.8.3 removes the core metrics rail from chat, replaces boxed
green/cyan message bubbles with a cleaner transcript style, streams first-pass
assistant replies progressively, and reduces voice playback lag with streamed
speech relay and lower-latency ElevenLabs defaults.

Version 0.8.2 makes the obsidian neural collective clearly visible through the
glass chat layer with stronger node definition, brighter short links, deeper
highlights, and reduced background blur. The neural field remains completely
unframed in all three themes.

Version 0.8.1 restores the obsidian neuron field behind chat after fixing its
canvas projection, while retaining the unframed perimeter introduced in v0.8.0.
Version 0.8.0 expanded Settings with ElevenLabs model/test/speaker boost,
auto-speak, response detail, cautious low-risk confirmation, conversation
context and retention, language/pronunciation, accessibility and density,
quiet hours, volume, and secret-free backup/restore. It also adds a modern gray
ZBRANO HUD, removes the circular neural frame, and places chat on a glass panel
over the obsidian node collective.

Version 0.7.5 adds persistent ElevenLabs Stability, Similarity, Style, and Speed
controls under ZBRANO Settings. The existing delivery values remain the defaults,
and saved values are applied server-side to every subsequent ElevenLabs request.

Version 0.7.4 adds device-persistent Light and Dark themes under Settings and
replaces the sparse background graph with a centered, depth-rendered collective
of hundreds of linked obsidian nodes inspired by the ZBRANO neural-core reference.

Version 0.7.3 adds a Settings tab with persistent General Instructions. The
instructions apply to every model response and survive app restarts/upgrades in
the add-on `/data` volume. ZBRANO can also append a behavior from chat when the
user explicitly asks to save or remember it as a standing instruction. Normal
examples and corrections are not saved automatically, and custom instructions
cannot weaken device permissions or safety rules.

Version 0.7.2 reduces response-to-voice delay by relaying ElevenLabs audio to
the browser as it is generated and playing MP3 chunks progressively. It uses
the low-latency `eleven_flash_v2_5` model by default. OpenAI and ElevenLabs
remain selectable, and ZBRANO can still retry a failed ElevenLabs response
with Cedar when `speech_fallback_to_openai` is enabled. The ElevenLabs key
never reaches the browser.

Required ElevenLabs settings:

- `elevenlabs_api_key`: API key created in ElevenLabs.
- `elevenlabs_voice_id`: ID shown for the selected or authorized custom voice.
- `elevenlabs_voice_name`: Browser label for the configured voice.
- `elevenlabs_model_id`: Defaults to low-latency `eleven_flash_v2_5`; use
  `eleven_multilingual_v2` when maximum expressiveness matters more than speed.

Do not paste the ElevenLabs key into ZBRANO's browser interface or chat.

Version 0.7.0 adds device-local push-to-talk voice. The browser records from
the microphone on the PC or phone, sends the bounded recording to ZBRANO for
transcription, routes the resulting text through the existing deterministic
Home Assistant and AI paths, and plays an AI-generated spoken response through
the same device. The OpenAI API key stays inside the add-on. Voice preferences
are stored per browser, and Stop interrupts both streamed text and playback.

Microphone access requires a secure browser context (HTTPS or localhost) and
the user must grant microphone permission to the Home Assistant/ZBRANO page.
The spoken voice is AI-generated.

Adds a terminal-style HUD with a lightweight Obsidian-inspired neural graph,
persistent browser prompt history navigated with the Up/Down arrow keys, and a
Stop control that cancels the active response stream on both client and server.

Version 0.6.5 stores conversations in Home Assistant's persistent add-on `/data`
volume and restores the active chat when ZBRANO is reopened. A conversation
sidebar supports opening, creating, and deleting saved chats. It also keeps
entity aliases persistent, includes the cyan intelligence-core HUD, and automatically enables
socket/outlet switches, climate/thermostat entities, and matching air-conditioner
status entities as approved low-risk entries. Other entity policies are unchanged.

Version 0.6.6 expanded the ZBRANO panel to the full available viewport. Alias
edits are synchronously backed up in the browser as well as saved to the add-on
policy. If Home Assistant navigation interrupts a pending request, ZBRANO
restores the local alias on return and repairs the persistent server policy.

## v0.6.0

Adds the first internal intent-routing layer.

## Root cause

Streaming requests were not passing the browser chat session ID into the
streaming assistant function, so all streamed requests used the default session.

## Fix

ZBRANO now passes the browser session ID through both streaming transports and
handles narrow, unambiguous Home Assistant requests on a deterministic local
route. These commands avoid an OpenAI tool-selection round:

- Turn on the workshop bench.
- Is it on?
- Now turn it off.
- What state is it in?

Ambiguous device names and unsupported requests continue through the model tool
loop. Existing entity policy and safe-domain checks still protect every action.

Set `workshop_memory_url` to the hostname or private IP of your Workshop Memory
service. The public example uses a neutral local hostname:

`http://workshop-memory.local:3001/mcp`

## Updating without losing configuration

Home Assistant keeps the app's existing configuration when ZBRANO is updated.
That includes the Workshop Memory URL, OpenAI and ElevenLabs API keys, voice ID,
model choices, and entity lists. ZBRANO reads those saved options at every
start; the defaults in `config.yaml` are used only for a new installation or a
newly introduced option.

Chats, General Instructions, and entity policies are stored in the app's
persistent `/data` directory and also survive normal updates and restarts.
Removing ZBRANO and selecting the option to delete its data, or restoring a
fresh Home Assistant installation without the app's backup data, can erase
them. Keep a Home Assistant backup before major upgrades.

## GitHub OAuth (v0.11.15)

The official GitHub MCP plugin can use GitHub Device Flow. Create a GitHub OAuth App (or GitHub App) with **Device Flow enabled**, copy its **Client ID**, and set `github_oauth_client_id` in the ZBRANO Home Assistant add-on configuration. No client secret is required for Device Flow.

After saving the add-on configuration and restarting ZBRANO, open **Plugins**, refresh the catalog, and press **Connect GitHub** on the official GitHub plugin. ZBRANO opens GitHub sign-in/authorization, displays the one-time device code, polls for completion, stores the returned bearer token only in server-side plugin secret storage, and installs the plugin disabled by default for review.
