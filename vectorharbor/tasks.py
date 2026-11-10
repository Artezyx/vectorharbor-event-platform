import os
from uuid import UUID
from celery import Celery
from .database import SessionLocal
from .service import process

celery_app = Celery('vectorharbor', broker=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'))
celery_app.conf.update(task_serializer='json', accept_content=['json'], task_acks_late=True,
                       worker_prefetch_multiplier=1, task_default_retry_delay=5)

@celery_app.task(name='vectorharbor.process_event', bind=True, autoretry_for=(OSError,), retry_backoff=True, max_retries=5)
def process_event(self, event_id: str) -> bool:
    with SessionLocal() as db:
        return process(db, UUID(event_id))
