"""Command-line interface for AI Incident Investigator."""

import argparse

import uvicorn


def _serve(host: str, port: int) -> None:
    uvicorn.run(
        "incident_investigator.main:app",
        host=host,
        port=port,
    )


def main() -> None:
    """Run the API server or a maintenance command."""
    parser = argparse.ArgumentParser(prog="incident-investigator")
    subparsers = parser.add_subparsers(dest="command")

    serve_parser = subparsers.add_parser("serve", help="Start the API and dashboard server.")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8000)

    migrate_parser = subparsers.add_parser(
        "migrate", help="Upgrade the configured database with bundled Alembic migrations."
    )
    migrate_parser.add_argument("--revision", default="head")

    args = parser.parse_args()

    if args.command == "migrate":
        from incident_investigator.database.migration_runner import upgrade_database

        upgrade_database(args.revision)
        return

    if args.command == "serve":
        _serve(args.host, args.port)
        return

    # Backwards compatible: no subcommand starts the server.
    _serve("127.0.0.1", 8000)


if __name__ == "__main__":
    main()
