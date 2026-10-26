from celery import Celery
from app.core.config import settings
celery = Celery("meditrack", broker=settings.redis_url, backend=settings.redis_url)
celery.conf.update(task_serializer="json", result_serializer="json", accept_content=["json"], timezone="UTC", enable_utc=True,
                   task_acks_late=True, worker_prefetch_multiplier=1, task_reject_on_worker_lost=True)
celery.conf.beat_schedule = {"dispatch-due-routine-reminders-every-minute": {"task": "app.workers.tasks.dispatch_due_reminders", "schedule": 60.0}}
celery.autodiscover_tasks(["app.workers"])
