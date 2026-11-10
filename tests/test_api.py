from fastapi.testclient import TestClient
from vectorharbor.main import app

client = TestClient(app)
DATA = {"event_type": "order.created", "payload": {"order_id": 40}}


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_idempotency_replay_and_conflict():
    headers = {"X-Tenant-Id": "alpha", "Idempotency-Key": "request-101"}
    first = client.post("/events", json=DATA, headers=headers)
    assert first.status_code == 201
    second = client.post("/events", json=DATA, headers=headers)
    assert second.status_code == 201
    assert second.json()["id"] == first.json()["id"]
    assert second.json()["replayed"] is True
    conflict = client.post(
        "/events", json={"event_type": "order.cancelled", "payload": {}}, headers=headers
    )
    assert conflict.status_code == 409


def test_tenant_isolation():
    headers = {"X-Tenant-Id": "tenant-a", "Idempotency-Key": "tenant-a-22"}
    created = client.post("/events", json=DATA, headers=headers)
    event_id = created.json()["id"]
    assert client.get(f"/events/{event_id}", headers={"X-Tenant-Id": "tenant-a"}).status_code == 200
    assert client.get(f"/events/{event_id}", headers={"X-Tenant-Id": "tenant-b"}).status_code == 404
