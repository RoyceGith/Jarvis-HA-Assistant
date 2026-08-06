FROM ghcr.io/home-assistant/base:latest

ARG BUILD_VERSION
ARG BUILD_ARCH

LABEL \
  io.hass.name="Jarvis Workshop Assistant" \
  io.hass.description="Local Jarvis agent and interface" \
  io.hass.version="${BUILD_VERSION}" \
  io.hass.type="app" \
  io.hass.arch="${BUILD_ARCH}"

RUN apk add --no-cache python3 py3-pip

WORKDIR /opt/jarvis

COPY requirements.txt .
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

COPY app ./app
COPY apply_interface_hotfix.py ./apply_interface_hotfix.py
COPY apply_agent_controls_v090.py ./apply_agent_controls_v090.py
COPY apply_plugin_manager_v0100.py ./apply_plugin_manager_v0100.py
COPY apply_build_fix_v0101.py ./apply_build_fix_v0101.py
COPY apply_ui_recovery_v0102.py ./apply_ui_recovery_v0102.py
COPY apply_plugin_catalog_v0110.py ./apply_plugin_catalog_v0110.py
COPY apply_plugin_catalog_fix_v0111.py ./apply_plugin_catalog_fix_v0111.py
RUN python3 ./apply_interface_hotfix.py \
    && python3 ./apply_agent_controls_v090.py \
    && python3 ./apply_build_fix_v0101.py \
    && python3 ./apply_plugin_manager_v0100.py \
    && python3 ./apply_ui_recovery_v0102.py \
    && python3 ./apply_plugin_catalog_v0110.py \
    && python3 ./apply_plugin_catalog_fix_v0111.py \
    && python3 -m py_compile ./app/main.py \
    && rm ./apply_interface_hotfix.py ./apply_agent_controls_v090.py ./apply_plugin_manager_v0100.py ./apply_build_fix_v0101.py ./apply_ui_recovery_v0102.py ./apply_plugin_catalog_v0110.py ./apply_plugin_catalog_fix_v0111.py

COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD ["/run.sh"]
