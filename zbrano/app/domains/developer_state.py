from __future__ import annotations

def developer_mode_enabled() -> bool:
    """Developer capabilities are not available in customer builds."""
    return False


def developer_system_instructions(base: str) -> str:
    return base
