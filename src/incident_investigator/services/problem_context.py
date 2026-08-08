def normalize_problem_description(
    problem_description: str | None,
    *,
    max_characters: int,
) -> str | None:
    """Normalize optional user context before persistence and prompt use."""
    if problem_description is None:
        return None
    normalized = problem_description.strip()
    if not normalized:
        return None
    return normalized[:max_characters]
