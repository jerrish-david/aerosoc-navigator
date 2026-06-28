# Architecture

## Purpose

`AeroSOC Navigator` is an AI-augmented cybersecurity operations platform. It supports alert triage and vulnerability prioritization without delegating final security decisions to the model.

## Architectural Principles

- Zero trust for every user and service call
- Deterministic controls remain authoritative
- Retrieval uses approved sources only
- High-risk actions require human approval
- Security telemetry and audit records are first-class outputs

## Layers

### Frontend

The frontend presents cases, alerts, evidence, and approval tasks. It should not contain security decision logic.

### Backend API

The FastAPI layer handles request validation, orchestration, and role-aware workflows.

### Security Layer

This layer validates tokens, checks RBAC, enforces rate limits, strips prompt-injection patterns, and validates model outputs.

### RAG Pipeline

The pipeline chunks approved documents, stores embeddings, performs hybrid retrieval, applies metadata filters, and injects evidence into prompts.

### Vector Database

`PostgreSQL + pgvector` stores both operational and retrieval data to simplify joins and minimize architectural sprawl.

### LLM Layer

Azure OpenAI is used for summarization, ATT&CK mapping suggestions, and triage recommendations. The model is advisory only.

### Logging and Monitoring

Structured logs support operations. Audit events support accountability and compliance.

