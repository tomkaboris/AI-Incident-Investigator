# AI Incident Investigator

> AI-powered incident analysis platform built with **FastAPI**, **OpenAI Agents SDK**, **SQLAlchemy**, and **SQLite**.

## Overview

AI Incident Investigator analyzes application and device logs using AI agents to:

- Classify incidents
- Estimate severity
- Identify probable root causes
- Generate remediation recommendations
- Produce structured investigation reports
- Store investigations for later review

The project follows modern software engineering practices:

- Clean Architecture
- Repository Pattern
- Async SQLAlchemy
- Dependency Injection
- Strong typing with Pydantic
- SOLID principles

---

# Features

- Upload log files
- AI-powered incident analysis
- Multi-agent orchestration
- Structured JSON responses
- Persistent incident history
- Investigation history
- REST API
- Ready for future PostgreSQL migration

---

# Architecture

```text
Client
   │
   ▼
FastAPI API
   │
   ▼
Application Services
   │
   ├── Incident Analyzer
   ├── Orchestrator
   └── Storage
   │
   ▼
Repositories
   │
   ▼
SQLite
```

---

# Project Structure

```text
src/
├── agents/
├── api/
├── database/
├── models/
├── repositories/
├── services/
└── main.py
```

---

# API

## POST /api/v1/incidents/analyze

Uploads a log file, performs the initial AI analysis, stores the incident and returns the created incident.

## POST /api/v1/incidents/{incident_id}/orchestrate

Runs a detailed multi-agent investigation using the original uploaded log.

## GET /api/v1/incidents/{incident_id}

Returns the stored incident.

## GET /api/v1/incidents/{incident_id}/investigations

Returns every investigation performed for the incident.

---

# Database

## incidents

Stores:

- Incident metadata
- Initial AI analysis
- Uploaded log (current implementation)
- Creation timestamp

## incident_investigations

Stores every orchestration result linked to an incident.

Relationship:

```text
Incident
   │
   └────── 1:N ──────► Investigation
```

---

# Log Storage Strategy

## Current implementation

The current implementation stores the uploaded log inside the database.

This design was intentionally chosen because it:

- keeps the project simple
- avoids external storage dependencies
- allows deterministic investigations
- allows orchestration without uploading the same log again

This approach is suitable for **small and medium-sized logs**.

---

# Limitations

Large production logs (for example 100–200 MB or hundreds of thousands of log lines) should **not** be stored directly in the database.

Instead, store:

- metadata in the database
- original log in object storage

Example architecture:

```text
Database
    │
    ├── filename
    ├── SHA256
    ├── size
    ├── storage_path
    ▼

Object Storage
    ├── Local Storage
    ├── Amazon S3
    ├── Azure Blob
    ├── MinIO
```

Only the storage implementation changes. The orchestration pipeline remains identical.

---

# Why keep the uploaded log?

Keeping the uploaded log enables:

- deterministic AI investigations
- reproducible results
- multiple orchestrations
- comparison between AI models
- investigation history

---

# Installation

```bash
git clone <repository>

cd AI-Incident-Investigator

python -m venv .venv

source .venv/bin/activate

pip install -e ".[dev]"
```

Create:

```text
.env
```

Example:

```text
OPENAI_API_KEY=your_api_key
OPENAI_MODEL=gpt-5.5
DATABASE_URL=sqlite+aiosqlite:///incident_investigator.db
```

Run:

```bash
fastapi dev src/incident_investigator/main.py
```

---

# Example Workflow

```text
Upload Log
      │
      ▼
Initial AI Analysis
      │
      ▼
Incident Created
      │
      ▼
Run Orchestration
      │
      ▼
Investigation Stored
      │
      ▼
View Investigation History
```

---

# Technology Stack

- Python 3.12+
- FastAPI
- SQLAlchemy 2.x
- SQLite
- Pydantic v2
- OpenAI Agents SDK

---

# Design Principles

- Clean Architecture
- Repository Pattern
- Dependency Injection
- SOLID
- Async-first
- Testability
- Separation of Concerns

---

# Future Improvements

- PostgreSQL
- Object Storage
- Background workers
- Streaming log uploads
- Semantic log retrieval (RAG)
- Vector database
- Authentication
- Web UI
- Metrics & Observability

---

# License

MIT License


---

# cURL Examples

## Analyze a log file

```bash
curl -X POST \
  "http://127.0.0.1:8000/api/v1/incidents/analyze" \
  -H "accept: application/json" \
  -F "log_file=@logs/sample.log"
```

Example response:

```json
{
  "id": "7bdbd2d9-f15c-4c39-a4d7-fef63d9dfb2f",
  "status": "analyzed",
  "filename": "sample.log",
  "created_at": "2026-07-23T18:35:17.921Z",
  "analysis": {
    "title": "Teams application crash",
    "category": "Application",
    "severity": "High",
    "summary": "Application terminated unexpectedly.",
    "probable_root_cause": "Unhandled NullPointerException.",
    "confidence": 0.94
  }
}
```

---

## Run a detailed orchestration

Replace `<incident_id>` with the ID returned by `/analyze`.

```bash
curl -X POST \
  "http://127.0.0.1:8000/api/v1/incidents/<incident_id>/orchestrate" \
  -H "accept: application/json"
```

---

## Get an incident

```bash
curl \
  "http://127.0.0.1:8000/api/v1/incidents/<incident_id>"
```

---

## Get investigation history

```bash
curl \
  "http://127.0.0.1:8000/api/v1/incidents/<incident_id>/investigations"
```
