## 0.10.0 - GitHub/GHE source correlation

### Added
- Optional read-only GitHub and GitHub Enterprise source-code correlation.
- Stack-trace/file/line extraction for Python, Java/Kotlin, and generic source locations.
- Error-text source search with bounded candidate and context limits.
- `source_analysis` JSON on initial and multi-agent investigation results without a DB migration.
- Dashboard Source Analysis tab with repository/file/function/line, confidence, source snippet, and link.
- Log-only fallback when GitHub is disabled or unavailable.
- GitHub configuration checks in `incident-investigator doctor`.
- Source-correlation unit tests and documented `.env` settings.

### Security
- GitHub tokens remain server-side and are never sent to AI models or returned by API/health/dashboard.
- Retrieved source is treated as untrusted evidence in AI prompts.
- GitHub integration failures cannot fail the core incident-analysis workflow.

## 0.9.0 - Unified archive dashboard and AI cost estimates

### Added
- One premium upload form for regular logs and recursive support bundles.
- Automatic archive detection and archive-specific incident metadata fields.
- Archive workspace tabs for overview, artifacts, cross-component timeline, evidence, fixes and report.
- Token usage persistence for initial, archive and multi-agent analyses.
- Configurable per-model USD pricing and estimated investigation cost.
- Alembic migration `20260726_0006_ai_usage_costs`.

### Notes
- Costs are estimates based on configured rates and provider-returned usage. Provider billing is authoritative.
- Missing usage or pricing is shown explicitly and never replaced with a guessed amount.

# Changelog

## 0.8.0 - Recursive support-bundle investigation
- Recursive ZIP/TAR/GZIP/BZIP2/XZ support-bundle extraction.
- Archive-bomb, path-traversal, link, file-count, depth, size, and ratio protection.
- Artifact manifest, checksums, Local/S3/MinIO persistence, component/format detection.
- Timestamp normalization, incident-time windowing, multi-file timeline, correlation IDs.
- Evidence-linked cross-component AI root-cause analysis and secret redaction.
- Archive artifact, timeline, and analysis REST endpoints.
- Alembic archive schema migration and extraction tests.

# Changelog

## 0.5.0 - 2026-07-25

### Added
- `LogStorage` protocol and backend factory.
- Atomic local-filesystem storage with path-traversal protection.
- S3-compatible storage for AWS S3, MinIO, and compatible object stores.
- SHA-256 integrity checks, storage keys, content types, and byte-size metadata.
- Download endpoint with checksum verification: `GET /api/v1/incidents/{incident_id}/log`.
- Configurable extension, content-type, binary-file, and maximum-size upload policies.
- Tests for local storage, integrity verification, and upload validation.
- Alembic migration from database-resident logs to metadata-only incident records.

### Changed
- Relational databases no longer store `raw_log`; they store only storage metadata and analysis results.
- Orchestration reads and verifies logs through the configured storage backend.
- Package version updated to 0.5.0.

### Migration warning
- Migration `20260725_0002` stops when legacy incident rows exist because a schema migration cannot safely choose or populate an external storage backend. Export/re-import important logs before upgrading.

## 0.2.0 - 2026-07-25

### Added
- Provider-neutral AI runtime with OpenAI and LiteLLM support.
- SQLite, PostgreSQL, and MySQL optional dependency groups.
- Alembic migration environment and initial schema.
- Provider, model, prompt version, and execution duration metadata.
- Configurable upload size and database auto-create behavior.
- Initial configuration, provider, and database tests.

## 0.5.1 - 2026-07-25

### Added
- Optional `problem_description` form field for the initial incident analysis endpoint.
- Persistent problem descriptions on incident records and API responses.
- Problem context in both single-agent analysis and multi-agent orchestration.
- Prompt rules that treat user descriptions as unverified context rather than technical proof or executable instructions.
- Alembic migration `20260725_0003` and tests for normalization and prompt propagation.

## 0.6.0 - Premium dashboard

- Added a bundled responsive dashboard at `/dashboard`.
- Added overview metrics, severity/category analytics, incident search and filtering.
- Added guided log upload with optional problem description.
- Added incident workspace with evidence, causal chain, fixes, report and log viewer tabs.
- Added in-dashboard multi-agent orchestration and report export actions.
- Added AI, database, storage and security settings overview.
- Added dashboard REST endpoints for overview and incident list data.
- Added dark/light themes and mobile navigation.

## 0.7.0 - Multi-user workspaces

### Added
- Login and workspace registration pages.
- Signed HTTP-only session authentication with SameSite cookies.
- CSRF protection for state-changing authenticated requests.
- Scrypt password hashing and basic login-attempt rate limiting.
- Organizations, memberships and owner/admin/investigator/viewer roles.
- Workspace-scoped incident and investigation access.
- Incident creator, assignee and investigation initiator attribution.
- Incident activity audit trail and collaboration endpoints.
- Team management with owner/admin member creation.
- User profile, team page, first-run onboarding and Help center.
- Help explanations for initial analysis, multi-agent investigation and key buttons.
- Alembic migration `20260726_0004_multi_user_workspaces`.

### Migration warning
- The multi-user migration intentionally stops when legacy incident rows exist because they have no safe organization or creator assignment. Export/recreate existing development incidents, or write a deployment-specific data migration before upgrading production data.
