#!/usr/bin/with-contenv bashio
set -euo pipefail

export JARVIS_LOG_LEVEL="$(bashio::config 'log_level')"
export WORKSHOP_MEMORY_URL="$(bashio::config 'workshop_memory_url')"
export WORKSHOP_MEMORY_INTERNAL_URL="$(bashio::config 'workshop_memory_internal_url')"
export OPENAI_API_KEY="$(bashio::config 'openai_api_key')"
export GITHUB_OAUTH_CLIENT_ID="$(bashio::config 'github_oauth_client_id')"
export OPENAI_MODEL="$(bashio::config 'openai_model')"
export OPENAI_TRANSCRIPTION_MODEL="$(bashio::config 'openai_transcription_model')"
export OPENAI_TTS_MODEL="$(bashio::config 'openai_tts_model')"
export SPEECH_PROVIDER="$(bashio::config 'speech_provider')"
export ELEVENLABS_API_KEY="$(bashio::config 'elevenlabs_api_key')"
export ELEVENLABS_VOICE_ID="$(bashio::config 'elevenlabs_voice_id')"
export ELEVENLABS_VOICE_NAME="$(bashio::config 'elevenlabs_voice_name')"
export ELEVENLABS_MODEL_ID="$(bashio::config 'elevenlabs_model_id')"
export SPEECH_FALLBACK_TO_OPENAI="$(bashio::config 'speech_fallback_to_openai')"
export HA_READ_ENTITIES="$(bashio::config 'ha_read_entities')"
export HA_CONTROL_ENTITIES="$(bashio::config 'ha_control_entities')"

bashio::log.info "Starting Jarvis Workshop Assistant..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8099 --proxy-headers
