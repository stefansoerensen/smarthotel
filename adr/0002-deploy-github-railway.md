# ADR-0002: Deploy from GitHub to Railway, with CI as the only test loop

Status: Accepted (2026-11-12). Mirrors pms-clone ADR-0006 (hub d35, d36).

## Context
The developer machine has no local runtime. The project needs one place where tests run and one
where the application runs, and it should work like the Hotel OS repository.

## Decision
`.github/workflows/ci.yml` is the only test loop: backend (Black, isort, pytest with a
Postgres service, migration drift), frontend (ESLint, Vitest, build) and an image build with a
smoke test. Railway runs two services, managed Postgres and one container from the root
`Dockerfile`; it waits for CI and runs migrations and bootstrap as the pre-deploy command. Work lands
directly on `main`.

## Consequences
+ Reproducible tests; a failing migration cannot take the site down.
− Feedback costs a push and a few minutes; tasks must end at a pushable state.
− `main` is production; there is no staging.
− The edge gateway (ADR-0004) is a second image; it gets its own CI job in SB2.
