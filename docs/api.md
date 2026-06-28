# API Overview

## Key Endpoints

- `POST /api/v1/alerts`
- `GET /api/v1/cases`
- `GET /api/v1/cases/{case_id}`
- `POST /api/v1/cases/{case_id}/triage`
- `POST /api/v1/cases/{case_id}/approve`
- `POST /api/v1/documents/upload`
- `GET /api/v1/dashboard/metrics`
- `GET /api/v1/health`

## Design Notes

- All write endpoints generate audit events.
- All protected endpoints require a validated bearer token.
- High-risk actions must pass authorization and approval policy checks.

