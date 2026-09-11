from __future__ import annotations

import time
import uuid

from homeassistant.components import conversation
from homeassistant.components.conversation import (
    AbstractConversationAgent,
    AssistantContent,
    ChatLog,
    ConversationEntity,
    ConversationEntityFeature,
    ConversationInput,
    ConversationResult,
    HOME_ASSISTANT_AGENT,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN, MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import area_registry as ar, device_registry as dr, intent
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import ZbranoApi, ZbranoApiError
from .const import CONF_FALLBACK_AGENT, CONF_URL


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    api = ZbranoApi(
        async_get_clientsession(hass),
        entry.data[CONF_URL],
        entry.data[CONF_ACCESS_TOKEN],
    )
    async_add_entities([ZbranoConversationEntity(entry, api)])


class ZbranoConversationEntity(ConversationEntity, AbstractConversationAgent):
    _attr_name = "ZBRANO"
    _attr_supported_features = ConversationEntityFeature.CONTROL

    def __init__(self, entry: ConfigEntry, api: ZbranoApi) -> None:
        self._attr_unique_id = entry.entry_id
        self._entry = entry
        self._api = api
        self._fallback_agent = str(
            entry.data.get(CONF_FALLBACK_AGENT, HOME_ASSISTANT_AGENT)
        )
        self._recent: dict[tuple[str, str], tuple[float, dict]] = {}

    @property
    def supported_languages(self):
        return MATCH_ALL

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        conversation.async_set_agent(self.hass, self._entry, self)

    async def async_will_remove_from_hass(self) -> None:
        conversation.async_unset_agent(self.hass, self._entry)
        await super().async_will_remove_from_hass()

    def _satellite_context(self, device_id: str | None) -> tuple[str, str]:
        if not device_id:
            return "", ""
        device = dr.async_get(self.hass).async_get(device_id)
        if device is None:
            return "", ""
        area = ar.async_get(self.hass).async_get_area(device.area_id) if device.area_id else None
        return device.name_by_user or device.name or "", area.name if area else ""

    async def _async_fallback(self, user_input: ConversationInput) -> ConversationResult:
        """Use exactly one HA agent when ZBRANO is confirmed unavailable."""
        if self._fallback_agent in {self._entry.entry_id, self.entity_id}:
            raise HomeAssistantError("The ZBRANO fallback assistant cannot be ZBRANO itself")
        return await conversation.async_converse(
            hass=self.hass,
            text=user_input.text,
            conversation_id=user_input.conversation_id,
            context=user_input.context,
            language=user_input.language,
            agent_id=self._fallback_agent,
            device_id=user_input.device_id,
            satellite_id=user_input.satellite_id,
            extra_system_prompt=user_input.extra_system_prompt,
        )

    def _request_key(self, user_input: ConversationInput) -> tuple[str, str]:
        source = (
            user_input.conversation_id
            or user_input.satellite_id
            or user_input.device_id
            or "unscoped"
        )
        return source, " ".join(user_input.text.casefold().split())

    async def async_process(self, user_input: ConversationInput) -> ConversationResult:
        """Choose ZBRANO or one fallback before opening a conversation log."""
        cached = self._recent.get(self._request_key(user_input))
        if not cached or time.monotonic() - cached[0] > 3:
            try:
                health = await self._api.health()
            except ZbranoApiError:
                return await self._async_fallback(user_input)
            if not health.get("ready"):
                return await self._async_fallback(user_input)
        return await super().async_process(user_input)

    async def _async_handle_message(
        self,
        user_input: ConversationInput,
        chat_log: ChatLog,
    ) -> ConversationResult:
        conversation_id = user_input.conversation_id or uuid.uuid4().hex
        key = self._request_key(user_input)
        cached = self._recent.get(key)
        if cached and time.monotonic() - cached[0] <= 3:
            payload = cached[1]
        else:
            satellite_name, area_name = self._satellite_context(user_input.device_id)
            try:
                payload = await self._api.converse(
                    {
                        "request_id": uuid.uuid4().hex,
                        "text": user_input.text,
                        "conversation_id": conversation_id,
                        "language": user_input.language,
                        "device_id": user_input.device_id or "",
                        "satellite_name": satellite_name,
                        "area_name": area_name,
                        "extra_system_prompt": user_input.extra_system_prompt or "",
                    }
                )
            except ZbranoApiError as exc:
                raise HomeAssistantError(
                    "ZBRANO accepted this request but its result is uncertain. "
                    "It was not repeated through the fallback assistant."
                ) from exc
            self._recent = {key: (time.monotonic(), payload)}

        reply = str(payload.get("reply") or "I could not produce a response.")
        chat_log.async_add_assistant_content_without_tools(
            AssistantContent(agent_id=user_input.agent_id, content=reply)
        )
        response = intent.IntentResponse(language=user_input.language)
        response.async_set_speech(reply)
        return ConversationResult(
            conversation_id=str(payload.get("conversation_id") or conversation_id),
            response=response,
            continue_conversation=bool(payload.get("continue_conversation")),
        )
