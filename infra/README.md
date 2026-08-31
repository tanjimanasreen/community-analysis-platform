# AWS CDK Infrastructure

This directory contains the AWS Cloud Development Kit (AWS CDK v2, Python) infrastructure code for the `community-analysis` platform.

## Architecture

AWS infrastructure code is strictly separated from the analytical backend (`src/`) and frontend (`frontend/`).

- **Multi-stage support**: Supports `dev` and `prod` stages without duplicating code.
- **Naming convention**: `<project>-<stage>-<component>` (e.g. `community-analysis-dev-storage`).
- **Standard tags**: Applied globally to all constructs:
  - `Project: community-analysis`
  - `Environment: dev | prod`
  - `ManagedBy: aws-cdk`

## Directory Structure

```text
infra/
├── app.py                     # CDK App entry point
├── cdk.json                   # CDK configuration and feature flags
├── requirements.txt           # Core CDK dependencies
├── requirements-dev.txt       # Development & testing dependencies (pytest)
├── .gitignore                 # CDK ignored files (.venv, cdk.out, caches)
├── community_analysis_infra/  # Constructs, stacks, and configuration
│   ├── __init__.py
│   ├── api_stack.py           # Authenticated Lambda & API Gateway stack
│   ├── baseline_stack.py      # Baseline infrastructure verification stack
│   ├── config.py              # Multi-stage configuration model
│   ├── frontend_stack.py      # S3 OAC, CloudFront SPA CDN & Cognito client
│   ├── registry_stack.py      # ECR API container registry stack
│   └── storage_stack.py       # S3 analytical data & artifact storage stack
└── tests/                     # Infrastructure unit tests
    ├── __init__.py
    ├── test_api_stack.py
    ├── test_app.py
    ├── test_config.py
    ├── test_frontend_stack.py
    ├── test_registry_stack.py
    └── test_storage_stack.py
```

## Quickstart

### 1. Set Up Virtual Environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

### 2. Run Tests

```bash
pytest tests
```

### 3. Synthesize CloudFormation Templates

```bash
cdk synth -c stage=dev
```

### 4. List Stacks

```bash
cdk list -c stage=dev
```

### 5. Bootstrap Environment (One-time per Account/Region)

```bash
cdk bootstrap aws://<ACCOUNT_ID>/<REGION> --profile <PROFILE>
```
