FROM ghcr.io/home-assistant/base:latest

ARG BUILD_VERSION
ARG BUILD_ARCH

LABEL \
  io.hass.name="ZBRANO" \
  io.hass.description="Local ZBRANO workshop intelligence core assistant" \
  io.hass.version="${BUILD_VERSION}" \
  io.hass.type="app" \
  io.hass.arch="${BUILD_ARCH}" \
  org.opencontainers.image.source="https://github.com/RoyceGith/Jarvis-HA-Assistant"

RUN apk add --no-cache python3 py3-pip py3-numpy py3-scipy py3-scikit-learn py3-tqdm py3-onnxruntime nodejs npm chromium nss freetype harfbuzz ca-certificates font-noto

# Playwright MCP runs locally beside Chromium. Pin the package so Raspberry Pi
# rebuilds cannot silently acquire an incompatible browser protocol release.
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
RUN npm install --global @playwright/mcp@0.0.78

WORKDIR /opt/jarvis

COPY requirements.txt ./requirements.txt
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt \
    && pip3 install --no-cache-dir --break-system-packages --no-deps openwakeword==0.6.0

# Since v0.13.0 these files are the canonical runtime source. Historical
# releases generated them by applying an ordered patch chain during the image
# build; the generated v0.12.112 result was verified and promoted into source.
COPY app ./app
COPY models/wakeword ./models/wakeword
COPY config.yaml ./config.yaml
COPY release_manifest.json ./release_manifest.json
COPY validate_release_manifest.py ./validate_release_manifest.py
COPY validate_inline_js.py ./validate_inline_js.py
COPY validate_new_chat_wiring.py ./validate_new_chat_wiring.py

RUN python3 ./validate_release_manifest.py \
    && python3 ./validate_inline_js.py ./app/static/index.html \
    && python3 ./validate_new_chat_wiring.py ./app/static/index.html \
    && python3 -m compileall -q ./app \
    && rm ./validate_release_manifest.py ./validate_inline_js.py ./validate_new_chat_wiring.py ./config.yaml

COPY run.sh /run.sh
RUN sed -i 's/\r$//' /run.sh \
    && chmod a+x /run.sh

CMD ["/run.sh"]
