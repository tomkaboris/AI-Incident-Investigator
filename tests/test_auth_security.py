from incident_investigator.auth.security import (
    hash_password,
    normalize_email,
    slugify,
    verify_password,
)


def test_password_hash_round_trip() -> None:
    encoded = hash_password("a-strong-password")
    assert encoded != "a-strong-password"
    assert verify_password("a-strong-password", encoded)
    assert not verify_password("wrong-password", encoded)


def test_identity_normalization() -> None:
    assert normalize_email(" User@Example.COM ") == "user@example.com"
    assert slugify("Platform Reliability Team") == "platform-reliability-team"
