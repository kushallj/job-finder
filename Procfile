api:    uvicorn main:app --host 0.0.0.0 --port 8000 --log-level info
worker: celery -A src.tasks worker --loglevel=info --concurrency=4 --queues=celery
beat:   celery -A src.tasks beat   --loglevel=info --scheduler celery.beat.PersistentScheduler
flower: celery -A src.tasks flower --port=5555
