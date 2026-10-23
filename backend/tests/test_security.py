import hashlib

from app.core.security import generate_secure_token, hash_token


def test_hash_token_deterministic() -> None:
    raw = "test_magic_link_token_12345"
    expected = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    assert hash_token(raw) == expected
    assert len(hash_token(raw)) == 64


def test_hash_token_different_inputs() -> None:
    assert hash_token("token_a") != hash_token("token_b")


def test_generate_secure_token_length_and_entropy() -> None:
    t1 = generate_secure_token(32)
    t2 = generate_secure_token(32)
    assert len(t1) >= 32
    assert t1 != t2
