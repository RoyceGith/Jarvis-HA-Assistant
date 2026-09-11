FROM ghcr.io/home-assistant/base:latest

ARG BUILD_VERSION
ARG BUILD_ARCH

LABEL \
  io.hass.name="ZBRANO" \
  io.hass.description="Local ZBRANO workshop intelligence core assistant" \
  io.hass.version="${BUILD_VERSION}" \
  io.hass.type="app" \
  io.hass.arch="${BUILD_ARCH}" \
  org.opencontainers.image.source="https://github.com/RoyceGith/ZBRANO_Core"

RUN apk add --no-cache python3 py3-pip py3-numpy py3-scipy py3-scikit-learn py3-tqdm py3-onnxruntime nodejs npm chromium nss freetype harfbuzz ca-certificates font-noto

# Playwright is a build-only browser smoke dependency. It is removed before the
# Home Assistant runtime image is finalized and is never exposed as a plugin.
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
RUN npm install --global @playwright/mcp@0.0.78

WORKDIR /opt/zbrano

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
COPY validate_i18n_catalog.py ./validate_i18n_catalog.py
COPY tests ./tests

RUN python3 ./validate_release_manifest.py
RUN python3 ./validate_i18n_catalog.py
RUN python3 ./validate_inline_js.py ./app/static/index.html
RUN python3 ./validate_new_chat_wiring.py ./app/static/index.html
RUN python3 -m compileall -q ./app
RUN python3 -m unittest discover -s ./tests -p "test_*.py"
# The browser application is architecture-independent. Run its Chromium smoke on
# native amd64; emulated aarch64 Chromium is nondeterministic under Buildx/QEMU.
# Both images still run every static validator, Python compilation, and API test.
RUN if [ "$BUILD_ARCH" = "aarch64" ]; then \
        echo "Browser smoke covered by the identical amd64 static application"; \
    else \
        node ./tests/browser_smoke.cjs; \
    fi
RUN npm uninstall --global @playwright/mcp \
    && apk del nodejs npm chromium nss freetype harfbuzz \
    && rm -r /root/.npm \
    && rm -r ./tests \
    && rm ./validate_release_manifest.py ./validate_i18n_catalog.py ./validate_inline_js.py ./validate_new_chat_wiring.py ./config.yaml

COPY run.sh /run.sh
RUN sed -i 's/\r$//' /run.sh \
    && chmod a+x /run.sh

CMD ["/run.sh"]
