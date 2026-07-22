import uvicorn


def main() -> None:
    """Start the AI Incident Investigator API server."""
    uvicorn.run(
        "incident_investigator.main:app",
        host="127.0.0.1",
        port=8000,
    )


if __name__ == "__main__":
    main()