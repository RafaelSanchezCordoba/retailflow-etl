# ADR-0001 — Local development environment

- **Status:** Accepted
- **Date:** 2026-10-19

## Context

RetailFlow runs Apache Airflow and PostgreSQL via Docker Compose on the developer
machine: macOS Darwin 25.3.0, Intel x86_64, zsh. Two environment decisions had to be
made before any code existed, because both are expensive to reverse later.

**1. Repository location.** The repository initially lived under
`~/Library/Mobile Documents/com~apple~CloudDocs/` (iCloud Drive). Docker bind mounts
and a PostgreSQL data directory inside an iCloud-synced path hit two failure modes:
iCloud may evict files to the cloud and present them as dataless placeholders, and it
syncs partially-written files. A PostgreSQL data directory needs stable local
filesystem semantics and `fsync` behaviour that a sync daemon does not guarantee, so
this corrupts the cluster rather than merely slowing it down.

**2. Toolchain versions.** The versions found on first inspection were:

| Tool | Found | Verdict |
|---|---|---|
| Python | 3.11.8 | OK |
| Docker Engine | 20.10.22 | too old |
| Docker Compose | v2.15.1 | too old |
| Git | 2.55.0 | OK |
| Terraform | 1.16.4 | OK |

Docker Engine 20.10 predates the Compose spec features the Airflow reference
`compose.yaml` relies on, in particular `depends_on` with `condition: service_healthy`
combined with `service_completed_successfully` for the init container.

## Decision

1. The repository lives at `~/Develop/retailflow-etl`, outside any cloud-synced
   directory. Generated data (`data/`, `logs/`) stays there too and is gitignored.
2. Docker Desktop was upgraded before any container work started. Verified after
   upgrade: Docker Engine **29.9.1**, Docker Compose **v5.6.0**, and
   `docker run --rm hello-world` succeeded.
3. Python **3.11.8** is the project interpreter, in a project-local `.venv`.
   `requires-python` is set to `>=3.11,<3.13` — the upper bound is a guess at Airflow 3's
   supported range and **must be checked against the official Airflow documentation in
   Stage 3** before it is relied on.
4. macOS is the only *verified* platform. Windows and Linux instructions may be
   documented but must be marked unverified until actually executed there.

## Consequences

- Everything under the repository path is local-only. No cloud backup of working state;
  Git plus the GitHub remote is the backup mechanism.
- Contributors on Docker Engine < 24 cannot run the stack. This is acceptable: the
  project targets a single developer machine and documents the minimum.
- Pinning Python to a single minor version keeps the environment reproducible but means
  the CI matrix will also run 3.11 only, so 3.12 incompatibilities would go unnoticed
  until someone upgrades.
- The exact dependency set is deliberately almost empty at this stage. Runtime
  dependencies are added in the stage that first needs them, not up front.
