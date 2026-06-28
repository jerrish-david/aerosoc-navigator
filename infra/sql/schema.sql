CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS roles (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS permissions (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS user_roles (
    user_id UUID NOT NULL REFERENCES users(id),
    role_id UUID NOT NULL REFERENCES roles(id),
    PRIMARY KEY (user_id, role_id)
);

CREATE TABLE IF NOT EXISTS assets (
    id UUID PRIMARY KEY,
    hostname TEXT NOT NULL UNIQUE,
    asset_type TEXT NOT NULL,
    owner TEXT NOT NULL,
    business_unit TEXT NOT NULL,
    criticality INTEGER NOT NULL CHECK (criticality BETWEEN 1 AND 5),
    internet_exposed BOOLEAN NOT NULL DEFAULT FALSE,
    data_classification TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS alerts (
    id UUID PRIMARY KEY,
    source TEXT NOT NULL,
    external_id TEXT NOT NULL,
    asset_id UUID NULL REFERENCES assets(id),
    raw_payload JSONB NOT NULL,
    severity TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'new',
    detected_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS cves (
    cve_id TEXT PRIMARY KEY,
    cvss_score NUMERIC(3,1) NOT NULL,
    cvss_vector TEXT NOT NULL,
    kev_flag BOOLEAN NOT NULL DEFAULT FALSE,
    exploit_maturity TEXT NOT NULL,
    published_at TIMESTAMPTZ NOT NULL,
    summary TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS iocs (
    id UUID PRIMARY KEY,
    type TEXT NOT NULL,
    value TEXT NOT NULL,
    source TEXT NOT NULL,
    confidence NUMERIC(3,2) NOT NULL,
    first_seen TIMESTAMPTZ NOT NULL,
    last_seen TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY,
    title TEXT NOT NULL,
    source_type TEXT NOT NULL,
    classification TEXT NOT NULL,
    checksum TEXT NOT NULL,
    approved_by TEXT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY,
    document_id UUID NOT NULL REFERENCES documents(id),
    chunk_text TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    embedding VECTOR(1536),
    chunk_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cases (
    id UUID PRIMARY KEY,
    case_type TEXT NOT NULL,
    title TEXT NOT NULL,
    asset_id UUID NULL REFERENCES assets(id),
    priority_score NUMERIC(4,2) NOT NULL DEFAULT 0.0,
    status TEXT NOT NULL DEFAULT 'open',
    assigned_to TEXT NULL,
    confidence_score NUMERIC(3,2) NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS case_findings (
    id UUID PRIMARY KEY,
    case_id UUID NOT NULL REFERENCES cases(id),
    mitre_technique TEXT NOT NULL,
    recommendation TEXT NOT NULL,
    evidence_score NUMERIC(3,2) NOT NULL,
    source_refs JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence_items (
    id UUID PRIMARY KEY,
    case_id UUID NOT NULL REFERENCES cases(id),
    evidence_type TEXT NOT NULL,
    ref_id TEXT NOT NULL,
    excerpt TEXT NOT NULL,
    source_uri TEXT NOT NULL,
    content_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS approvals (
    id UUID PRIMARY KEY,
    case_id UUID NOT NULL REFERENCES cases(id),
    action TEXT NOT NULL,
    requested_by TEXT NOT NULL,
    approved_by TEXT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    approved_at TIMESTAMPTZ NULL
);

CREATE TABLE IF NOT EXISTS model_runs (
    id UUID PRIMARY KEY,
    case_id UUID NOT NULL REFERENCES cases(id),
    prompt_version TEXT NOT NULL,
    retrieved_doc_ids JSONB NOT NULL,
    citation_coverage NUMERIC(3,2) NOT NULL,
    confidence_score NUMERIC(3,2) NOT NULL,
    blocked_reason TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_events (
    id UUID PRIMARY KEY,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    before_state JSONB NULL,
    after_state JSONB NULL,
    correlation_id TEXT NOT NULL,
    prev_hash TEXT NULL,
    event_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

