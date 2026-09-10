# ZBRANO v0.13.208

Automation Studio provides a graphical, step-by-step workflow for Home Assistant
automations. Use Setup &amp; safety, When, Only if, Then, and optional Outcomes beside the
interactive flow canvas. Natural-language creation, templates, drag-and-drop,
saved automation compatibility, and the full Advanced editor remain available.

Version 0.13.208 adds a formatted Markdown reading view for memory notes, an
explicit Edit action, visible last-updated dates, and formatted printing.

Version 0.13.207 uses the memory space name as a compact, undecorated print title.

Version 0.13.206 places note content directly below its title without sacrificing
the expanded editor height.

Version 0.13.205 automatically opens a space's first note, keeps category
navigation visible above the editor, and expands the usable note workspace.

Version 0.13.204 suggests broad and specific note collections before the first
save. My Memory prioritizes a spacious editor, hides internal `.md` extensions,
supports renaming notes and categories, and prints individual notes cleanly.

Version 0.13.203 files saved knowledge into descriptive topic notes such as **Soup
Recipes**, offers one append-or-create choice for related existing collections, and
confirms the exact destination after saving.

Version 0.13.202 makes deleting the final saved conversation atomic in the interface:
the deleted row disappears and exactly one fresh unsaved chat remains.

Version 0.13.201 completes explicitly requested automatic Memory Database saves
without a redundant approval. Large saves use announced, bounded phases while
other permanent edits retain their approval boundary.

Version 0.13.200 keeps headings, lists, spacing, and emphasis intact when users
stop a streamed response, and retains the interrupted answer in chat history.

Version 0.13.199 presents automatic Knowledge Memory writes as **Save to Memory
Database**, clearly distinguishing durable notes from Fast Memory preferences.

Version 0.13.198 keeps optional remote MCP connectors out of unrelated chat
requests. Connectors are attached only when named explicitly, so a failed remote
server cannot break ordinary questions, recipes, device control, or local Memory.

Version 0.13.197 turns Memory into an automatic everyday experience. Users write
what ZBRANO should remember; it chooses the area and note, reuses existing spaces,
creates missing organization, and avoids duplicates. Custom layouts remain optional.

Version 0.13.196 restores reliable vertical scrolling throughout Memory Database
and Template Studio, including creation and editing forms on desktop and compact
screens.

Version 0.13.195 separates a memory space's category from its layout. After choosing
Home, Work, Personal, or Learning, users see only relevant organizational layouts
with clear names instead of choosing Home or Work twice.

Version 0.13.194 adds a dedicated Memory Studio. Memory Database provides visual
categories, spaces, note search, and a simple editor. Template Studio lets users
build reusable note-card layouts for any subject without configuring an MCP
server. Custom categories and templates are included in local backup and restore.

Version 0.13.193 adds built-in Knowledge Memory with customizable spaces instead
of assuming that every user has a workshop or projects. Markdown notes are stored
locally, searched by ZBRANO's own tools, protected by write approval, and included
in settings backup and restore. A saved legacy Workshop Memory endpoint is used
only for a one-time import and is no longer required afterward.

Version 0.13.192 adds bring-your-own AI through OpenRouter. A user can keep direct
OpenAI or provide their own OpenRouter key, choose a model from its live catalog,
and pay that provider directly. Home Assistant control commands keep their fast
local route. The interface accurately limits OpenRouter sessions to local function
tools until web search and remote-plugin compatibility is verified.

Version 0.13.191 adds a clear wake-detection choice. Browser recognition is
recommended for all voices; the private local prototype is labelled experimental
because it was tuned with the owner's recordings. Existing local-model preferences
remain intact, and calibration is accurately described as a false-trigger filter.

Version 0.13.190 filters status, temperature, and mode helper entities out of
power-command choices. Air-conditioner wording now gives the actual climate or
thermostat entity priority, even if helper entities share the same device name.

Version 0.13.189 makes direct on/off chat commands faster by resolving approved
Control Devices locally before preparing AI or Workshop tools. Matching sensors no
longer make an otherwise clear device command ambiguous, and successful WebSocket
actions are verified without sending the action again.

Version 0.13.188 moves interface language selection into a compact flag control
in the top-right header. The choice is saved immediately and changes only interface
copy and displayed dates; conversation replies follow each user message and browser
speech recognition follows the device locale.

Version 0.13.187 extends the four-language interface throughout the main and
advanced workspaces. It localizes hundreds of additional controls and the complete
About showcase, translates dynamically changed accessibility labels, formats dates
with the selected locale, and build-gates catalog coverage while continuing to
protect conversation, entity, and user-authored automation content.

Version 0.13.186 introduces the localization foundation for English, Greek,
Italian, and French. ZBRANO can follow the device language or a saved selection,
translate core interface controls as they appear, and show localized Home Assistant
configuration descriptions. Conversation content, entity names, and saved automation
text are deliberately never translated.

Version 0.13.185 publishes ZBRANO for both `aarch64` and `amd64` Home Assistant
systems. The official build matrix validates each platform independently and joins
them behind the existing generic image reference, preserving installed-system
updates and persistent data.

Version 0.13.184 adds original ZBRANO presentation artwork for the Home Assistant
store and public product pages. Release checks enforce the icon and logo dimensions,
transparent PNG format, size limits, and thin-repository boundary.

Version 0.13.183 replaces the public release-diary pages with focused product and
installation guides. New users can quickly understand ZBRANO's requirements,
capabilities, entity permissions, automation safety, privacy, updates, and support.
The full release record remains in the public changelog.

Version 0.13.182 introduces a top-level About tab designed as a truthful ZBRANO
product showcase. Six organized capability groups, a simple four-step journey,
ownership messaging, and direct product actions make the complete feature set easy
to understand on desktop and mobile.

Version 0.13.181 adds friendly Home Assistant Configuration labels and descriptions
for every ZBRANO option. Required, optional, advanced, protected, and legacy fields
are identified plainly, and release validation prevents a shipped option from
losing its explanation.

Version 0.13.180 fixes the Home Assistant setup action so it opens dedicated
connection help rather than Device Access. The guide explains that Supervisor
connects ZBRANO automatically, points to app status and logs, and rechecks the
connection directly without requesting an address or token.

Version 0.13.179 replaces Entity permissions jargon in Setup with Device access,
Sensor devices, and Control devices. Empty access now clearly distinguishes a
chat-ready ZBRANO from one that can read or act on the home.

Version 0.13.178 puts the five essential permission columns first and gives them
plain names. Technical details remain available to the right, saved custom layouts
are preserved, and selecting a permission category exposes a usable table viewport.

Version 0.13.177 keeps each permission checkbox, access choice, saved record,
summary, and export consistent. Do not allow always revokes access, and checking
a blocked entity safely restores read access without granting device control.

Version 0.13.176 replaces internal entity-access terminology with Sensor device,
Control device, and Do not allow. HVAC status sensors remain read-only even when
their names match the setup recommendation, and legacy saved values remain intact.

Version 0.13.175 removes legacy automatic socket and HVAC permission grants. Newly
discovered devices remain unchecked until explicitly selected, existing saved
permissions stay compatible, and formerly automatic records become editable and
revocable. Recommendations no longer write authority.

Version 0.13.174 adds plain-language Sensor, Control, and All entity permission
views with live installation counts and read-only filtering.

Version 0.13.173 adds an in-product Home Assistant AI configuration guide with a
clear save, restart, and verification sequence.

Version 0.13.172 adds a shareable Installation Report covering connections,
storage, backup, permission counts, and automation safety totals with sanitized
copy and download actions.

Version 0.13.167 gives completed onboarding a useful destination. The final screen
shows ready and later capabilities separately, opens Chat directly, and lets users
review all setup connections without resetting their completion state.

Version 0.13.166 presents Setup as one focused step at a time with a compact
progress rail, plain-language explanations, direct Check and Configure actions,
and live required-step gates. Optional voice, memory, plugins, and notifications
remain skippable and can be revisited later.

Version 0.13.165 removes all Grinder-specific fields from the general Home
Assistant add-on configuration and startup environment. Existing private Grinder
monitoring continues from the protected `/data` record migrated by v0.13.164.

Version 0.13.164 migrates enabled or customized owner-only Grinder settings into
protected `/data` storage before ZBRANO starts. The Grinder runtime now reads
that private configuration first, allowing its transitional public add-on fields
to be removed safely after existing owner installations have migrated.

Version 0.13.163 moves action authority into the IF or ELSE IF path that owns
the tasks. Each executable path can ask before running or run automatically,
while message-only paths notify without showing action authority.

Version 0.13.162 marks only the specific incomplete Studio card as needing
attention. Per-automation sleep hours now pause individual rules, with an explicit
security override for rules that must keep running. Branch power tasks also infer
the correct Home Assistant action from the selected device.

Version 0.13.161 makes branch messages optional task blocks. A new ELSE IF path
contains no message by default, and message-only outcomes notify normally without
offering approval for an action that does not exist.

Version 0.13.160 synchronizes device choices in nested branch tasks and shows
the complete Home Assistant friendly name on the task card. Partial search text
is treated as incomplete instead of being displayed or saved as a device.

Version 0.13.159 gives every branch message its own plainly named delivery
choices: say it aloud, show it in ZBRANO notifications, or send it to Home
Assistant notifications. The redundant This path runs when selector is removed,
and all checks in a branch must be true.

Version 0.13.158 makes IF and ELSE IF lanes begin with the condition that defines
them, without redundant editable branch-name cards. Each speaking path owns its
message, silent monitoring hides messages completely, and bottom task menus open
upward so their choices stay visible.

Version 0.13.157 shows each device or sensor's current value directly in entity
selection results. Readings include units, and climate devices prefer their live
current temperature while retaining the entity name and ID.

Version 0.13.156 defaults IF and ELSE IF device checks to the selected entity's
state. Attribute selection is now a collapsed advanced choice and automatically
opens only when an existing automation already uses an attribute.

Version 0.13.155 moves Setup & safety and step progress out of the block bar
into a compact guide line. The palette now contains only actual flow blocks,
while New automation, Try it safely, and Save automation use smaller controls.

Version 0.13.154 keeps Power turns on and Power turns off highlighted after a
device is selected, including climate entities. These events now ask only for
the power device and optional duration instead of comparison details.

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

Knowledge Memory is built into ZBRANO and stores Markdown notes in the app's
persistent data directory. Users can create neutral spaces for Home, Work,
Study, Recipes, a Project, or anything else. It does not require a domain,
tunnel, MCP server, or account controlled by the ZBRANO developer. An existing
legacy Workshop Memory URL is used only for a one-time local import when that
saved option is still present after an upgrade.

## Updating without losing configuration

Home Assistant keeps the app's existing configuration when ZBRANO is updated.
That includes OpenAI and ElevenLabs API keys, voice ID, model choices, and
entity lists. ZBRANO reads those saved options at every
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
