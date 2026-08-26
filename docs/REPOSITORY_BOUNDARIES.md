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

The private canonical source repository is
`https://github.com/RoyceGith/ZBRANO_Core`. The clean-history public distribution
repository is `https://github.com/RoyceGith/ZBRANO_HA_Assistant` and contains only
Home Assistant installation metadata and documentation. The published container
retains the compatibility image path `ghcr.io/roycegith/jarvis-ha-assistant`; moving
source code must not strand installed Home Assistant apps on a different package
path.

## Public Home Assistant distribution

`RoyceGith/ZBRANO_HA_Assistant` is a clean-history public update repository. It
contains only Home Assistant repository metadata, add-on configuration, installation
documentation, and non-secret presentation assets. It points Supervisor at the
published GHCR image and does not contain the private application source or build
workflow.

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
distribution repository is created from an explicit allowlist rather than copied
from the source tree. These are guardrails, not substitutes for secret scanning or
reviewing every commit.
