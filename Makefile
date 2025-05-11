.PHONY: load-data

load-data:
	docker-compose exec backend python -c "from load_data import load_all_data; from db import SessionLocal; db = SessionLocal(); load_all_data(db)"

.PHONY: run
run:
	docker-compose up --build

.PHONY: stop
stop:
	docker-compose down

.PHONY: frontend
frontend:
	docker-compose -f docker-compose.frontend.yml up --build

.PHONY: backend
backend:
	docker-compose -f docker-compose.backend.yml up --build

.PHONY: db
db:
	docker-compose -f docker-compose.db.yml up --build
