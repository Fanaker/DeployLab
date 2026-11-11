# DeployLab — release checklist

**Version:** 1.0.0  
**Date:** 2026-11-11  
**Scope:** DevOps/CI/CD demonstration. No cloud resources are created.

## Verified in the creation environment
- FastAPI API and SQLite persistence tested through five Pytest tests.
- JavaScript parser check passed (`node --check web/app.js`).
- Four screenshot views rendered from bundled frontend and API response.
- `/health`, `/ready`, `/metrics`, simulated releases and rollback tested.

## Prepared, not executed here
- Dockerfile image build (Docker engine unavailable in build environment).
- Docker Compose API+Prometheus runtime (requires Docker on user's machine).
- GitHub Actions execution (runs after pushing to GitHub).

## Simulated/illustrative data
- Historical deploy pipeline, service statuses, traffic and P95 latencies.
- The dashboard's deployment and rollback buttons record demo events in SQLite; they do not deploy software to production.
- The security-scan card is a UI illustration, not implemented in the current CI workflow.
