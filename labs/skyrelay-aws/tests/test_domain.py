import pytest
from src.domain import normalize, digest, identity, key

def test_canonical_digest():
    assert digest({"a":1,"b":2}) == digest({"b":2,"a":1})

def test_rejects_invalid_input():
    with pytest.raises(ValueError):
        normalize({"type":"BAD","payload":{}})
    with pytest.raises(ValueError):
        normalize({"type":"invoice.paid","payload":"bad"})

def test_tenant_comes_from_auth_claims():
    assert identity({"requestContext":{"authorizer":{"claims":{"sub":"user-12345"}}}}) == "user-12345"
    with pytest.raises(ValueError):
        identity({})

def test_idempotency_case():
    assert key({"IDEMPOTENCY-KEY":"sale-12345"}) == "sale-12345"
