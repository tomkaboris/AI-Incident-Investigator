"""Command-line interface for AI Incident Investigator."""

from __future__ import annotations

import argparse
import sys

import uvicorn


def _run_preflight() -> bool:
    """Print actionable startup diagnostics and return whether startup may continue."""
    from incident_investigator.config import get_settings
    from incident_investigator.preflight import collect_diagnostics, format_diagnostics, has_errors

    diagnostics = collect_diagnostics(get_settings())
    if diagnostics:
        print(format_diagnostics(diagnostics), file=sys.stderr)
    return not has_errors(diagnostics)


def _serve(host: str, port: int) -> None:
    if not _run_preflight():
        raise SystemExit(2)
    uvicorn.run(
        "incident_investigator.main:app",
        host=host,
        port=port,
    )


def _migrate(revision: str) -> None:
    if not _run_preflight():
        raise SystemExit(2)
    from incident_investigator.database.migration_runner import upgrade_database

    upgrade_database(revision)


def _doctor() -> None:
    from incident_investigator.config import get_settings
    from incident_investigator.preflight import collect_diagnostics, format_diagnostics, has_errors

    diagnostics = collect_diagnostics(get_settings())
    print(format_diagnostics(diagnostics))
    if has_errors(diagnostics):
        raise SystemExit(2)


def main() -> None:
    """Run the API server, migrations, or configuration diagnostics."""
    parser = argparse.ArgumentParser(prog="incident-investigator")
    subparsers = parser.add_subparsers(dest="command")

    serve_parser = subparsers.add_parser("serve", help="Start the API and dashboard server.")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8000)

    migrate_parser = subparsers.add_parser(
        "migrate", help="Upgrade the configured database with bundled Alembic migrations."
    )
    migrate_parser.add_argument("--revision", default="head")

    subparsers.add_parser(
        "doctor",
        help="Validate configuration and optional dependencies without starting the server.",
    )

    args = parser.parse_args()

    if args.command == "migrate":
        _migrate(args.revision)
        return

    if args.command == "doctor":
        _doctor()
        return

    if args.command == "serve":
        _serve(args.host, args.port)
        return

    # Backwards compatible: no subcommand starts the server.
    _serve("127.0.0.1", 8000)


if __name__ == "__main__":
    main()
