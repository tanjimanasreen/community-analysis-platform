# Plan 096 — AWS Memgraph Deployment Deferred

**Status: DEFERRED / NOT REQUIRED FOR CURRENT DEPLOYMENT**

## Purpose

Document the decision to defer AWS deployment of Memgraph Community Edition for the current `community-analysis` productionization effort.

This is an intentional scope decision, not a removal of Memgraph support.

## Current Data Flow

For the datasets currently being deployed and demonstrated, analytical input continues to come from the existing repository-supported raw-data workflow:

```text
data/raw/
    ↓
existing ingestion / preprocessing
    ↓
network / community / topic / theme / evolution pipelines
    ↓
canonical analytical run artifacts
    ↓
S3
    ↓
Lambda API
    ↓
CloudFront frontend