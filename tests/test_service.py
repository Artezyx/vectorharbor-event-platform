from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
import pytest
from vectorharbor.database import Base
from vectorharbor.models import Event
from vectorharbor.schema import EventIn
from vectorharbor.service import ConflictError, fingerprint, process, store

@pytest.fixture
def db():
    engine = create_engine('sqlite+pysqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()

def payload(amount=100, tenant='acme'):
    return EventIn(tenant_id=tenant, event_type='invoice.paid', metadata={'amount': amount, 'currency': 'MXN'})

def test_canonical_hash_ignores_object_field_order():
    first = EventIn(tenant_id='acme', event_type='invoice.paid', metadata={'b': 2, 'a': 1})
    second = EventIn(tenant_id='acme', event_type='invoice.paid', metadata={'a': 1, 'b': 2})
    assert fingerprint(first) == fingerprint(second)

def test_idempotent_replay_does_not_duplicate_event(db):
    first, old = store(db, payload(), 'key-01')
    second, replay = store(db, payload(), 'key-01')
    assert old is False and replay is True and first.id == second.id
    assert len(db.scalars(select(Event)).all()) == 1

def test_same_key_changed_payload_conflicts(db):
    store(db, payload(100), 'key-01')
    with pytest.raises(ConflictError):
        store(db, payload(101), 'key-01')

def test_tenant_keys_are_isolated(db):
    a, _ = store(db, payload(100, 'acme'), 'key-01')
    b, _ = store(db, payload(100, 'nova'), 'key-01')
    assert a.id != b.id

def test_processing_is_once_only(db):
    event, _ = store(db, payload(), 'key-02')
    assert process(db, event.id) is True
    assert process(db, event.id) is False
    assert db.get(Event, event.id).status == 'processed'
