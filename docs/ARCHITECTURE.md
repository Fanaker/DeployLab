# DeployLab architecture and CI decisions

## Running processes
- API: FastAPI, local port 8000; SQLite file stored under `/service/data/` with a Docker named volume.
- Monitoring: Prometheus port 9090, reads `/metrics` every 15 seconds using the Compose service DNS `retail-api`.
- Frontend: static HTML/CSS/JS served from the same FastAPI service.

## CI
`.github/workflows/ci.yml` triggers on push/PR, uses Python 3.11, runs API tests, syntax-checks JavaScript, and builds a local Docker image without pushing to a registry. This avoids cloud secrets.

## Health and telemetry
`/health` is a lightweight liveness route; `/ready` executes a SQLite `SELECT 1`; `/metrics` exposes request counters and uptime. It does not provide complete application performance monitoring. The dashboard's historical graphs are fictitious sample data.

## Rollback demonstration
A release is a row in SQLite and rollback changes its status. This teaches auditability and state transitions but does not control container orchestration. To build an actual deployment pipeline, add a registry, isolated environments, approval checks, deployment targets and executable rollback automation.
