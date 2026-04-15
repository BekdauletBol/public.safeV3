.PHONY: setup backend frontend workers db-migrate admin

setup:
	bash scripts/setup.sh

backend:
	cd backend && source venv/bin/activate && uvicorn main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npm run dev

workers:
	cd backend && source venv/bin/activate && celery -A app.workers.celery_app worker --loglevel=info

db-schema:
	psql -U postgres -d publicsafe -f database/schema.sql

db-migrate:
	cd backend && source venv/bin/activate && alembic upgrade head

admin:
	curl -s -X POST http://localhost:8000/api/v1/auth/create-admin \
		-H "Content-Type: application/json" \
		-d '{"username":"admin","email":"admin@example.com","password":"admin123"}' | python3 -m json.tool

test:
	cd backend && source venv/bin/activate && pytest -v
