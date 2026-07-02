.PHONY: help test format lint db-up db-down db-check validate-config ingest-sample run-network-sample run-topic-sample run-theme-sample run-pipeline-sample run-longitudinal-sample verify-output-contract verify-longitudinal-output-contract api-smoke-test run-api frontend-install frontend-build frontend-lint run-frontend build-report

PYTHON ?= .venv/bin/python
SAMPLE_CONFIG ?= configs/sample_twitter_reply.yml
SAMPLE_INTERACTIONS ?= /tmp/community-analysis-sample-interactions.csv
SAMPLE_REPORT ?= /tmp/community-analysis-artifact-index.md
LONGITUDINAL_CONFIG_03 ?= configs/longitudinal/sample_twitter_reply_03.yml
LONGITUDINAL_CONFIG_04 ?= configs/longitudinal/sample_twitter_reply_04.yml
LONGITUDINAL_OUTPUT ?= /tmp/community-analysis-longitudinal-sample
LONGITUDINAL_REPORT ?= /tmp/community-analysis-longitudinal-artifact-index.md

help:
	@echo "Available targets:"
	@echo "  test                 - Run unit tests"
	@echo "  format               - Format code with black"
	@echo "  lint                 - Lint code with flake8"
	@echo "  db-up                - Start local Memgraph instance"
	@echo "  db-check             - Check database connectivity"
	@echo "  validate-config      - Validate the offline sample configuration"
	@echo "  ingest-sample        - Build derived sample interactions without a database"
	@echo "  run-network-sample   - Run network/community sample stages offline"
	@echo "  run-topic-sample     - Run topic sample stages from saved network outputs"
	@echo "  run-theme-sample     - Run theme sample from saved topic outputs"
	@echo "  run-pipeline-sample  - Run the offline sample pipeline and artifact index"
	@echo "  run-longitudinal-sample - Run two-month offline pipeline and transitions"
	@echo "  verify-output-contract - Validate generated one-month sample artifact schemas"
	@echo "  verify-longitudinal-output-contract - Validate generated longitudinal artifact schemas"
	@echo "  api-smoke-test       - Run read-only backend API smoke tests"
	@echo "  run-api              - Start the read-only artifact API"
	@echo "  frontend-install     - Install frontend dependencies"
	@echo "  frontend-build       - Build the read-only dashboard"
	@echo "  frontend-lint        - Lint the read-only dashboard"
	@echo "  run-frontend         - Start the dashboard dev server"
	@echo "  build-report         - Build a markdown artifact index for sample outputs"

test:
	$(PYTHON) -m pytest tests/unit

db-up:
	docker compose up -d memgraph

db-down:
	docker compose down

db-check:
	$(PYTHON) -m src.cli db-check --config $(SAMPLE_CONFIG)

format:
	$(PYTHON) -m black src/ tests/

lint:
	$(PYTHON) -m flake8 src/ tests/

validate-config:
	$(PYTHON) -m src.cli validate-config --config $(SAMPLE_CONFIG)

ingest-sample:
	$(PYTHON) -m src.cli ingest-interactions --file tests/fixtures/sample_relationships.csv --config $(SAMPLE_CONFIG) --out $(SAMPLE_INTERACTIONS) --no-db

run-network-sample:
	MPLBACKEND=Agg MPLCONFIGDIR=/tmp $(PYTHON) -m src.cli run-social-network --config $(SAMPLE_CONFIG)

run-topic-sample:
	MPLBACKEND=Agg MPLCONFIGDIR=/tmp $(PYTHON) -m src.cli run-topics --config $(SAMPLE_CONFIG)

run-theme-sample:
	MPLBACKEND=Agg MPLCONFIGDIR=/tmp $(PYTHON) -m src.cli run-theme-analysis --config $(SAMPLE_CONFIG)

run-pipeline-sample: ingest-sample run-network-sample run-topic-sample run-theme-sample build-report

run-longitudinal-sample:
	$(PYTHON) -m src.cli ingest-interactions --file tests/fixtures/longitudinal/twitter_reply_03_2017.csv --config $(LONGITUDINAL_CONFIG_03) --out $(LONGITUDINAL_OUTPUT)/interactions_03.csv --no-db
	MPLBACKEND=Agg MPLCONFIGDIR=/tmp $(PYTHON) -m src.cli run-social-network --config $(LONGITUDINAL_CONFIG_03)
	MPLBACKEND=Agg MPLCONFIGDIR=/tmp $(PYTHON) -m src.cli run-topics --config $(LONGITUDINAL_CONFIG_03)
	$(PYTHON) -m src.cli ingest-interactions --file tests/fixtures/longitudinal/twitter_reply_04_2017.csv --config $(LONGITUDINAL_CONFIG_04) --out $(LONGITUDINAL_OUTPUT)/interactions_04.csv --no-db
	MPLBACKEND=Agg MPLCONFIGDIR=/tmp $(PYTHON) -m src.cli run-social-network --config $(LONGITUDINAL_CONFIG_04)
	MPLBACKEND=Agg MPLCONFIGDIR=/tmp $(PYTHON) -m src.cli run-topics --config $(LONGITUDINAL_CONFIG_04)
	MPLBACKEND=Agg MPLCONFIGDIR=/tmp $(PYTHON) -m src.cli run-theme-analysis --config $(LONGITUDINAL_CONFIG_04)
	$(PYTHON) -m src.cli build-report --config $(LONGITUDINAL_CONFIG_04) --out $(LONGITUDINAL_REPORT)

verify-output-contract:
	$(PYTHON) -m src.cli verify-output-contract --config $(SAMPLE_CONFIG)

verify-longitudinal-output-contract:
	$(PYTHON) -m src.cli verify-output-contract --config $(LONGITUDINAL_CONFIG_04) --longitudinal

api-smoke-test:
	$(PYTHON) -m pytest tests/unit/test_backend_api.py

run-api:
	COMMUNITY_ANALYSIS_API_CONFIGS=$(SAMPLE_CONFIG),$(LONGITUDINAL_CONFIG_04) $(PYTHON) -m uvicorn backend.main:app --reload

frontend-install:
	cd frontend && if [ -f package-lock.json ]; then npm ci; else npm install; fi

frontend-build:
	cd frontend && npm run build

frontend-lint:
	cd frontend && npm run lint

run-frontend:
	cd frontend && npm run dev

build-report:
	$(PYTHON) -m src.cli build-report --config $(SAMPLE_CONFIG) --out $(SAMPLE_REPORT)
