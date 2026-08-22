# ZBRANO canonical-source baseline

## Frozen release

- Release: `0.12.112`
- Git commit: `435ef91`
- Image: `zbrano-canonical-baseline:0.12.112`
- Baseline date: 2026-08-22

Feature development was frozen at this release before canonical-source consolidation.

## Generated application fingerprints

These files were extracted from the successfully validated image after the complete historical patch chain ran.

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `app/main.py` | 542,732 | `1FCE3174411BAAC69980DA445E9EFCFED74B4315B6FD793F22DCC184A4B2FCBA` |
| `app/static/index.html` | 462,923 | `8BEBB7A10ACF864AD65C83C5B9F667975BDB642E2E5BA2B7B356A7A03904E961` |
| `app/intent_router.py` | 1,483 | `FC048DC2DF9D2BDB693697CF474C4A40964896D429468A124458E6782BA84732` |

## Baseline validation

- Complete Docker image build: passed.
- Release manifest alignment for `0.12.112`: passed.
- Inline JavaScript validation: 28 script blocks passed.
- New Chat wiring validation: passed.
- Generated backend Python compilation: passed.
- Current-release regression `tests/test_v012112.py`: 3 passed.
- Core unittest suite: 31 passed; one obsolete assertion still expected the original `0.8.5` source marker and was classified as test debt rather than a product failure.

## Canonicalisation rule

The generated files above are the behavioral source of truth. The `0.13.0` conversion may change release markers, build layout, tests, and documentation, but it must not intentionally remove or alter an existing feature. Subsequent architecture work must begin from the canonical files rather than reconstructing the historical patch chain.
