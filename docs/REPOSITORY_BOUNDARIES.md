# ZBRANO repository boundaries

## Public Home Assistant core

This repository is the public, independently runnable ZBRANO Home Assistant app. It
owns the local user interface, local assistant runtime, Home Assistant integration,
voice pipeline, local memories, automations, notifications, plugins, and documented
integration contracts. A clean checkout must build without access to any private
repository.

Home Assistant options and runtime data belong in Supervisor-managed configuration
and `/data`. Personal entity IDs, locations, credentials, calibration recordings,
memory databases, local setup directories, and operator handoff notes must not be
committed.

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

`validate_public_repo.py` checks tracked paths, repository metadata, ignore rules,
and product-facing defaults. GitHub Actions runs it before image preparation. This is
a guardrail, not a substitute for secret scanning or reviewing every commit.
