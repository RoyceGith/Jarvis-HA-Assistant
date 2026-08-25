# ZBRANO testing strategy

ZBRANO uses progressively broader test layers so fast checks remain useful while
runtime boundaries are validated in the environment where they actually execute.

## Unit and source-contract tests

The repository-level `tests/` suite runs with the Python standard library. It checks
isolated persistence and policy behavior, modular source boundaries, release markers,
and frontend wiring without requiring Home Assistant or application dependencies.

Run it from the repository root:

```text
python -m unittest discover -s tests
```

## Application integration tests

`jarvis/tests/` imports the real FastAPI application and sends requests through its
ASGI boundary. These tests use temporary persistence paths and do not contact Home
Assistant, Workshop Memory, OpenAI, or other external services.

The image build runs this suite after installing the exact runtime dependencies and
before publishing an image. Initial coverage verifies:

- application import plus startup and shutdown handler registration;
- `/api/health` and frontend delivery;
- Settings API validation and persisted round trips;
- Chat API creation, rename, listing, deletion, and persisted round trips.

Inside an environment with `jarvis/requirements.txt` installed, run:

```text
cd jarvis
python -m unittest discover -s tests -p "test_*.py"
```

Future browser, migration, and release tests should build on this boundary while
keeping all external integrations deterministic and opt-in.
