ZBRANO v0.12.70 keeps voice playback starting while response text is still streaming and pre-generates the next spoken segment during current playback, removing the multi-second pause between sentence-sized TTS requests.

ZBRANO v0.12.69 routes grinder freeze, reboot, telemetry, and incident prompts exclusively to the local read-only grinder diagnostic tools. It retrieves the stored pre-failure window instead of asking for an export and treats a later manual POWER ON reset as operator-caused when the user identifies it that way.
