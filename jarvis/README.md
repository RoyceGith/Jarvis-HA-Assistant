# Jarvis Workshop Assistant v0.8.5

Version 0.8.5 adds clean Markdown rendering for Jarvis chat replies and guides
assistant responses toward readable sections, spacing, bullets, and concise
paragraphs.

Version 0.8.4 starts text-to-speech from streamed response chunks instead of
waiting for the full assistant response to finish, so Jarvis can begin speaking
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
Jarvis HUD, removes the circular neural frame, and places chat on a glass panel
over the obsidian node collective.

Version 0.7.5 adds persistent ElevenLabs Stability, Similarity, Style, and Speed
controls under Jarvis Settings. The existing delivery values remain the defaults,
and saved values are applied server-side to every subsequent ElevenLabs request.

Version 0.7.4 adds device-persistent Light and Dark themes under Settings and
replaces the sparse background graph with a centered, depth-rendered collective
of hundreds of linked obsidian nodes inspired by the Jarvis neural-core reference.

Version 0.7.3 adds a Settings tab with persistent General Instructions. The
instructions apply to every model response and survive app restarts/upgrades in
the add-on `/data` volume. Jarvis can also append a behavior from chat when the
user explicitly asks to save or remember it as a standing instruction. Normal
examples and corrections are not saved automatically, and custom instructions
cannot weaken device permissions or safety rules.

Version 0.7.2 reduces response-to-voice delay by relaying ElevenLabs audio to
the browser as it is generated and playing MP3 chunks progressively. It uses
the low-latency `eleven_flash_v2_5` model by default. OpenAI and ElevenLabs
remain selectable, and Jarvis can still retry a failed ElevenLabs response
with Cedar when `speech_fallback_to_openai` is enabled. The ElevenLabs key
never reaches the browser.

Required ElevenLabs settings:

- `elevenlabs_api_key`: API key created in ElevenLabs.
- `elevenlabs_voice_id`: ID shown for the selected or authorized custom voice.
- `elevenlabs_voice_name`: Browser label for the configured voice.
- `elevenlabs_model_id`: Defaults to low-latency `eleven_flash_v2_5`; use
  `eleven_multilingual_v2` when maximum expressiveness matters more than speed.

Do not paste the ElevenLabs key into Jarvis's browser interface or chat.

Version 0.7.0 adds device-local push-to-talk voice. The browser records from
the microphone on the PC or phone, sends the bounded recording to Jarvis for
transcription, routes the resulting text through the existing deterministic
Home Assistant and AI paths, and plays an AI-generated spoken response through
the same device. The OpenAI API key stays inside the add-on. Voice preferences
are stored per browser, and Stop interrupts both streamed text and playback.

Microphone access requires a secure browser context (HTTPS or localhost) and
the user must grant microphone permission to the Home Assistant/Jarvis page.
The spoken voice is AI-generated.

Adds a terminal-style HUD with a lightweight Obsidian-inspired neural graph,
persistent browser prompt history navigated with the Up/Down arrow keys, and a
Stop control that cancels the active response stream on both client and server.

Version 0.6.5 stores conversations in Home Assistant's persistent add-on `/data`
volume and restores the active chat when Jarvis is reopened. A conversation
sidebar supports opening, creating, and deleting saved chats. It also keeps
entity aliases persistent, includes the cyan intelligence-core HUD, and automatically enables
socket/outlet switches, climate/thermostat entities, and matching air-conditioner
status entities as approved low-risk entries. Other entity policies are unchanged.

Version 0.6.6 expands the Jarvis panel to the full available viewport. Alias
edits are synchronously backed up in the browser as well as saved to the add-on
policy. If Home Assistant navigation interrupts a pending request, Jarvis
restores the local alias on return and repairs the persistent server policy.

## v0.6.0

Adds the first internal intent-routing layer.

## Root cause

Streaming requests were not passing the browser chat session ID into the
streaming assistant function, so all streamed requests used the default session.

## Fix

Jarvis now passes the browser session ID through both streaming transports and
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

Home Assistant keeps the app's existing configuration when Jarvis is updated.
That includes the Workshop Memory URL, OpenAI and ElevenLabs API keys, voice ID,
model choices, and entity lists. Jarvis reads those saved options at every
start; the defaults in `config.yaml` are used only for a new installation or a
newly introduced option.

Chats, General Instructions, and entity policies are stored in the app's
persistent `/data` directory and also survive normal updates and restarts.
Removing Jarvis and selecting the option to delete its data, or restoring a
fresh Home Assistant installation without the app's backup data, can erase
them. Keep a Home Assistant backup before major upgrades.

## GitHub OAuth (v0.11.15)

The official GitHub MCP plugin can use GitHub Device Flow. Create a GitHub OAuth App (or GitHub App) with **Device Flow enabled**, copy its **Client ID**, and set `github_oauth_client_id` in the Jarvis Home Assistant add-on configuration. No client secret is required for Device Flow.

After saving the add-on configuration and restarting Jarvis, open **Plugins**, refresh the catalog, and press **Connect GitHub** on the official GitHub plugin. Jarvis opens GitHub sign-in/authorization, displays the one-time device code, polls for completion, stores the returned bearer token only in server-side plugin secret storage, and installs the plugin disabled by default for review.
