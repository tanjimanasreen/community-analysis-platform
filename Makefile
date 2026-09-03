.PHONY: help bootstrap install install-dev test test-unit test-integration format lint mlflow-ui \
	db-up db-down db-check tei-up tei-down tei-check validate-config ingest-sample run-network-sample \
	run-topic-sample run-theme-sample evaluate-sample run-pipeline-test \
	run-pipeline-sample run-dashboard-sample run-longitudinal-sample \
	run-evolution-pipeline-test pipeline-preflight translation-preflight translation-detect cd-preflight canonical-theme-benchmark monthly-theme-cluster-benchmark run-evolution-pipeline verify-output-contract \
	verify-evolution-output-contract verify-longitudinal-output-contract api-smoke-test run-api demo demo-api \
	demo-frontend frontend-install frontend-build frontend-lint frontend-typecheck \
	frontend-test frontend-coverage frontend-e2e frontend-check dashboard-fixture \
	run-frontend clean-generated clean-cache build-report benchmark-performance \
	infra-install infra-test infra-synth infra-list \
	infra-diff-api infra-deploy-api \
	api-image-build api-image-smoke \
	tei-image-build tei-image-smoke tei-compat-smoke

PYTHON ?= .venv/bin/python
UV ?= uv
SAMPLE_CONFIG ?= tests/configs/test_single_month.yml
SAMPLE_OUTPUT ?= local_output/tests/community-analysis-sample
SAMPLE_THEME_OUTPUT ?= local_output/tests/community-analysis-theme-sample
SAMPLE_INTERACTIONS ?= local_output/tests/community-analysis-sample-interactions.parquet
SAMPLE_REPORT ?= local_output/tests/community-analysis-artifact-index.md
CANONICAL_BENCHMARK_OUT ?= local_output/benchmarks/canonical-theme
MONTHLY_CLUSTER_BENCHMARK_OUT ?= local_output/benchmarks/monthly-theme-clustering

TEST_EVOLUTION_CONFIG ?= tests/configs/test_evolution.yml
export EVOLUTION_OUTPUT ?= local_output/tests/community-analysis-evolution-test
export EVOLUTION_REPORT ?= local_output/tests/community-analysis-evolution-artifact-index.md
# Optional provider override for non-sample evolution runs. It is separate
# from THEME_PROVIDER, which remains pinned to mock for sample targets.
EVOLUTION_THEME_PROVIDER ?=

export DASHBOARD_FIXTURE_ROOT ?= local_output/tests/community-dashboard-fixture
export API_ARTIFACT_ROOT ?= $(SAMPLE_OUTPUT)

# Keep all sample/demo theme generation deterministic and offline.
# A command-line override remains possible, e.g. `make run-theme-sample THEME_PROVIDER=mock`.
THEME_PROVIDER := mock

help:
	@echo "Available targets:"
	@echo "  bootstrap            - Synchronize the locked development/orchestration environment"
	@echo "  install              - Create .venv and install runtime dependencies"
	@echo "  install-dev          - Create .venv and install runtime + dev dependencies"
	@echo "  test                 - Run the full test suite"
	@echo "  mlflow-ui            - Start the local MLflow UI on 127.0.0.1:5001"
	@echo "  format               - Format code with black"
	@echo "  lint                 - Lint code with flake8"
	@echo "  db-up                - Start local Memgraph instance"
	@echo "  db-check             - Check database connectivity"
	@echo "  validate-config      - Validate the offline sample configuration"
	@echo "  ingest-sample        - Build derived sample interactions without a database"
	@echo "  run-network-sample   - Run network/community sample stages offline"
	@echo "  run-topic-sample     - Run topic sample stages from saved network outputs"
	@echo "  run-theme-sample     - Run theme sample from saved topic outputs using the offline mock provider"
	@echo "  evaluate-sample      - Run the offline DeepEval + MLflow benchmark pipeline"
	@echo "  run-pipeline-test    - Run the legacy stage-by-stage offline test pipeline"
	@echo "  run-dashboard-sample - Publish a canonical manifest-backed sample run"
	@echo "  run-evolution-pipeline-test - Run two-month offline evolution pipeline and transitions"
	@echo "  pipeline-preflight   - Fail fast on dependencies, inputs, credentials, and required TEI profiles"
	@echo "  translation-preflight - Prepare/reuse network outputs and report cached translation workload without cloud translation calls"
	@echo "  translation-detect   - Call language detection only, cache results, and report exact translation request workload"
	@echo "  cd-preflight         - Validate local CD environment, infra venv, Python imports, and workflow contracts without AWS access or deployment"
	@echo "  canonical-theme-benchmark - Benchmark Stage-B canonicalization from saved theme artifacts without changing production outputs"
	@echo "  monthly-theme-cluster-benchmark - Benchmark Stage-A monthly HDBSCAN from saved clean theme artifacts without changing production outputs"
	@echo "  run-evolution-pipeline - Run a real evolution pipeline after preflight (CONFIG=...)"
	@echo "  verify-output-contract - Validate generated one-month test artifact schemas"
	@echo "  verify-evolution-output-contract - Validate generated evolution artifact schemas"
	@echo "  api-smoke-test       - Run read-only dashboard API smoke tests"
	@echo "  run-api              - Start the read-only artifact API"
	@echo "  demo                 - Run offline test, verifiers, report, and API smoke tests"
	@echo "  demo-api             - Start the read-only artifact API for demo outputs"
	@echo "  demo-frontend        - Start the read-only dashboard dev server"
	@echo "  frontend-install     - Install frontend dependencies"
	@echo "  frontend-build       - Build the read-only dashboard"
	@echo "  frontend-lint        - Lint the read-only dashboard"
	@echo "  frontend-typecheck   - Type-check frontend TypeScript boundaries"
	@echo "  frontend-test        - Run frontend unit/component tests"
	@echo "  frontend-coverage    - Run focused frontend coverage gate"
	@echo "  frontend-e2e         - Run Chromium Playwright workflows against the canonical fixture"
	@echo "  dashboard-fixture    - Build deterministic canonical dashboard artifacts"
	@echo "  frontend-check       - Run typecheck, lint, coverage, build, and bundle budget"
	@echo "  run-frontend         - Start the dashboard dev server"
	@echo "  clean-generated      - Remove known demo outputs and frontend build output"
	@echo "  clean-cache          - Remove Python/test/Vite caches and egg-info"
	@echo "  build-report         - Build a markdown artifact index for sample outputs"
	@echo "  benchmark-performance - Compare legacy and indexed message aggregation"
	@echo "  infra-install        - Create infra/.venv and install CDK dependencies"
	@echo "  infra-test           - Run pytest on CDK infrastructure tests"
	@echo "  infra-synth          - Synthesize CDK CloudFormation templates (STAGE=dev|prod, IMAGE_TAG=...)"
	@echo "  infra-list           - List CDK stacks (STAGE=dev|prod, IMAGE_TAG=...)"
	@echo "  infra-diff-api       - Diff CDK ApiStack (STAGE=dev|prod, IMAGE_TAG=...)"
	@echo "  infra-deploy-api     - Deploy CDK ApiStack (STAGE=dev|prod, IMAGE_TAG=...)"
	@echo "  api-image-build      - Build API Docker container image for linux/arm64"
	@echo "  api-image-smoke      - Build and run local smoke test on API container"
	@echo "  tei-image-build      - Build TEI Docker container image for linux/arm64"
	@echo "  tei-image-smoke      - Run local CLI smoke test on TEI container"
	@echo "  tei-compat-smoke     - Run local dual-container TEI compatibility smoke test"

bootstrap:
	$(UV) sync --frozen --extra orchestration

install:
	$(UV) sync --frozen --no-dev

install-dev:
	$(UV) sync --frozen --extra orchestration --extra tracking

test-unit:
	uv run --frozen --extra orchestration --extra tracking python -m pytest tests/unit

test-integration:
	uv run --frozen --extra orchestration --extra tracking python -m pytest tests/integration

test:
	uv run --frozen --extra orchestration --extra tracking python -m pytest tests

mlflow-ui:
	@mkdir -p .mlflow/artifacts
	uvx --from mlflow==3.14.0 mlflow ui \
		--host 127.0.0.1 \
		--port 5001 \
		--backend-store-uri "sqlite:///$$(pwd)/.mlflow/mlflow.db" \
		--default-artifact-root "file://$$(pwd)/.mlflow/artifacts"

db-up:
	docker compose up -d memgraph

db-down:
	docker compose down

tei-up:
	bash scripts/start_tei.sh

tei-down:
	bash scripts/stop_tei.sh

tei-check:
	$(UV) run --frozen --extra orchestration python scripts/check_tei.py

db-check:
	$(PYTHON) -m src.cli db-check --config $(SAMPLE_CONFIG)

format:
	$(PYTHON) -m black src/ tests/

lint:
	uv run pre-commit run --all-files --show-diff-on-failure

validate-config:
	$(PYTHON) -m src.cli validate-config --config $(SAMPLE_CONFIG)

ingest-sample:
	$(PYTHON) -m src.cli ingest-interactions --file tests/fixtures/sample_relationships.csv --config $(SAMPLE_CONFIG) --out $(SAMPLE_INTERACTIONS) --no-db

run-network-sample:
	MPLBACKEND=Agg MPLCONFIGDIR=/tmp $(PYTHON) -m src.cli run-social-network --config $(SAMPLE_CONFIG)

run-topic-sample:
	MPLBACKEND=Agg MPLCONFIGDIR=/tmp $(PYTHON) -m src.cli run-topics --config $(SAMPLE_CONFIG)

run-theme-sample:
	MPLBACKEND=Agg MPLCONFIGDIR=/tmp $(PYTHON) -m src.cli run-theme-analysis --config $(SAMPLE_CONFIG) --theme-provider $(THEME_PROVIDER)

evaluate-sample:
	@echo "Running DeepEval sample evaluation..."
	$(PYTHON) -m src.cli theme-benchmark build-dataset --config $(SAMPLE_CONFIG) --run-id offline-smoke --limit 10
	$(PYTHON) -m src.cli theme-benchmark run --config $(SAMPLE_CONFIG) --run-id offline-smoke --providers keyword_baseline,mock
	$(PYTHON) -m src.cli theme-benchmark export-review --config $(SAMPLE_CONFIG) --run-id offline-smoke
	$(PYTHON) -m src.cli theme-benchmark evaluate-deepeval --config $(SAMPLE_CONFIG) --run-id offline-smoke
run-pipeline-test: ingest-sample run-network-sample run-topic-sample run-theme-sample build-report

# Backward-compatible names documented in HARNESS.md and AGENTS.md.
run-pipeline-sample: run-pipeline-test

run-dashboard-sample:
	MPLBACKEND=Agg MPLCONFIGDIR=/tmp $(PYTHON) -m src.cli run-all --config $(SAMPLE_CONFIG) --theme-provider $(THEME_PROVIDER)

run-longitudinal-sample: run-evolution-pipeline-test

run-evolution-pipeline-test:
	@mkdir -p $(EVOLUTION_OUTPUT)
	@mkdir -p /tmp/prefect
	$(PYTHON) -m src.cli ingest-interactions --file tests/fixtures/longitudinal/twitter_reply_03_2017.csv --config $(TEST_EVOLUTION_CONFIG) --dataset-id 03 --out $(EVOLUTION_OUTPUT)/interactions_03.parquet --no-db
	$(PYTHON) -m src.cli ingest-interactions --file tests/fixtures/longitudinal/twitter_reply_04_2017.csv --config $(TEST_EVOLUTION_CONFIG) --dataset-id 04 --out $(EVOLUTION_OUTPUT)/interactions_04.parquet --no-db
	PREFECT_HOME=/tmp/prefect PREFECT_API_DATABASE_CONNECTION_URL="sqlite+aiosqlite:////tmp/prefect/prefect.db" MPLBACKEND=Agg MPLCONFIGDIR=/tmp $(PYTHON) -m src.cli run-evolution-pipeline --config $(TEST_EVOLUTION_CONFIG) --theme-provider $(THEME_PROVIDER)
	$(PYTHON) -m src.cli build-report --config $(TEST_EVOLUTION_CONFIG) --out $(EVOLUTION_REPORT)

verify-output-contract:
	$(PYTHON) -m src.cli verify-output-contract --config $(SAMPLE_CONFIG)

verify-evolution-output-contract:
	$(PYTHON) -m src.cli verify-output-contract --config $(TEST_EVOLUTION_CONFIG) --longitudinal

# Backward-compatible name retained for pre-evolution scripts and notes.
verify-longitudinal-output-contract: verify-evolution-output-contract

pipeline-preflight:
	@if [ -z "$(CONFIG)" ]; then \
		echo "Error: CONFIG is not set. Usage: make pipeline-preflight CONFIG=configs/twitter/reply_evolution.yml"; \
		exit 1; \
	fi
	$(UV) run --frozen --extra orchestration python -m src.cli pipeline-preflight --config $(CONFIG) $(if $(EVOLUTION_THEME_PROVIDER),--theme-provider $(EVOLUTION_THEME_PROVIDER))

translation-preflight:
	@if [ -z "$(CONFIG)" ]; then \
		echo "Error: CONFIG is not set. Usage: make translation-preflight CONFIG=configs/telegram/forwarded_message_evolution.yml"; \
		exit 1; \
	fi
	@mkdir -p /tmp/prefect
	PREFECT_HOME=/tmp/prefect PREFECT_API_DATABASE_CONNECTION_URL="sqlite+aiosqlite:////tmp/prefect/prefect.db" MPLBACKEND=Agg MPLCONFIGDIR=/tmp $(UV) run --frozen --extra orchestration python -m src.cli translation-preflight --config $(CONFIG) $(if $(DATASET_ID),--dataset-id $(DATASET_ID))

translation-detect:
	@if [ -z "$(CONFIG)" ]; then \
		echo "Error: CONFIG is not set. Usage: make translation-detect CONFIG=configs/telegram/forwarded_message_evolution.yml"; \
		exit 1; \
	fi
	@mkdir -p /tmp/prefect
	PREFECT_HOME=/tmp/prefect PREFECT_API_DATABASE_CONNECTION_URL="sqlite+aiosqlite:////tmp/prefect/prefect.db" MPLBACKEND=Agg MPLCONFIGDIR=/tmp $(UV) run --frozen --extra orchestration python -m src.cli translation-detect --config $(CONFIG) $(if $(DATASET_ID),--dataset-id $(DATASET_ID))

cd-preflight:
	@echo "=== CD Preflight: 1. Verifying/provisioning infra environment ==="
	@if [ ! -x infra/.venv/bin/python ]; then \
		echo "Provisioning infra/.venv using uv..."; \
		$(UV) venv infra/.venv --python 3.11 && $(UV) pip install --python infra/.venv/bin/python -r infra/requirements.txt; \
	fi
	@infra/.venv/bin/python -c "import aws_cdk; print('  [OK] infra/.venv imports aws_cdk')"
	@echo "=== CD Preflight: 2. Verifying repository root CD module imports ==="
	@$(UV) run --frozen python -c "import scripts.aws_cd; import scripts.aws_run_evolution; print('  [OK] root environment imports scripts.aws_cd and scripts.aws_run_evolution')"
	@echo "=== CD Preflight: 3. Verifying CD workflow contracts and unit tests ==="
	@$(UV) run --frozen --extra orchestration --extra tracking python -m pytest tests/unit/test_workflow_contracts.py tests/unit/test_aws_cd.py -v --tb=short
	@echo "=== CD Preflight: PASS ==="

canonical-theme-benchmark:
	@if [ -z "$(THEMES_DIR)" ]; then \
		echo "Error: THEMES_DIR is not set. Usage: make canonical-theme-benchmark THEMES_DIR=<.../data/themes|.../theme_clusters>"; \
		exit 1; \
	fi
	$(PYTHON) -m src.cli canonical-theme-benchmark --themes-dir $(THEMES_DIR) --out-dir $(CANONICAL_BENCHMARK_OUT)

monthly-theme-cluster-benchmark:
	@if [ -z "$(THEMES_DIR)" ]; then \
		echo "Error: THEMES_DIR is not set. Usage: make monthly-theme-cluster-benchmark THEMES_DIR=<.../data/themes|.../theme_clusters>"; \
		exit 1; \
	fi
	$(PYTHON) -m src.cli monthly-theme-cluster-benchmark --themes-dir $(THEMES_DIR) --out-dir $(MONTHLY_CLUSTER_BENCHMARK_OUT)

run-evolution-pipeline: pipeline-preflight
	@mkdir -p /tmp/prefect
	PREFECT_HOME=/tmp/prefect PREFECT_API_DATABASE_CONNECTION_URL="sqlite+aiosqlite:////tmp/prefect/prefect.db" MPLBACKEND=Agg MPLCONFIGDIR=/tmp $(UV) run --frozen --extra orchestration python -m src.cli run-evolution-pipeline --config $(CONFIG) $(if $(EVOLUTION_THEME_PROVIDER),--theme-provider $(EVOLUTION_THEME_PROVIDER))

api-smoke-test:
	uv run --frozen --extra orchestration --extra tracking python -m pytest tests/unit/test_backend_api.py

API_HOST ?= 127.0.0.1
API_PORT ?= 8000

run-api:
	COMMUNITY_ANALYSIS_ARTIFACT_ROOT=$(API_ARTIFACT_ROOT) uv run --frozen --extra orchestration --extra tracking python -m uvicorn src.api.app:app --host $(API_HOST) --port $(API_PORT)

demo: run-pipeline-test verify-output-contract run-evolution-pipeline-test verify-evolution-output-contract build-report api-smoke-test

demo-api: run-api

demo-frontend: run-frontend

frontend-install:
	cd frontend && if [ -f package-lock.json ]; then npm ci; else npm install; fi

frontend-build:
	cd frontend && npm run build

frontend-lint:
	cd frontend && npm run lint

frontend-typecheck:
	cd frontend && npm run typecheck

frontend-test:
	cd frontend && npm run test -- --run

frontend-coverage:
	cd frontend && npm run test:coverage

frontend-e2e: dashboard-fixture
	cd frontend && DASHBOARD_PYTHON=$(abspath $(PYTHON)) DASHBOARD_FIXTURE_ROOT=$(DASHBOARD_FIXTURE_ROOT) npm run test:e2e

dashboard-fixture:
	$(PYTHON) scripts/build_dashboard_fixture.py --out $(DASHBOARD_FIXTURE_ROOT)

frontend-check:
	cd frontend && npm run check

run-frontend:
	cd frontend && npm run dev

clean-generated:
	rm -rf "$(SAMPLE_OUTPUT)" "$(SAMPLE_THEME_OUTPUT)" "$(SAMPLE_INTERACTIONS)" "$(SAMPLE_REPORT)" "$(EVOLUTION_OUTPUT)" "$(EVOLUTION_REPORT)" "$(DASHBOARD_FIXTURE_ROOT)" frontend/dist frontend/playwright-report frontend/test-results frontend/coverage

clean-cache:
	find . -path ./.venv -prune -o -path ./frontend/node_modules -prune -o -type d -name "__pycache__" -prune -exec rm -rf {} +
	rm -rf .pytest_cache .mypy_cache .ruff_cache frontend/.vite frontend/playwright-report frontend/test-results frontend/coverage
	find . -path ./.venv -prune -o -path ./frontend/node_modules -prune -o -type d -name "*.egg-info" -prune -exec rm -rf {} +

build-report:
	$(PYTHON) -m src.cli build-report --config $(SAMPLE_CONFIG) --out $(SAMPLE_REPORT)

benchmark-performance:
	$(PYTHON) -m scripts.benchmark_community_messages

INFRA_STAGE ?= dev

infra-install:
	python3.11 -m venv infra/.venv
	infra/.venv/bin/pip install --upgrade pip
	infra/.venv/bin/pip install -r infra/requirements-dev.txt

infra-test:
	PYTHONPATH=infra infra/.venv/bin/pytest infra/tests

infra-synth:
ifndef IMAGE_TAG
	$(error IMAGE_TAG is required (e.g. make infra-synth INFRA_STAGE=$(INFRA_STAGE) IMAGE_TAG=<GIT_SHA> [BATCH_IMAGE_TAG=<BATCH_TAG>] [TEI_ANALYTICS_IMAGE_TAG=<ANALYTICS_TAG>] [TEI_IMAGE_TAG=<TEI_TAG>]))
endif
	cd infra && cdk synth -c stage=$(INFRA_STAGE) -c image_tag=$(IMAGE_TAG) $(if $(BATCH_IMAGE_TAG),-c batch_image_tag=$(BATCH_IMAGE_TAG)) $(if $(TEI_ANALYTICS_IMAGE_TAG),-c tei_analytics_image_tag=$(TEI_ANALYTICS_IMAGE_TAG)) $(if $(TEI_IMAGE_TAG),-c tei_image_tag=$(TEI_IMAGE_TAG))

infra-list:
ifndef IMAGE_TAG
	$(error IMAGE_TAG is required (e.g. make infra-list INFRA_STAGE=$(INFRA_STAGE) IMAGE_TAG=<GIT_SHA> [BATCH_IMAGE_TAG=<BATCH_TAG>] [TEI_ANALYTICS_IMAGE_TAG=<ANALYTICS_TAG>] [TEI_IMAGE_TAG=<TEI_TAG>]))
endif
	cd infra && cdk list -c stage=$(INFRA_STAGE) -c image_tag=$(IMAGE_TAG) $(if $(BATCH_IMAGE_TAG),-c batch_image_tag=$(BATCH_IMAGE_TAG)) $(if $(TEI_ANALYTICS_IMAGE_TAG),-c tei_analytics_image_tag=$(TEI_ANALYTICS_IMAGE_TAG)) $(if $(TEI_IMAGE_TAG),-c tei_image_tag=$(TEI_IMAGE_TAG))

infra-diff-api:
ifndef IMAGE_TAG
	$(error IMAGE_TAG is required (e.g. make infra-diff-api INFRA_STAGE=$(INFRA_STAGE) IMAGE_TAG=<GIT_SHA>))
endif
	cd infra && cdk diff community-analysis-$(INFRA_STAGE)-api -c stage=$(INFRA_STAGE) -c image_tag=$(IMAGE_TAG)

infra-deploy-api:
ifndef IMAGE_TAG
	$(error IMAGE_TAG is required (e.g. make infra-deploy-api INFRA_STAGE=$(INFRA_STAGE) IMAGE_TAG=<GIT_SHA>))
endif
	cd infra && cdk deploy community-analysis-$(INFRA_STAGE)-api -c stage=$(INFRA_STAGE) -c image_tag=$(IMAGE_TAG) --require-approval never

infra-diff-frontend:
ifndef IMAGE_TAG
	$(error IMAGE_TAG is required (e.g. make infra-diff-frontend INFRA_STAGE=$(INFRA_STAGE) IMAGE_TAG=<GIT_SHA>))
endif
	cd infra && cdk diff community-analysis-$(INFRA_STAGE)-frontend -c stage=$(INFRA_STAGE) -c image_tag=$(IMAGE_TAG)

infra-deploy-frontend:
ifndef IMAGE_TAG
	$(error IMAGE_TAG is required (e.g. make infra-deploy-frontend INFRA_STAGE=$(INFRA_STAGE) IMAGE_TAG=<GIT_SHA>))
endif
	cd infra && cdk deploy community-analysis-$(INFRA_STAGE)-frontend -c stage=$(INFRA_STAGE) -c image_tag=$(IMAGE_TAG) --require-approval never

infra-diff-batch:
ifndef IMAGE_TAG
	$(error IMAGE_TAG is required (e.g. make infra-diff-batch INFRA_STAGE=$(INFRA_STAGE) IMAGE_TAG=<GIT_SHA> BATCH_IMAGE_TAG=<BATCH_TAG> TEI_ANALYTICS_IMAGE_TAG=<PLAN095_SHA> TEI_IMAGE_TAG=<PLAN095_SHA>))
endif
ifndef BATCH_IMAGE_TAG
	$(error BATCH_IMAGE_TAG is required (e.g. make infra-diff-batch INFRA_STAGE=$(INFRA_STAGE) IMAGE_TAG=<GIT_SHA> BATCH_IMAGE_TAG=<BATCH_TAG> TEI_ANALYTICS_IMAGE_TAG=<PLAN095_SHA> TEI_IMAGE_TAG=<PLAN095_SHA>))
endif
ifndef TEI_ANALYTICS_IMAGE_TAG
	$(error TEI_ANALYTICS_IMAGE_TAG is required (e.g. make infra-diff-batch INFRA_STAGE=$(INFRA_STAGE) IMAGE_TAG=<GIT_SHA> BATCH_IMAGE_TAG=<BATCH_TAG> TEI_ANALYTICS_IMAGE_TAG=<PLAN095_SHA> TEI_IMAGE_TAG=<PLAN095_SHA>))
endif
ifndef TEI_IMAGE_TAG
	$(error TEI_IMAGE_TAG is required (e.g. make infra-diff-batch INFRA_STAGE=$(INFRA_STAGE) IMAGE_TAG=<GIT_SHA> BATCH_IMAGE_TAG=<BATCH_TAG> TEI_ANALYTICS_IMAGE_TAG=<PLAN095_SHA> TEI_IMAGE_TAG=<PLAN095_SHA>))
endif
	cd infra && cdk diff community-analysis-$(INFRA_STAGE)-batch -c stage=$(INFRA_STAGE) -c image_tag=$(IMAGE_TAG) -c batch_image_tag=$(BATCH_IMAGE_TAG) -c tei_analytics_image_tag=$(TEI_ANALYTICS_IMAGE_TAG) -c tei_image_tag=$(TEI_IMAGE_TAG)

infra-deploy-batch:
ifndef IMAGE_TAG
	$(error IMAGE_TAG is required (e.g. make infra-deploy-batch INFRA_STAGE=$(INFRA_STAGE) IMAGE_TAG=<GIT_SHA> BATCH_IMAGE_TAG=<BATCH_TAG> TEI_ANALYTICS_IMAGE_TAG=<PLAN095_SHA> TEI_IMAGE_TAG=<PLAN095_SHA>))
endif
ifndef BATCH_IMAGE_TAG
	$(error BATCH_IMAGE_TAG is required (e.g. make infra-deploy-batch INFRA_STAGE=$(INFRA_STAGE) IMAGE_TAG=<GIT_SHA> BATCH_IMAGE_TAG=<BATCH_TAG> TEI_ANALYTICS_IMAGE_TAG=<PLAN095_SHA> TEI_IMAGE_TAG=<PLAN095_SHA>))
endif
ifndef TEI_ANALYTICS_IMAGE_TAG
	$(error TEI_ANALYTICS_IMAGE_TAG is required (e.g. make infra-deploy-batch INFRA_STAGE=$(INFRA_STAGE) IMAGE_TAG=<GIT_SHA> BATCH_IMAGE_TAG=<BATCH_TAG> TEI_ANALYTICS_IMAGE_TAG=<PLAN095_SHA> TEI_IMAGE_TAG=<PLAN095_SHA>))
endif
ifndef TEI_IMAGE_TAG
	$(error TEI_IMAGE_TAG is required (e.g. make infra-deploy-batch INFRA_STAGE=$(INFRA_STAGE) IMAGE_TAG=<GIT_SHA> BATCH_IMAGE_TAG=<BATCH_TAG> TEI_ANALYTICS_IMAGE_TAG=<PLAN095_SHA> TEI_IMAGE_TAG=<PLAN095_SHA>))
endif
	cd infra && cdk deploy community-analysis-$(INFRA_STAGE)-batch -c stage=$(INFRA_STAGE) -c image_tag=$(IMAGE_TAG) -c batch_image_tag=$(BATCH_IMAGE_TAG) -c tei_analytics_image_tag=$(TEI_ANALYTICS_IMAGE_TAG) -c tei_image_tag=$(TEI_IMAGE_TAG) --require-approval never

API_LOCAL_IMAGE ?= community-analysis-api:dev
API_IMAGE_TAG ?= $(API_LOCAL_IMAGE)
API_IMAGE_PLATFORM ?= linux/arm64

api-image-build:
	docker build --platform $(API_IMAGE_PLATFORM) -t $(API_LOCAL_IMAGE) -f Dockerfile.api .

api-image-smoke: api-image-build
	@echo "Running local container smoke tests on $(API_LOCAL_IMAGE)..."
	@CONTAINER_ID=$$(docker run -d -p 8000:8000 $(API_LOCAL_IMAGE)) && \
	trap 'docker stop $$CONTAINER_ID >/dev/null 2>&1 && docker rm $$CONTAINER_ID >/dev/null 2>&1' EXIT && \
	sleep 3 && \
	curl -fs http://127.0.0.1:8000/api/v1/health >/dev/null && \
	curl -fs http://127.0.0.1:8000/api/v1/ready >/dev/null && \
	echo "Container smoke test passed."

ANALYTICS_LOCAL_IMAGE ?= community-analysis-analytics:dev
ANALYTICS_IMAGE_PLATFORM ?= linux/arm64

analytics-image-build:
	docker build --platform $(ANALYTICS_IMAGE_PLATFORM) -t $(ANALYTICS_LOCAL_IMAGE) -f Dockerfile.analytics .

analytics-image-smoke: analytics-image-build
	@echo "Running local container smoke tests on $(ANALYTICS_LOCAL_IMAGE)..."
	docker run --rm $(ANALYTICS_LOCAL_IMAGE) --help >/dev/null && echo "Container --help smoke passed."
	docker run --rm $(ANALYTICS_LOCAL_IMAGE) --dry-run --config tests/configs/test_evolution.yml && echo "Container config validation smoke passed."
	@echo "Analytics container smoke tests passed."

analytics-image-sample: analytics-image-build
	@echo "Running real deterministic analytical sample inside $(ANALYTICS_LOCAL_IMAGE)..."
	docker run --rm -e THEME_PROVIDER=mock $(ANALYTICS_LOCAL_IMAGE) --config tests/configs/test_evolution.yml --skip-s3-download --skip-s3-upload
	@echo "Analytics container real sample execution passed."

TEI_LOCAL_IMAGE ?= community-analysis-tei:dev
TEI_IMAGE_PLATFORM ?= linux/arm64

tei-image-build:
	docker build --platform $(TEI_IMAGE_PLATFORM) -t $(TEI_LOCAL_IMAGE) -f Dockerfile.tei .

tei-image-smoke: tei-image-build
	@echo "Running local container smoke tests on $(TEI_LOCAL_IMAGE)..."
	docker run --rm $(TEI_LOCAL_IMAGE) --help >/dev/null && echo "TEI container --help smoke passed."
	@echo "TEI container smoke tests passed."

tei-compat-smoke: tei-image-build
	@echo "Running real local TEI compatibility smoke against $(TEI_LOCAL_IMAGE)..."
	uv run python scripts/check_tei_compat.py --image $(TEI_LOCAL_IMAGE)

submit-batch-run:
ifeq ($(filter command line environment%,$(origin INFRA_STAGE)),)
	$(error INFRA_STAGE is required (e.g. make submit-batch-run INFRA_STAGE=dev CONFIG=tests/configs/test_evolution.yml THEME_PROVIDER=mock))
endif
ifndef CONFIG
	$(error CONFIG is required (e.g. make submit-batch-run INFRA_STAGE=$(INFRA_STAGE) CONFIG=tests/configs/test_evolution.yml THEME_PROVIDER=mock))
endif
ifeq ($(filter command line environment%,$(origin THEME_PROVIDER)),)
	$(error THEME_PROVIDER is required (e.g. make submit-batch-run INFRA_STAGE=$(INFRA_STAGE) CONFIG=$(CONFIG) THEME_PROVIDER=mock))
endif
	@echo "Submitting AWS Batch job for $(CONFIG) on stage $(INFRA_STAGE)..."
	aws batch submit-job \
		--job-name "community-analysis-$(INFRA_STAGE)-$$(date +%Y%m%d%H%M%S)" \
		--job-queue "community-analysis-$(INFRA_STAGE)-queue" \
		--job-definition "community-analysis-$(INFRA_STAGE)-analytics-job" \
		--container-overrides '{"environment": [{"name": "CONFIG_PATH", "value": "$(CONFIG)"}, {"name": "THEME_PROVIDER", "value": "$(THEME_PROVIDER)"}]}'
