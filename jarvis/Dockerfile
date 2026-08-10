FROM ghcr.io/home-assistant/base:latest

ARG BUILD_VERSION
ARG BUILD_ARCH

LABEL \
  io.hass.name="ZBRANO" \
  io.hass.description="Local ZBRANO workshop intelligence core assistant" \
  io.hass.version="${BUILD_VERSION}" \
  io.hass.type="app" \
  io.hass.arch="${BUILD_ARCH}"

RUN apk add --no-cache python3 py3-pip nodejs npm chromium nss freetype harfbuzz ca-certificates font-noto

# Playwright MCP runs locally beside Chromium. Pin the package so Raspberry Pi
# rebuilds cannot silently acquire an incompatible browser protocol release.
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
RUN npm install --global @playwright/mcp@0.0.78

WORKDIR /opt/jarvis

COPY requirements.txt .
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

COPY app ./app
COPY config.yaml ./config.yaml
COPY release_manifest.json ./release_manifest.json
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
COPY apply_developer_indicator_and_policy_v0126.py ./apply_developer_indicator_and_policy_v0126.py
COPY apply_persistent_chat_attachment_labels_v0127.py ./apply_persistent_chat_attachment_labels_v0127.py
COPY apply_plugin_workspace_v0128.py ./apply_plugin_workspace_v0128.py
COPY apply_plugin_oauth_v0129.py ./apply_plugin_oauth_v0129.py
COPY apply_autonomous_automations_v01210.py ./apply_autonomous_automations_v01210.py
COPY apply_workshop_memory_writes_v01211.py ./apply_workshop_memory_writes_v01211.py
COPY apply_workshop_task_approval_v01212.py ./apply_workshop_task_approval_v01212.py
COPY apply_release_alignment_v01213.py ./apply_release_alignment_v01213.py
COPY apply_zbrano_identity_v01214.py ./apply_zbrano_identity_v01214.py
COPY apply_ingress_oauth_callback_retry_v01215.py ./apply_ingress_oauth_callback_retry_v01215.py
COPY apply_playwright_developer_tools_v01216.py ./apply_playwright_developer_tools_v01216.py
COPY apply_build_cleanup_fix_v01217.py ./apply_build_cleanup_fix_v01217.py
COPY apply_workshop_bulk_edit_capacity_v01218.py ./apply_workshop_bulk_edit_capacity_v01218.py
COPY apply_modern_controls_and_neural_settings_v01219.py ./apply_modern_controls_and_neural_settings_v01219.py
COPY apply_navigation_settings_and_chat_wrap_v01220.py ./apply_navigation_settings_and_chat_wrap_v01220.py
COPY apply_release_memory_sync_v01221.py ./apply_release_memory_sync_v01221.py
COPY apply_release_validator_build_fix_v01222.py ./apply_release_validator_build_fix_v01222.py
COPY apply_live_developer_progress_v01223.py ./apply_live_developer_progress_v01223.py
COPY apply_diagnostic_investigate_fix_v01224.py ./apply_diagnostic_investigate_fix_v01224.py
COPY apply_bounded_model_continuation_v01225.py ./apply_bounded_model_continuation_v01225.py
COPY apply_native_web_search_v01226.py ./apply_native_web_search_v01226.py
COPY apply_playwright_mcp_readiness_fix_v01226.py ./apply_playwright_mcp_readiness_fix_v01226.py
COPY apply_playwright_host_port_fix_v01227.py ./apply_playwright_host_port_fix_v01227.py
COPY apply_composer_web_plugins_v01228.py ./apply_composer_web_plugins_v01228.py
COPY apply_frontend_cache_refresh_v01229.py ./apply_frontend_cache_refresh_v01229.py
COPY apply_local_plugin_icons_and_composer_stack_v01230.py ./apply_local_plugin_icons_and_composer_stack_v01230.py
COPY apply_live_tool_timeline_v01231.py ./apply_live_tool_timeline_v01231.py
COPY apply_web_source_curation_v01232.py ./apply_web_source_curation_v01232.py
COPY apply_provider_approval_flow_v01233.py ./apply_provider_approval_flow_v01233.py
COPY apply_native_approval_and_activity_order_v01234.py ./apply_native_approval_and_activity_order_v01234.py
COPY apply_mcp_approval_payload_fix_v01235.py ./apply_mcp_approval_payload_fix_v01235.py
COPY apply_playwright_routing_timeout_v01236.py ./apply_playwright_routing_timeout_v01236.py
COPY apply_playwright_chat_isolation_v01237.py ./apply_playwright_chat_isolation_v01237.py
COPY apply_mobile_chat_layout_v01238.py ./apply_mobile_chat_layout_v01238.py
COPY apply_conversation_authority_alignment_v01239.py ./apply_conversation_authority_alignment_v01239.py
COPY apply_measured_chat_editor_v01240.py ./apply_measured_chat_editor_v01240.py
COPY apply_compact_conversation_rows_v01241.py ./apply_compact_conversation_rows_v01241.py
COPY apply_conversation_row_inset_v01242.py ./apply_conversation_row_inset_v01242.py
COPY apply_notification_center_v01243.py ./apply_notification_center_v01243.py
COPY apply_notification_watchlist_v01244.py ./apply_notification_watchlist_v01244.py
COPY apply_notifications_scrolling_v01245.py ./apply_notifications_scrolling_v01245.py
COPY apply_telegram_notify_compat_v01246.py ./apply_telegram_notify_compat_v01246.py
COPY apply_telegram_exact_payload_v01247.py ./apply_telegram_exact_payload_v01247.py
COPY apply_notification_websocket_and_tab_activity_v01248.py ./apply_notification_websocket_and_tab_activity_v01248.py
COPY apply_telegram_plain_text_v01249.py ./apply_telegram_plain_text_v01249.py
COPY apply_telegram_service_routing_v01250.py ./apply_telegram_service_routing_v01250.py
COPY apply_semantic_tab_activity_v01251.py ./apply_semantic_tab_activity_v01251.py
COPY apply_notification_watch_dedup_v01252.py ./apply_notification_watch_dedup_v01252.py
COPY apply_voice_latency_and_activity_revisions_v01253.py ./apply_voice_latency_and_activity_revisions_v01253.py
COPY apply_gmail_pre_registered_oauth_v01254.py ./apply_gmail_pre_registered_oauth_v01254.py
COPY validate_release_manifest.py ./validate_release_manifest.py
COPY validate_inline_js.py ./validate_inline_js.py
COPY validate_new_chat_wiring.py ./validate_new_chat_wiring.py
RUN rm() { command rm -f "$@"; } \
    && python3 ./apply_interface_hotfix.py \
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
    && python3 ./apply_developer_indicator_and_policy_v0126.py \
    && python3 ./apply_persistent_chat_attachment_labels_v0127.py \
    && python3 ./apply_plugin_workspace_v0128.py \
    && python3 ./apply_plugin_oauth_v0129.py \
    && python3 ./apply_autonomous_automations_v01210.py \
    && python3 ./apply_workshop_memory_writes_v01211.py \
    && python3 ./apply_workshop_task_approval_v01212.py \
    && python3 ./apply_release_alignment_v01213.py \
    && python3 ./apply_zbrano_identity_v01214.py \
    && python3 ./apply_ingress_oauth_callback_retry_v01215.py \
    && python3 ./apply_playwright_developer_tools_v01216.py \
    && python3 ./apply_build_cleanup_fix_v01217.py \
    && rm ./apply_build_cleanup_fix_v01217.py \
    && python3 ./apply_workshop_bulk_edit_capacity_v01218.py \
    && rm ./apply_workshop_bulk_edit_capacity_v01218.py \
    && python3 ./apply_modern_controls_and_neural_settings_v01219.py \
    && rm ./apply_modern_controls_and_neural_settings_v01219.py \
    && python3 ./apply_navigation_settings_and_chat_wrap_v01220.py \
    && rm ./apply_navigation_settings_and_chat_wrap_v01220.py \
    && python3 ./apply_release_memory_sync_v01221.py \
    && rm ./apply_release_memory_sync_v01221.py \
    && python3 ./apply_release_validator_build_fix_v01222.py \
    && rm ./apply_release_validator_build_fix_v01222.py \
    && python3 ./apply_live_developer_progress_v01223.py \
    && rm ./apply_live_developer_progress_v01223.py \
    && python3 ./apply_diagnostic_investigate_fix_v01224.py \
    && rm ./apply_diagnostic_investigate_fix_v01224.py \
    && python3 ./apply_bounded_model_continuation_v01225.py \
    && rm ./apply_bounded_model_continuation_v01225.py \
    && python3 ./apply_native_web_search_v01226.py \
    && rm ./apply_native_web_search_v01226.py \
    && python3 ./apply_playwright_mcp_readiness_fix_v01226.py \
    && rm ./apply_playwright_mcp_readiness_fix_v01226.py \
    && python3 ./apply_playwright_host_port_fix_v01227.py \
    && rm ./apply_playwright_host_port_fix_v01227.py \
    && python3 ./apply_composer_web_plugins_v01228.py \
    && rm ./apply_composer_web_plugins_v01228.py \
    && python3 ./apply_frontend_cache_refresh_v01229.py \
    && rm ./apply_frontend_cache_refresh_v01229.py \
    && python3 ./apply_local_plugin_icons_and_composer_stack_v01230.py \
    && rm ./apply_local_plugin_icons_and_composer_stack_v01230.py \
    && python3 ./apply_live_tool_timeline_v01231.py \
    && rm ./apply_live_tool_timeline_v01231.py \
    && python3 ./apply_web_source_curation_v01232.py \
    && rm ./apply_web_source_curation_v01232.py \
    && python3 ./apply_provider_approval_flow_v01233.py \
    && rm ./apply_provider_approval_flow_v01233.py \
    && python3 ./apply_native_approval_and_activity_order_v01234.py \
    && rm ./apply_native_approval_and_activity_order_v01234.py \
    && python3 ./apply_mcp_approval_payload_fix_v01235.py \
    && rm ./apply_mcp_approval_payload_fix_v01235.py \
    && python3 ./apply_playwright_routing_timeout_v01236.py \
    && rm ./apply_playwright_routing_timeout_v01236.py \
    && python3 ./apply_playwright_chat_isolation_v01237.py \
    && rm ./apply_playwright_chat_isolation_v01237.py \
    && python3 ./apply_mobile_chat_layout_v01238.py \
    && rm ./apply_mobile_chat_layout_v01238.py \
    && python3 ./apply_conversation_authority_alignment_v01239.py \
    && rm ./apply_conversation_authority_alignment_v01239.py \
    && python3 ./apply_measured_chat_editor_v01240.py \
    && rm ./apply_measured_chat_editor_v01240.py \
    && python3 ./apply_compact_conversation_rows_v01241.py \
    && rm ./apply_compact_conversation_rows_v01241.py \
    && python3 ./apply_conversation_row_inset_v01242.py \
    && rm ./apply_conversation_row_inset_v01242.py \
    && python3 ./apply_notification_center_v01243.py \
    && rm ./apply_notification_center_v01243.py \
    && python3 ./apply_notification_watchlist_v01244.py \
    && rm ./apply_notification_watchlist_v01244.py \
    && python3 ./apply_notifications_scrolling_v01245.py \
    && rm ./apply_notifications_scrolling_v01245.py \
    && python3 ./apply_telegram_notify_compat_v01246.py \
    && rm ./apply_telegram_notify_compat_v01246.py \
    && python3 ./apply_telegram_exact_payload_v01247.py \
    && rm ./apply_telegram_exact_payload_v01247.py \
    && python3 ./apply_notification_websocket_and_tab_activity_v01248.py \
    && rm ./apply_notification_websocket_and_tab_activity_v01248.py \
    && python3 ./apply_telegram_plain_text_v01249.py \
    && rm ./apply_telegram_plain_text_v01249.py \
    && python3 ./apply_telegram_service_routing_v01250.py \
    && rm ./apply_telegram_service_routing_v01250.py \
    && python3 ./apply_semantic_tab_activity_v01251.py \
    && rm ./apply_semantic_tab_activity_v01251.py \
    && python3 ./apply_notification_watch_dedup_v01252.py \
    && rm ./apply_notification_watch_dedup_v01252.py \
    && python3 ./apply_voice_latency_and_activity_revisions_v01253.py \
    && rm ./apply_voice_latency_and_activity_revisions_v01253.py \
    && python3 ./apply_gmail_pre_registered_oauth_v01254.py \
    && rm ./apply_gmail_pre_registered_oauth_v01254.py \
    && python3 ./validate_release_manifest.py \
    && rm ./validate_release_manifest.py ./config.yaml \
    && python3 ./validate_inline_js.py ./app/static/index.html \
    && python3 ./validate_new_chat_wiring.py ./app/static/index.html \
    && python3 -m py_compile ./app/main.py \
    && rm ./apply_interface_hotfix.py ./apply_agent_controls_v090.py ./apply_plugin_manager_v0100.py ./apply_build_fix_v0101.py ./apply_ui_recovery_v0102.py ./apply_plugin_catalog_v0110.py ./apply_plugin_catalog_fix_v0111.py ./apply_plugin_dom_fix_v0112.py ./apply_plugin_init_fix_v0113.py ./apply_catalog_tdz_fix_v0114.py ./apply_catalog_escape_fix_v0115.py ./apply_catalog_backend_and_chat_ui_v0116.py ./apply_build_source_fix_v0118.py ./apply_plugin_controls_and_new_chat_v01119.py ./apply_chat_catalog_github_auth_v01110.py ./apply_catalog_cache_and_auth_clarity_v01111.py ./apply_plugin_tdz_final_fix_v01112.py ./apply_install_routing_fix_v01113.py ./apply_install_routing_build_fix_v01114.py ./apply_github_oauth_enable_v01115.py ./apply_entities_brand_and_oauth_env_v01116.py ./apply_oauth_popup_and_zbrano_brand_v01117.py ./apply_shared_files_and_github_state_v01118.py ./apply_frontend_repair_and_device_picker_v01119.py ./apply_github_chat_shared_fix_v01120.py ./apply_new_chat_draft_fix_v01121.py ./apply_new_chat_shared_files_fix_v01122.py ./apply_new_chat_sidebar_draft_v01123.py ./apply_remove_legacy_new_chat_interceptor_v01124.py ./apply_build_recovery_v01125.py ./apply_plugin_runtime_dom_fix_v01126.py ./apply_runtime_order_fix_v01127.py ./apply_plugin_manager_recovery_v01128.py ./apply_github_tool_approval_build_fix_v01129.py ./apply_github_tool_approval_policy_v01129.py ./apply_shared_files_runtime_recovery_v01130.py ./apply_catalog_and_plugin_compact_v01131.py ./apply_developer_mode_self_diagnostics_v0120.py ./apply_attach_and_operational_diagnostics_v0121.py ./apply_attachment_upload_fix_v0122.py ./apply_shared_files_and_diagnostics_v0123.py ./apply_investigation_engine_v0124.py ./apply_developer_tool_isolation_v0125.py ./apply_developer_indicator_and_policy_v0126.py ./apply_persistent_chat_attachment_labels_v0127.py ./apply_plugin_workspace_v0128.py ./apply_plugin_oauth_v0129.py ./apply_autonomous_automations_v01210.py ./apply_workshop_memory_writes_v01211.py ./apply_workshop_task_approval_v01212.py ./apply_release_alignment_v01213.py ./apply_zbrano_identity_v01214.py ./apply_ingress_oauth_callback_retry_v01215.py ./apply_playwright_developer_tools_v01216.py ./validate_inline_js.py ./validate_new_chat_wiring.py

COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD ["/run.sh"]
