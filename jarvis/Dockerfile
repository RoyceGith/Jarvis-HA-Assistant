FROM ghcr.io/home-assistant/base:latest

ARG BUILD_VERSION
ARG BUILD_ARCH

LABEL \
  io.hass.name="Jarvis Workshop Assistant" \
  io.hass.description="Local Jarvis agent and interface" \
  io.hass.version="${BUILD_VERSION}" \
  io.hass.type="app" \
  io.hass.arch="${BUILD_ARCH}"

RUN apk add --no-cache python3 py3-pip nodejs

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
COPY apply_plugin_dom_fix_v0112.py ./apply_plugin_dom_fix_v0112.py
COPY apply_plugin_init_fix_v0113.py ./apply_plugin_init_fix_v0113.py
COPY apply_catalog_tdz_fix_v0114.py ./apply_catalog_tdz_fix_v0114.py
COPY apply_catalog_escape_fix_v0115.py ./apply_catalog_escape_fix_v0115.py
COPY apply_catalog_backend_and_chat_ui_v0116.py ./apply_catalog_backend_and_chat_ui_v0116.py
COPY apply_build_source_fix_v0118.py ./apply_build_source_fix_v0118.py
COPY apply_plugin_controls_and_new_chat_v0119.py ./apply_plugin_controls_and_new_chat_v0119.py
COPY apply_chat_catalog_github_auth_v01110.py ./apply_chat_catalog_github_auth_v01110.py
COPY apply_catalog_cache_and_auth_clarity_v01111.py ./apply_catalog_cache_and_auth_clarity_v01111.py
COPY apply_plugin_tdz_final_fix_v01112.py ./apply_plugin_tdz_final_fix_v01112.py
COPY apply_install_routing_fix_v01113.py ./apply_install_routing_fix_v01113.py
COPY apply_install_routing_build_fix_v01114.py ./apply_install_routing_build_fix_v01114.py
COPY apply_github_oauth_enable_v01115.py ./apply_github_oauth_enable_v01115.py
COPY apply_entities_brand_and_oauth_env_v01116.py ./apply_entities_brand_and_oauth_env_v01116.py
COPY apply_oauth_popup_and_zbrano_brand_v01117.py ./apply_oauth_popup_and_zbrano_brand_v01117.py
COPY apply_shared_files_and_github_state_v01118.py ./apply_shared_files_and_github_state_v01118.py
COPY apply_frontend_repair_and_device_picker_v01119.py ./apply_frontend_repair_and_device_picker_v01119.py
COPY apply_github_chat_shared_fix_v01120.py ./apply_github_chat_shared_fix_v01120.py
COPY apply_new_chat_draft_fix_v01121.py ./apply_new_chat_draft_fix_v01121.py
COPY apply_new_chat_shared_files_fix_v01122.py ./apply_new_chat_shared_files_fix_v01122.py
COPY apply_new_chat_sidebar_draft_v01123.py ./apply_new_chat_sidebar_draft_v01123.py
COPY apply_remove_legacy_new_chat_interceptor_v01124.py ./apply_remove_legacy_new_chat_interceptor_v01124.py
COPY apply_build_recovery_v01125.py ./apply_build_recovery_v01125.py
COPY apply_plugin_runtime_dom_fix_v01126.py ./apply_plugin_runtime_dom_fix_v01126.py
COPY apply_runtime_order_fix_v01127.py ./apply_runtime_order_fix_v01127.py
COPY apply_plugin_manager_recovery_v01128.py ./apply_plugin_manager_recovery_v01128.py
COPY apply_github_tool_approval_build_fix_v01129.py ./apply_github_tool_approval_build_fix_v01129.py
COPY apply_github_tool_approval_policy_v01129.py ./apply_github_tool_approval_policy_v01129.py
COPY apply_shared_files_runtime_recovery_v01130.py ./apply_shared_files_runtime_recovery_v01130.py
COPY apply_catalog_and_plugin_compact_v01131.py ./apply_catalog_and_plugin_compact_v01131.py
COPY apply_developer_mode_self_diagnostics_v0120.py ./apply_developer_mode_self_diagnostics_v0120.py
COPY apply_attach_and_operational_diagnostics_v0121.py ./apply_attach_and_operational_diagnostics_v0121.py
COPY apply_attachment_upload_fix_v0122.py ./apply_attachment_upload_fix_v0122.py
COPY apply_shared_files_and_diagnostics_v0123.py ./apply_shared_files_and_diagnostics_v0123.py
COPY apply_investigation_engine_v0124.py ./apply_investigation_engine_v0124.py
COPY apply_developer_tool_isolation_v0125.py ./apply_developer_tool_isolation_v0125.py
COPY validate_inline_js.py ./validate_inline_js.py
COPY validate_new_chat_wiring.py ./validate_new_chat_wiring.py
RUN python3 ./apply_interface_hotfix.py \
    && python3 ./apply_agent_controls_v090.py \
    && python3 ./apply_build_fix_v0101.py \
    && python3 ./apply_plugin_manager_v0100.py \
    && python3 ./apply_ui_recovery_v0102.py \
    && python3 ./apply_plugin_catalog_v0110.py \
    && python3 ./apply_plugin_catalog_fix_v0111.py \
    && python3 ./apply_plugin_dom_fix_v0112.py \
    && python3 ./apply_plugin_init_fix_v0113.py \
    && python3 ./apply_catalog_tdz_fix_v0114.py \
    && python3 ./apply_catalog_escape_fix_v0115.py \
    && python3 ./apply_build_source_fix_v0118.py \
    && python3 ./apply_catalog_backend_and_chat_ui_v0116.py \
    && python3 ./apply_plugin_controls_and_new_chat_v0119.py \
    && python3 ./apply_chat_catalog_github_auth_v01110.py \
    && python3 ./apply_catalog_cache_and_auth_clarity_v01111.py \
    && python3 ./apply_plugin_tdz_final_fix_v01112.py \
    && python3 ./apply_install_routing_build_fix_v01114.py \
    && python3 ./apply_install_routing_fix_v01113.py \
    && python3 ./apply_github_oauth_enable_v01115.py \
    && python3 ./apply_entities_brand_and_oauth_env_v01116.py \
    && python3 ./apply_oauth_popup_and_zbrano_brand_v01117.py \
    && python3 ./apply_shared_files_and_github_state_v01118.py \
    && python3 ./apply_frontend_repair_and_device_picker_v01119.py \
    && python3 ./apply_github_chat_shared_fix_v01120.py \
    && python3 ./apply_new_chat_draft_fix_v01121.py \
    && python3 ./apply_new_chat_shared_files_fix_v01122.py \
    && python3 ./apply_new_chat_sidebar_draft_v01123.py \
    && python3 ./apply_remove_legacy_new_chat_interceptor_v01124.py \
    && python3 ./apply_build_recovery_v01125.py \
    && python3 ./apply_plugin_runtime_dom_fix_v01126.py \
    && python3 ./apply_runtime_order_fix_v01127.py \
    && python3 ./apply_plugin_manager_recovery_v01128.py \
    && python3 ./apply_github_tool_approval_build_fix_v01129.py \
    && python3 ./apply_github_tool_approval_policy_v01129.py \
    && python3 ./apply_shared_files_runtime_recovery_v01130.py \
    && python3 ./apply_catalog_and_plugin_compact_v01131.py \
    && python3 ./apply_developer_mode_self_diagnostics_v0120.py \
    && python3 ./apply_attach_and_operational_diagnostics_v0121.py \
    && python3 ./apply_attachment_upload_fix_v0122.py \
    && python3 ./apply_shared_files_and_diagnostics_v0123.py \
    && python3 ./apply_investigation_engine_v0124.py \
    && python3 ./apply_developer_tool_isolation_v0125.py \
    && python3 ./validate_inline_js.py ./app/static/index.html \
    && python3 ./validate_new_chat_wiring.py ./app/static/index.html \
    && python3 -m py_compile ./app/main.py \
    && rm ./apply_interface_hotfix.py ./apply_agent_controls_v090.py ./apply_plugin_manager_v0100.py ./apply_build_fix_v0101.py ./apply_ui_recovery_v0102.py ./apply_plugin_catalog_v0110.py ./apply_plugin_catalog_fix_v0111.py ./apply_plugin_dom_fix_v0112.py ./apply_plugin_init_fix_v0113.py ./apply_catalog_tdz_fix_v0114.py ./apply_catalog_escape_fix_v0115.py ./apply_catalog_backend_and_chat_ui_v0116.py ./apply_build_source_fix_v0118.py ./apply_plugin_controls_and_new_chat_v0119.py ./apply_chat_catalog_github_auth_v01110.py ./apply_catalog_cache_and_auth_clarity_v01111.py ./apply_plugin_tdz_final_fix_v01112.py ./apply_install_routing_fix_v01113.py ./apply_install_routing_build_fix_v01114.py ./apply_github_oauth_enable_v01115.py ./apply_entities_brand_and_oauth_env_v01116.py ./apply_oauth_popup_and_zbrano_brand_v01117.py ./apply_shared_files_and_github_state_v01118.py ./apply_frontend_repair_and_device_picker_v01119.py ./apply_github_chat_shared_fix_v01120.py ./apply_new_chat_draft_fix_v01121.py ./apply_new_chat_shared_files_fix_v01122.py ./apply_new_chat_sidebar_draft_v01123.py ./apply_remove_legacy_new_chat_interceptor_v01124.py ./apply_build_recovery_v01125.py ./apply_plugin_runtime_dom_fix_v01126.py ./apply_runtime_order_fix_v01127.py ./apply_plugin_manager_recovery_v01128.py ./apply_github_tool_approval_build_fix_v01129.py ./apply_github_tool_approval_policy_v01129.py ./apply_shared_files_runtime_recovery_v01130.py ./apply_catalog_and_plugin_compact_v01131.py ./apply_developer_mode_self_diagnostics_v0120.py ./apply_attach_and_operational_diagnostics_v0121.py ./apply_attachment_upload_fix_v0122.py ./apply_shared_files_and_diagnostics_v0123.py ./apply_investigation_engine_v0124.py ./apply_developer_tool_isolation_v0125.py ./validate_inline_js.py ./validate_new_chat_wiring.py

COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD ["/run.sh"]
