# AeroSOC Navigator

`AeroSOC Navigator` is an AI-assisted SOC triage and vulnerability prioritization platform designed as a realistic cybersecurity internship portfolio project.

The application ingests alerts, CVEs, IOCs, and approved internal documentation, then produces citation-backed analyst recommendations with human approval checkpoints. The LLM augments analysts, but deterministic controls remain the source of truth.

## Portfolio Goals

- Demonstrate SOC alert triage workflows
- Show vulnerability management and risk prioritization
- Implement secure RAG with enterprise guardrails
- Enforce zero trust, RBAC, audit logging, and approval workflows
- Map controls to NIST CSF, NIST AI RMF, CIS Controls, OWASP Top 10, and MITRE ATT&CK

## Core Stack

- Python
- FastAPI
- PostgreSQL
- pgvector
- Azure OpenAI
- Docker
- GitHub Actions

## Repository Layout

- `app/`: backend application
- `tests/`: unit, integration, security, and prompt-injection tests
- `docs/`: architecture, threat model, API, and compliance mappings
- `infra/`: Docker and Azure deployment scaffolding
- `.github/workflows/`: CI and security automation

## Quick Start

1. Copy `.env.example` to `.env`.
2. Review `infra/sql/schema.sql`.
3. Start services with `docker compose up --build`.
4. Open the API docs at `/docs`.

## Current Status

This scaffold is intentionally half-implemented:

- The API surface and architecture are real.
- Security-critical workflows include pseudocode and TODO markers.
- The project is structured to support clean architecture, DI, repository pattern, and secure defaults.

## Demo Story

1. Ingest an alert from a SIEM-like source.
2. Enrich it with asset criticality and vulnerability context.
3. Retrieve approved runbooks and threat bulletins via hybrid retrieval.
4. Generate a structured triage draft with citations.
5. Validate confidence and evidence coverage.
6. Require human approval for high-risk actions.
7. Write immutable audit events for every major step.

## Ruach Institute portal

An isolated student portal is mounted at `/institute`. It uses Supabase Magic Links,
server-rendered pages, approved-student enrollment checks, and database RLS.
See [the setup and deployment guide](docs/ruach-institute.md) before enabling it.
