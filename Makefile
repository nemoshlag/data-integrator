.PHONY: setup test clean deploy lint format help dev start-local stop-local logs test-deployment

VENV = venv
PYTHON = $(VENV)/bin/python
PIP = $(VENV)/bin/pip
STAGE ?= dev

help:
	@echo "Available commands:"
	@echo "  make setup            - Create virtual environment and install dependencies"
	@echo "  make dev             - Start local development environment"
	@echo "  make test            - Run all tests"
	@echo "  make lint            - Run code quality checks"
	@echo "  make format          - Format code"
	@echo "  make deploy          - Deploy to AWS (specify STAGE=prod for production)"
	@echo "  make clean           - Remove virtual environment and build artifacts"
	@echo "  make test-deployment - Run deployment tests"
	@echo "  make start-local     - Start local DynamoDB"
	@echo "  make stop-local      - Stop local DynamoDB"
	@echo "  make logs            - View Lambda function logs"

setup:
	chmod +x scripts/*.sh scripts/*.py
	./scripts/setup_dev.sh

dev: start-local
	serverless offline start

test:
	$(PYTHON) -m pytest tests/unit/ -v
	$(PYTHON) -m pytest tests/integration/ -v

test-unit:
	$(PYTHON) -m pytest tests/unit/ -v

test-integration:
	$(PYTHON) -m pytest tests/integration/ -v

test-deployment:
	./scripts/test_deployment.sh

lint:
	$(PYTHON) -m black . --check
	$(PYTHON) -m isort . --check-only
	$(PYTHON) -m flake8 .
	$(PYTHON) -m mypy src/

format:
	$(PYTHON) -m black .
	$(PYTHON) -m isort .

start-local:
	docker run -d -p 8000:8000 amazon/dynamodb-local || true
	@echo "DynamoDB running at http://localhost:8000"

stop-local:
	docker stop $$(docker ps -q --filter ancestor=amazon/dynamodb-local) || true

logs:
	@if [ -z "$(FUNCTION)" ]; then \
		echo "Please specify a function name: make logs FUNCTION=functionName"; \
	else \
		serverless logs -f $(FUNCTION) -t --stage $(STAGE); \
	fi

deploy:
	serverless deploy --stage $(STAGE)

deploy-function:
	@if [ -z "$(FUNCTION)" ]; then \
		echo "Please specify a function name: make deploy-function FUNCTION=functionName"; \
	else \
		serverless deploy function -f $(FUNCTION) --stage $(STAGE); \
	fi

clean:
	rm -rf $(VENV)
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov
	rm -rf .mypy_cache
	rm -rf .serverless
	rm -rf **/__pycache__
	rm -rf **/*.pyc
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	docker stop $$(docker ps -q --filter ancestor=amazon/dynamodb-local) || true

# CI/CD targets
ci-test: setup lint test

cd-deploy: validate deploy test-deployment

validate:
	serverless print
	serverless package --noDeploy

# Development environment setup
dev-environment: setup start-local
	@echo "Development environment setup complete"
	@echo "Run 'source venv/bin/activate' to activate virtual environment"

# Watch DynamoDB logs
watch-dynamodb:
	docker logs -f $$(docker ps -q --filter ancestor=amazon/dynamodb-local)

# Initialize local tables for development
init-local-tables: start-local
	@echo "Creating local tables..."
	$(PYTHON) scripts/init_local_tables.py

# Run end-to-end tests
e2e: test-deployment
	@echo "End-to-end tests complete"