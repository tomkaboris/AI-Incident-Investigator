# AI Incident Investigator

AI Incident Investigator is a FastAPI and CLI application that analyzes uploaded logs and runs structured AI-assisted incident investigations. Version 0.5.1 separates large log content from relational metadata through a pluggable storage layer.

## Features

- Single-agent analysis and multi-agent orchestration
- OpenAI or LiteLLM-routed models
- SQLite, PostgreSQL, and MySQL/MariaDB
- Metadata-only relational records; logs live in local or S3-compatible storage
- AWS S3, MinIO, and compatible object stores
- SHA-256 integrity verification before orchestration or download
- Configurable upload size, extension, content type, and binary-file policies
- Alembic migrations and typed Python package

## Installation

Local storage with SQLite:

```bash
pip install "ai-incident-investigator[sqlite]"
```

PostgreSQL, MySQL, or S3 support:

```bash
pip install "ai-incident-investigator[postgresql]"
pip install "ai-incident-investigator[mysql]"
pip install "ai-incident-investigator[s3]"
```

All integrations:

```bash
pip install "ai-incident-investigator[all]"
```

Development:

```bash
pip install -e ".[dev]"
```

## Configuration

Copy `.env.example` to `.env`.

```env
AI_PROVIDER=openai
AI_MODEL=gpt-5.4-mini
AI_API_KEY=your-key
DATABASE_URL=sqlite+aiosqlite:///./incident_investigator.db
STORAGE_BACKEND=local
LOCAL_STORAGE_PATH=./data/logs
MAX_UPLOAD_SIZE_BYTES=10485760
```

### S3 / MinIO

```env
STORAGE_BACKEND=s3
S3_BUCKET=incident-logs
S3_PREFIX=uploads
S3_ENDPOINT_URL=http://localhost:9000
S3_REGION=us-east-1
S3_ACCESS_KEY_ID=minioadmin
S3_SECRET_ACCESS_KEY=minioadmin
S3_USE_SSL=false
```

Omit `S3_ENDPOINT_URL` for normal AWS S3. Credentials may also come from the standard AWS credential chain.

### Upload policy

```env
ALLOWED_LOG_EXTENSIONS=.log,.txt,.out,.err,.json,.jsonl,.csv,.yaml,.yml
ALLOWED_LOG_CONTENT_TYPES=text/plain,text/csv,application/json,application/x-ndjson,application/yaml,text/yaml,application/octet-stream
REJECT_BINARY_LOGS=true
MAX_UPLOAD_SIZE_BYTES=10485760
MAX_LOG_CHARACTERS=50000
```

`MAX_UPLOAD_SIZE_BYTES` limits stored input. `MAX_LOG_CHARACTERS` independently limits text sent to the AI model.

## Database migrations

For production:

```env
DATABASE_AUTO_CREATE=false
```

```bash
alembic upgrade head
```

### Upgrade from 0.2.0

Migration `20260725_0002` removes `raw_log` from the relational database. It deliberately stops when existing incidents are present because it cannot safely select credentials and upload historical data to an external backend. Export important legacy logs, use a clean database, or create a deployment-specific data migration before running the upgrade.

## Run

```bash
incident-investigator
```

Open `http://127.0.0.1:8000/docs`.

## API examples

Analyze and store a log:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/incidents/analyze" \
  -H "Content-Type: multipart/form-data" \
  -F "log_file=@log-example.log"
```

Run orchestration:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/incidents/INCIDENT_ID/orchestrate"
```

Download and verify the original log:

```bash
curl -OJ "http://127.0.0.1:8000/api/v1/incidents/INCIDENT_ID/log"
```

## Storage design

The `incidents` table stores:

- backend name and opaque storage key
- SHA-256 checksum
- byte size and content type
- incident analysis and summary metadata

The object itself is read through the `LogStorage` protocol. New backends can implement `save`, `read`, `delete`, and `exists` without changing repositories or API workflows.

## Provider compatibility

| Provider path | Configuration | Structured output/tool support |
|---|---|---|
| OpenAI direct | `AI_PROVIDER=openai` | Primary tested path |
| Anthropic via LiteLLM | `AI_PROVIDER=litellm` | Model-dependent; validate before production |
| Gemini via LiteLLM | `AI_PROVIDER=litellm` | Model-dependent; validate before production |
| Azure/OpenAI-compatible via LiteLLM | `AI_PROVIDER=litellm` | Deployment/model-dependent |

## Quality checks

```bash
ruff check .
pytest
python -m build
python -m twine check dist/*
```

## Security notes

- Never commit `.env`, database files, stored logs, credentials, caches, or build artifacts.
- Keep S3/MinIO buckets private and grant only object-level permissions required by the application.
- SHA-256 detects corruption or replacement; it does not encrypt the log.
- Use TLS for remote storage and rotate any leaked credential.
- Uploaded logs may contain secrets. Apply retention policies and least-privilege access.

## License

MIT

## Premium dashboard

Version 0.6.0 includes a dashboard bundled directly in the Python package. No Node.js build is required.

Start the application:

```bash
incident-investigator
```

Open:

```text
http://127.0.0.1:8000/dashboard
```

The dashboard provides:

- operational overview and incident metrics;
- searchable incident library;
- guided upload with optional problem description;
- evidence-based root-cause workspace;
- causal-chain and remediation views;
- checksum-verified log viewer;
- multi-agent orchestration;
- generated Markdown incident reports;
- provider, database, storage, and security status.

The dashboard calls the same public REST API available under `/api/v1`. Swagger remains available at `/docs`.

## Multi-user workspaces

Version 0.7.0 adds organization-scoped accounts. Visit `/register` to create the first workspace and owner account, then use **Team → Add member** to create additional admin, investigator, or viewer accounts. Members of one workspace share incident history, while every incident, investigation, assignment and status change remains attributed to a user.

Browser authentication uses a signed HTTP-only session cookie, SameSite protection and a per-session CSRF token. Passwords are stored using Python's `hashlib.scrypt`; plaintext passwords are never persisted.

```env
SESSION_SECRET_KEY=replace-with-a-long-random-secret
SESSION_COOKIE_NAME=incident_investigator_session
SESSION_MAX_AGE_SECONDS=604800
SESSION_HTTPS_ONLY=true
REGISTRATION_ENABLED=true
```

Set `SESSION_HTTPS_ONLY=true` behind HTTPS. After the first workspace is created, public deployments may set `REGISTRATION_ENABLED=false` and let owners/admins create members from the Team page.

Roles:

- `owner`: full workspace and team control.
- `admin`: team management and incident operations.
- `investigator`: create incidents and run AI investigations.
- `viewer`: read-only access to shared workspace history.

The Help center is available from the bottom of the dashboard sidebar. It explains the initial single-agent workflow, the multi-agent workflow, evidence validation, fixes, reports and the purpose of the main controls.


## Recursive support-bundle analysis (0.8.0)
Upload ZIP, TAR/TGZ/TBZ2/TXZ, GZIP, BZIP2, or XZ bundles with nested archives using `POST /api/v1/incidents/analyze-archive`. The request accepts `archive_file`, required `problem_description`, optional `incident_time`, `timezone`, and `system_name`. The service safely extracts nested archives, blocks path traversal and links, enforces size/file/depth/compression-ratio limits, stores every artifact through the configured Local/S3/MinIO backend, calculates SHA-256 checksums, detects formats/components, normalizes timestamps, creates a cross-component timeline, redacts common secrets before AI processing, and returns evidence-linked root-cause analysis.

```bash
curl -X POST http://127.0.0.1:8000/api/v1/incidents/analyze-archive \
  -F archive_file=@support-bundle.zip \
  -F problem_description="Device disconnected during a call" \
  -F incident_time="2026-07-25T14:35:00" \
  -F timezone="Europe/Belgrade" \
  -F system_name="X52-2"
```

Additional endpoints: `GET /{incident_id}/artifacts`, `GET /{incident_id}/timeline`, and `GET /{incident_id}/archive-analysis`. Raw artifact download is disabled by default.

## 0.9.0 unified log and archive dashboard

The dashboard's **New investigation** form accepts either one regular log file or one
compressed support bundle. Archive extensions are detected automatically and routed to
`POST /api/v1/incidents/analyze-archive`. Archive incidents expose premium workspace tabs
for bundle metadata, extracted artifacts, evidence, causal chain, remediation, the
cross-component timeline, and the generated Markdown report.

### AI token usage and estimated cost

The application records input, output, and total token usage for initial log analysis,
archive analysis, and every multi-agent investigation when the selected provider returns
usage metadata. Cost is an estimate in USD and is calculated only from rates that you
configure; the package does not hardcode provider prices because they can change.

Configure USD prices per one million tokens:

```env
AI_MODEL_PRICING_JSON={"openai:your-model":{"input_per_1m":1.25,"output_per_1m":5.00},"anthropic/your-model":{"input_per_1m":3.00,"output_per_1m":15.00}}
```

Use the exact provider/model identifier shown in the dashboard. When usage is unavailable
or a model has no configured price, the UI displays that status instead of inventing a
cost. Provider invoices remain the authoritative billing record.

Apply the new schema:

```bash
alembic upgrade head
```
