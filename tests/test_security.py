"""Negative security tests: tampered signatures, expiry, scope and tenant isolation."""
from datetime import datetime, timedelta, timezone
import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from vectorharbor.security import require_principal, require_scope

SECRET = "testing-only-secret-with-at-least-32-bytes"
def token(**changes):
    now = datetime.now(timezone.utc)
    claims = {"sub": "user-123", "tenant_id": "acme", "scope": "events:read events:write",
              "iss": "vectorharbor-local", "aud": "vectorharbor-api",
              "iat": now, "exp": now + timedelta(minutes=5)}
    claims.update(changes)
    return jwt.encode(claims, SECRET, algorithm="HS256")

@pytest.fixture(autouse=True)
def key(monkeypatch):
    monkeypatch.setenv("VECTORHARBOR_JWT_SECRET", SECRET)

def authenticate(value):
    return require_principal(HTTPAuthorizationCredentials(scheme="Bearer", credentials=value))

def test_valid_token_and_tenant_permissions():
    principal = authenticate(token())
    assert principal.tenant_id == "acme"
    require_scope(principal, "acme", "events:read")

@pytest.mark.parametrize("value", [
    "not-a-jwt", jwt.encode({"sub": "user-123", "tenant_id": "acme"}, "wrong-key", algorithm="HS256"),
    token(exp=datetime.now(timezone.utc) - timedelta(minutes=5)),
])
def test_rejects_invalid_or_expired_jwt(value):
    with pytest.raises(HTTPException) as exc:
        authenticate(value)
    assert exc.value.status_code == 401

def test_rejects_other_tenant_even_with_valid_token():
    with pytest.raises(HTTPException) as exc:
        require_scope(authenticate(token()), "other-tenant", "events:read")
    assert exc.value.status_code == 403

def test_rejects_missing_scope():
    with pytest.raises(HTTPException) as exc:
        require_scope(authenticate(token(scope="events:read")), "acme", "events:write")
    assert exc.value.status_code == 403

def test_rejects_missing_credentials():
    with pytest.raises(HTTPException) as exc:
        require_principal(None)
    assert exc.value.status_code == 401
