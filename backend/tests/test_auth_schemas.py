"""Authentication schema and password-hashing dependency checks."""

import pytest
from pydantic import ValidationError

from app.core.security import hash_password, verify_password
from app.schemas.auth import RegisterRequest


def test_registration_schema_accepts_valid_email():
    request = RegisterRequest(email="person@example.com", password="password123")
    assert request.email == "person@example.com"


def test_registration_schema_rejects_short_password():
    with pytest.raises(ValidationError):
        RegisterRequest(email="person@example.com", password="short")


def test_password_hash_round_trip():
    password = "password123"
    assert verify_password(password, hash_password(password))
