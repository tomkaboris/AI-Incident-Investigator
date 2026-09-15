# AI Incident Investigator

AI Incident Investigator is a Python application for automated log analysis, incident investigation, and AI-assisted root-cause analysis. It combines a FastAPI backend, CLI tooling, database-backed incident records, optional S3-compatible storage, and a built-in dashboard for structured investigations.

## Why use it?

It helps teams investigate application and infrastructure incidents by:

- uploading one or more logs and analyzing them with AI;
- correlating stack traces and error hints to source code in GitHub/GitHub Enterprise;
- storing evidence, findings, and investigation metadata in a relational database;
- tracking AI token usage and estimated cost;
- exposing the full workflow through a web dashboard and REST API.

## Features

- Single-agent and multi-agent investigation flows
- OpenAI and LiteLLM-compatible model routing
- SQLite, PostgreSQL, and MySQL/MariaDB support
- Local storage or S3/MinIO-compatible object storage
- SHA-256 verification for uploaded logs and downloads
- Configurable upload, file-type, and binary-file policies
- Optional GitHub/GitHub Enterprise source correlation
- Built-in dashboard for uploads, evidence, reports, and workflow history
- Recursive archive support for support bundles and compressed artifacts
- Multi-user workspace and role-based access
- Alembic migrations and typed package structure

## Quick start

Install the package with the database backend you want to use:

```bash
# SQLite
pip install "ai-incident-investigator[sqlite]"

# PostgreSQL
pip install "ai-incident-investigator[postgresql]"

# MySQL / MariaDB
pip install "ai-incident-investigator[mysql]"
```

If you also want S3 or MinIO support:

```bash
pip install "ai-incident-investigator[sqlite,s3]"
```

For all integrations:

```bash
pip install "ai-incident-investigator[all]"
```

For local development:

```bash
pip install -e ".[dev]"
```

## Configuration

Create a `.env` file in the directory where you run the application:

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

Omit `S3_ENDPOINT_URL` for normal AWS S3. Credentials can also come from the standard AWS credential chain.

### Upload policy

```env
ALLOWED_LOG_EXTENSIONS=.log,.txt,.out,.err,.json,.jsonl,.csv,.yaml,.yml
ALLOWED_LOG_CONTENT_TYPES=text/plain,text/csv,application/json,application/x-ndjson,application/yaml,text/yaml,application/octet-stream
REJECT_BINARY_LOGS=true
MAX_UPLOAD_SIZE_BYTES=10485760
MAX_LOG_CHARACTERS=50000
```

`MAX_UPLOAD_SIZE_BYTES` limits stored input, while `MAX_LOG_CHARACTERS` limits the amount of text sent to the AI model.

## Run the app

Start the service:

```bash
incident-investigator
# or explicitly:
incident-investigator serve --host 127.0.0.1 --port 8000
```

Open the API docs:

- Swagger UI: http://127.0.0.1:8000/docs
- Dashboard: http://127.0.0.1:8000/dashboard

## Database migrations

For production deployments, it is usually recommended to disable automatic creation:

```env
DATABASE_AUTO_CREATE=false
```

Then run:

```bash
incident-investigator migrate
```

## Preflight and validation

Before starting the app, you can run:

```bash
incident-investigator doctor
```

This checks the current environment, configured database driver, AI provider, and optional storage dependencies. The same validation is also run automatically by `serve` and `migrate`.

## Source-code correlation

The GitHub/GitHub Enterprise integration is optional. When enabled, the application can use repository context to validate stack-trace and file references and present them as evidence, not as direct instructions to the model.

Example configuration:

```env
GITHUB_ENABLED=true
GITHUB_BASE_URL=https://github.company.example
GITHUB_TOKEN=replace-with-read-only-token
GITHUB_ORGANIZATION=my-organization
GITHUB_SOURCE_LOOKUP_ENABLED=true
GITHUB_CONTEXT_LINES=25
GITHUB_MAX_SEARCH_RESULTS=5
GITHUB_MAX_CANDIDATES=8
GITHUB_MAX_QUERIES=6
GITHUB_TIMEOUT_SECONDS=10
GITHUB_VERIFY_SSL=true
```

The integration is read-only and intentionally designed to fail safely: if GitHub is unavailable or lookup fails, the core investigation still continues with log-based inference as a fallback.

Possible source statuses include:

- `resolved`
- `inferred_from_log`
- `multiple_candidates`
- `not_found`
- `not_configured`
- `lookup_failed`

## API examples

Analyze and store a log:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/incidents/analyze" \
  -H "Content-Type: multipart/form-data" \
  -F "log_file=@log-example.log"
```

Run orchestration for an incident:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/incidents/INCIDENT_ID/orchestrate"
```

Download the original log:

```bash
curl -OJ "http://127.0.0.1:8000/api/v1/incidents/INCIDENT_ID/log"
```

## Advanced capabilities

### Recursive support-bundle analysis

The application can analyze compressed support bundles such as ZIP, TAR, TGZ, TBZ2, TXZ, GZIP, BZIP2, and XZ archives.

```bash
curl -X POST http://127.0.0.1:8000/api/v1/incidents/analyze-archive \
  -F archive_file=@support-bundle.zip \
  -F problem_description="Device disconnected during a call" \
  -F incident_time="2026-07-25T14:35:00" \
  -F timezone="Europe/Belgrade" \
  -F system_name="X52-2"
```

This workflow validates archive contents, enforces extraction limits, redacts common secrets, builds a component timeline, and exposes evidence-linked root-cause analysis.

### Multi-user workspaces

Version 0.7.0 adds workspace-scoped accounts and authorization. Roles include:

- `owner`
- `admin`
- `investigator`
- `viewer`

Example session settings:

```env
SESSION_SECRET_KEY=replace-with-a-long-random-secret
SESSION_COOKIE_NAME=incident_investigator_session
SESSION_MAX_AGE_SECONDS=604800
SESSION_HTTPS_ONLY=true
REGISTRATION_ENABLED=true
```

### AI token usage and cost tracking

The system tracks input, output, and total token usage for analysis runs when the provider returns usage metadata. You can configure USD pricing per one million tokens:

```env
AI_MODEL_PRICING_JSON={"openai:your-model":{"input_per_1m":1.25,"output_per_1m":5.00},"anthropic/your-model":{"input_per_1m":3.00,"output_per_1m":15.00}}
```

If a model has no configured price, the UI shows that status instead of inventing a value.

## Security notes

- Never commit `.env`, database files, stored logs, credentials, caches, or build artifacts.
- Keep S3/MinIO buckets private and grant only the minimum required permissions.
- SHA-256 verifies integrity, but it does not encrypt stored logs.
- Use TLS for remote storage and rotate any exposed credentials.
- Uploaded logs may contain secrets; apply retention and least-privilege access controls.

## Development and quality checks

```bash
ruff check .
pytest
python -m build
python -m twine check dist/*
```

## License

MIT
