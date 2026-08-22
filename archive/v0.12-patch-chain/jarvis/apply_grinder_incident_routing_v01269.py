import os
from pathlib import Path


ROOT = Path(os.environ.get("ZBRANO_ROOT", "/opt/jarvis"))
MAIN = ROOT / "app/main.py"
INDEX = ROOT / "app/static/index.html"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"ZBRANO v0.12.69 expected one {label} marker; found {count}"
        )
    return text.replace(old, new, 1)


def require(text: str, marker: str, label: str) -> None:
    if marker not in text:
        raise RuntimeError(f"ZBRANO v0.12.69 patch missing: {label}")


def main() -> None:
    backend = MAIN.read_text(encoding="utf-8")
    frontend = INDEX.read_text(encoding="utf-8")

    runtime_marker = '''def runtime_chat_tools(search_mode: str = "auto", message: str = "") -> list[dict[str, Any]]:
    if is_home_assistant_priority_intent(message):
        return home_assistant_priority_tools()
    if developer_mode_enabled():
        return developer_runtime_tools() + developer_mcp_tools()
    tools = WORKSHOP_TOOLS + GRINDER_MONITOR_TOOLS + workshop_memory_function_tools() + gmail_direct_function_tools() + active_mcp_tools()
    search_tool = native_web_search_tool(search_mode)
    return tools + ([search_tool] if search_tool else [])
'''
    routed_runtime = r'''GRINDER_DIAGNOSTIC_INTENT_TERMS = (
    "incident", "freeze", "freezes", "froze", "frozen", "stuck", "reboot",
    "restarted", "reset reason", "telemetry", "heartbeat", "hx711",
    "measuring", "measurement", "flight recorder", "pre-failure",
    "pre failure", "boot id", "grinder status", "grinder monitor",
)


def is_grinder_diagnostic_intent(message: str) -> bool:
    normalized = " ".join(str(message or "").casefold().split())
    if "grinder" not in normalized and "espresso_grinder-" not in normalized:
        return False
    return any(term in normalized for term in GRINDER_DIAGNOSTIC_INTENT_TERMS)


def grinder_priority_tools() -> list[dict[str, Any]]:
    return list(GRINDER_MONITOR_TOOLS)


def runtime_chat_tools(search_mode: str = "auto", message: str = "") -> list[dict[str, Any]]:
    if developer_mode_enabled():
        return developer_runtime_tools() + developer_mcp_tools()
    if is_grinder_diagnostic_intent(message):
        return grinder_priority_tools()
    if is_home_assistant_priority_intent(message):
        return home_assistant_priority_tools()
    tools = WORKSHOP_TOOLS + GRINDER_MONITOR_TOOLS + workshop_memory_function_tools() + gmail_direct_function_tools() + active_mcp_tools()
    search_tool = native_web_search_tool(search_mode)
    return tools + ([search_tool] if search_tool else [])
'''
    backend = replace_once(
        backend,
        runtime_marker,
        routed_runtime,
        "grinder priority runtime",
    )

    priority_marker = '''def priority_system_instructions(base: str, message: str) -> str:
    if not is_home_assistant_priority_intent(message):
        return developer_system_instructions(base)
    return base + """

HOME ASSISTANT DEVICE CONTROL INTENT IS ACTIVE.'''
    priority_replacement = '''def priority_system_instructions(base: str, message: str) -> str:
    if not developer_mode_enabled() and is_grinder_diagnostic_intent(message):
        return base + """

GRINDER DIAGNOSTIC INTENT IS ACTIVE.
Use the provided local grinder diagnostic tools before answering. They are the authoritative runtime source and
are not Workshop Memory tools. When an incident identifier is present, call get_grinder_incident with that exact
identifier. Otherwise call list_grinder_incidents, select the incident matching the user's timing description,
then call get_grinder_incident. Analyze the bounded pre_failure_window rather than asking the user for an export.
If the user says they manually removed power after a freeze, treat the later POWER ON reset as operator-caused and
exclude it from classification of the initiating failure. Compare telemetry sequence, weight, HX711 data age, loop
timing, state age, heap, Wi-Fi/MQTT state, relay command, boot identifier, and reset evidence. Clearly separate
measured evidence from inference. Never claim these tools are unavailable when they are present in this request.
The grinder diagnostic tools are read-only and must never issue control commands.
""".strip()
    if not is_home_assistant_priority_intent(message):
        return developer_system_instructions(base)
    return base + """

HOME ASSISTANT DEVICE CONTROL INTENT IS ACTIVE.'''
    backend = replace_once(
        backend,
        priority_marker,
        priority_replacement,
        "grinder priority instructions",
    )

    backend = backend.replace('version="0.12.68"', 'version="0.12.69"')
    backend = backend.replace('"version": "0.12.68"', '"version": "0.12.69"')
    backend = backend.replace(
        '"X-ZBRANO-Frontend-Version": "0.12.68"',
        '"X-ZBRANO-Frontend-Version": "0.12.69"',
    )
    backend = backend.replace(
        '"name": "ZBRANO Developer Mode", "version": "0.12.68"',
        '"name": "ZBRANO Developer Mode", "version": "0.12.69"',
    )
    frontend = frontend.replace("HUD 0.12.68", "HUD 0.12.69")

    required = (
        "def is_grinder_diagnostic_intent(",
        "return grinder_priority_tools()",
        "GRINDER DIAGNOSTIC INTENT IS ACTIVE",
        "call get_grinder_incident with that exact",
        "Analyze the bounded pre_failure_window",
        'version="0.12.69"',
    )
    missing = [marker for marker in required if marker not in backend]
    if missing or "HUD 0.12.69" not in frontend:
        raise RuntimeError(
            "ZBRANO v0.12.69 verification failed: " + ", ".join(missing)
        )

    MAIN.write_text(backend, encoding="utf-8")
    INDEX.write_text(frontend, encoding="utf-8")


if __name__ == "__main__":
    main()
