# ZBRANO repository boundaries

## Private core source

`RoyceGith/ZBRANO_Core` is the private canonical source and build repository. It owns
the local user interface, assistant runtime, Home Assistant integration, voice
pipeline, local memories, automations, notifications, plugins, tests, and container
publication workflow.

Home Assistant options and runtime data belong in Supervisor-managed configuration
and `/data`. Personal entity IDs, locations, credentials, calibration recordings,
memory databases, local setup directories, and operator handoff notes must not be
committed.

Grinder monitoring is an owner-specific private extension. It must not appear in
first-run onboarding, general product defaults, public product documentation,
subscription entitlements, or installations distributed to other users. Its current
compatibility path must be separated without breaking the owner's stored settings.
Release 0.13.164 migrated any enabled or customized legacy add-on values into
permission-restricted `/data/zbrano_owner_extensions.json` and made the extension
runtime prefer the migrated record. After that compatibility release was installed
on the owner's system, release 0.13.165 removed all Grinder-specific fields from the
general Home Assistant add-on options and startup environment. The private runtime
continues from its migrated `/data` record without exposing the extension to other users.

The private canonical source repository is
`https://github.com/RoyceGith/ZBRANO_Core`. The public distribution repository is
`https://github.com/RoyceGith/ZBRANO_HA_Assistant`; its current tree contains only
Home Assistant installation metadata and documentation. It retains the last
previously public source commit and the initial thin-distribution head as merge
ancestry so Supervisor clones cached on either side of the transition can
fast-forward across the split. The published container
retains the compatibility image path `ghcr.io/roycegith/jarvis-ha-assistant`; moving
source code must not strand installed Home Assistant apps on a different package
path.

## Public Home Assistant distribution

`RoyceGith/ZBRANO_HA_Assistant` is a thin public update repository. Its current tree
contains only Home Assistant repository metadata, add-on configuration, installation
documentation, and non-secret presentation assets. It points Supervisor at the
published GHCR image and contains no current application source or build workflow.
Source commits made after the split exist only in `ZBRANO_Core`; historical source
that was already public remains reachable and cannot be retroactively revoked.
The v0.13.57 bridge commit joins both public transition histories while retaining
only explicitly allowlisted distribution files in its current tree. Home Assistant
configuration translations are presentation metadata and may ship beside the app
configuration without exposing application source.
The allowlisted `jarvis/icon.png` and `jarvis/logo.png` are public presentation
assets. Their PNG format, dimensions, transparency, and bounded size are validated
before publication.
The v0.13.58 release preserves that bridge and aligns the container-only release
fixtures with the published runtime version.

## Private platform services

Future hosted capabilities belong in a separate private repository. This includes:

- customer identity, organizations, accounts, and subscription entitlements;
- billing provider integration, licensing, plans, and premium policy;
- the hosted ZBRANO community, moderation, abuse controls, and community data;
- cloud deployment infrastructure, production observability, and service secrets;
- proprietary server-side intelligence or premium modules.

The private platform may depend on published public-core contracts. The public core
must not import private source code, require private build artifacts, or contain a
hidden bypass for subscription checks. Optional hosted capabilities must fail closed
and leave local Home Assistant functionality usable.

## Shared contracts

When hosted services are implemented, their protocol schemas and compatibility
versions should be published in this repository without credentials or proprietary
implementation. Authentication tokens are runtime data and must use Home Assistant
secret storage. The public client must treat all entitlement and community responses
as untrusted network input.

## Enforcement

`validate_public_repo.py` checks tracked paths, distribution metadata, ignore rules,
and product-facing defaults before the private core publishes an image. The public
distribution repository tree is created from an explicit allowlist rather than copied
from the source tree. These are guardrails, not substitutes for secret scanning or
reviewing every commit.
