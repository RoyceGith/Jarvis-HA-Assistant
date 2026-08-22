# ZBRANO v0.12 patch-chain archive

This directory preserves the historical build-time patch generators and their release-specific structural tests through v0.12.112.

They are retained for audit and archaeology only:

- `jarvis/` contains the 147 Python scripts that previously transformed the original backend and frontend during every image build.
- `tests/` contains the 121 release-specific tests that validated those scripts and their order.

Starting with v0.13.0, the generated v0.12.112 result is checked in under `jarvis/app/` as canonical source. Nothing in this archive is copied into the Home Assistant image or executed by the active build. New development and tests must target canonical source directly.

The frozen generated-file fingerprints and validation evidence are recorded in `docs/CANONICAL_BASELINE.md`.
