# Jarvis Workshop Assistant v0.7.3

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

Workshop Memory default remains:

`http://192.168.178.49:3001/mcp`
