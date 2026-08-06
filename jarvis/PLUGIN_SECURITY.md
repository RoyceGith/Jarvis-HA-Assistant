# Jarvis MCP Plugin Security Model

Jarvis v0.10.0 uses deny-by-default controls for MCP plugins.

## Enforced controls

- Only public `https://` MCP endpoints are accepted.
- URLs containing embedded credentials are rejected.
- Localhost, `.local`, private, loopback, link-local, reserved, and non-global IP targets are rejected after DNS resolution.
- HTTP redirects are rejected during validation and tool discovery.
- New plugins are installed disabled.
- Discovered tools are blocked unless the MCP server explicitly declares `readOnlyHint: true`.
- Each read-only tool must be enabled explicitly.
- Write-capable and unknown tools cannot be enabled in v0.10.0.
- Only enabled, allow-listed read-only tools are sent to the OpenAI Responses API.
- Bearer tokens are stored separately in `/data/plugins/secrets.json` with file mode `0600`.
- Tokens are never returned by plugin APIs or displayed in the interface.
- Installed-plugin and discovered-tool counts are bounded.

## Deliberate limitation

Write-capable MCP tools are excluded until Jarvis has a complete approval-request interface and auditable approval lifecycle.
