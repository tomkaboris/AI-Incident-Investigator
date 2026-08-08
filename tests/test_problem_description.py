from incident_investigator.services.problem_context import normalize_problem_description


def test_problem_description_is_optional_and_normalized() -> None:
    assert normalize_problem_description(None, max_characters=100) is None
    assert normalize_problem_description("   ", max_characters=100) is None
    assert normalize_problem_description("  freezes after deploy  ", max_characters=100) == (
        "freezes after deploy"
    )
    assert normalize_problem_description("abcdef", max_characters=3) == "abc"
