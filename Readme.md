# Smart Automated Deployment System for Web Applications Using DevOps

> **Team 08** | Domain: DevOps  
> Abinesh B · Abisheck A M · Dharun S · Jeevan Kumar S  
> Guide: Mrs Nivetha R (Assistant Professor I)

A fully automated CI/CD pipeline that detects code changes, builds the application inside containers, runs automated tests, and deploys — all without manual intervention.

---

## Architecture Overview

```
Developer Push
      │
      ▼
GitHub Repository ──► GitHub Actions CI/CD
                              │
                ┌─────────────┼─────────────┐
                │             │             │
              Lint       Unit Tests     Security
                │             │             │
                └─────────────┼─────────────┘
                              │
                    Integration Tests
                    (if docs/ or app.py changed)
                              │
                    Docker Build & Push to GHCR
                    (only on push to main/staging)
                              │
              ┌───────────────┴───────────────┐
        Backend Container            Frontend Container
        FastAPI  :8000               Nginx    :3000
              │
      ┌───────┴────────┐
  Prometheus         Grafana
    :9090              :3001
```

**Technology Stack:**

| Layer | Tool | Purpose |
|-------|------|---------|
| Version Control | Git & GitHub | Branching, webhooks, source management |
| CI/CD | GitHub Actions | Automated build → test → deploy pipeline |
| Containerization | Docker + Docker Compose | Identical environments everywhere |
| Backend API | FastAPI + ChromaDB | RAG query engine with vector search |
| Frontend | Nginx | Dashboard UI + reverse proxy to backend |
| Monitoring | Prometheus + Grafana | Real-time metrics and auto-provisioned dashboards |

---

## Project Structure

```
.
├── app.py                          # FastAPI entry point — /query, /metrics, dashboard routes
├── embed_docs.py                   # Reads docs/*.txt → embeds into ChromaDB
├── requirements.txt                # Python dependencies
├── pyproject.toml                  # Ruff + pytest + coverage configuration
├── docker-compose.yml              # Orchestrates all 4 containers
│
├── backend/                        # Backend module
│   ├── __init__.py
│   ├── api.py                      # Dashboard API routes (docker-status, pipeline-status, etc.)
│   └── Dockerfile                  # python:3.11-slim image
│
├── frontend/                       # Frontend module
│   ├── index.html                  # Interactive DevOps dashboard UI
│   ├── nginx.conf                  # Reverse proxy: /query, /api/, /metrics → backend
│   └── Dockerfile                  # nginx:alpine image
│
├── docs/                           # RAG knowledge base (changes here trigger CI)
│   ├── k8s.txt                     # Kubernetes documentation
│   ├── Devops.txt                  # DevOps concepts
│   ├── nextwork.txt                # NextWork content
│   └── CI_AND_TESTING.md           # CI/CD documentation
│
├── monitoring/                     # Observability stack
│   ├── prometheus.yml              # Scrapes backend:8000/metrics every 15s
│   └── grafana/
│       └── provisioning/
│           ├── datasources/        # Auto-provisions Prometheus datasource (uid: prometheus)
│           └── dashboards/         # Pre-built RAG API dashboard (JSON)
│
├── tests/                          # All tests in one place
│   ├── __init__.py
│   ├── conftest.py                 # Fixtures: mock LLM + mock ChromaDB collection
│   ├── test_app.py                 # Unit tests — FastAPI TestClient for /query
│   └── semantic_test.py            # Integration tests — live RAG quality assertions
│
└── .github/
    └── workflows/
        └── ci.yml                  # Full CI/CD pipeline definition
```

---

## Services & Access URLs

| Service | URL | Purpose |
|---------|-----|---------|
| Dashboard UI | http://localhost:3000 | Frontend — ask questions, view Docker/CI/CD status |
| Backend API | http://localhost:8000/docs | Swagger UI for all endpoints |
| Prometheus | http://localhost:9090 | Metrics explorer & PromQL |
| Grafana | http://localhost:3001 | Dashboards — login: admin / admin |

---

## Quick Start

```bash
# Start all 4 services
docker-compose up --build

# Make a query
curl -X POST "http://localhost:8000/query?q=What%20is%20Kubernetes"

# View raw Prometheus metrics
curl http://localhost:8000/metrics | grep rag_
```

---

## CI/CD Pipeline

The workflow at [`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs on **every push and pull request**.

### Job Flow

```
push / PR
   │
   ├── path-filter     Detect if docs/, app.py, embed_docs.py changed → sets rag_changed
   ├── lint            ruff check + ruff format --check  (quality gate)
   ├── unit-tests      pytest tests/test_app.py + coverage ≥ 80%  (quality gate)
   ├── security        pip-audit CVE scan on requirements.txt  (quality gate)
   │
   ├── integration     Rebuild embeddings → start API → run tests/semantic_test.py
   │   └── runs when: PR (always) | push with rag_changed == true
   │
   ├── build           Docker build + push to GitHub Container Registry (ghcr.io)
   │   └── runs when: push to main or staging + all jobs above passed
   │
   └── notify          Posts PR comment listing failed jobs
       └── runs when: any job fails
```

### When Each Job Runs

| Trigger | lint | unit-tests | security | integration | build |
|---------|------|------------|----------|-------------|-------|
| PR (any files) | ✅ | ✅ | ✅ | ✅ | ❌ |
| Push — non-RAG files changed | ✅ | ✅ | ✅ | ❌ skipped | ❌ |
| Push — `docs/` or `app.py` changed | ✅ | ✅ | ✅ | ✅ | ❌ |
| Push to **main** — `docs/` changed | ✅ | ✅ | ✅ | ✅ | ✅ |

**Demo trigger:** Edit any file in `docs/` and push to `main` → all 6 jobs run including Docker build.

### Quality Gates

| Gate | Tool | Threshold |
|------|------|-----------|
| Code style | `ruff check` + `ruff format --check` | Zero violations |
| Test coverage | `pytest --cov=app` + `coverage report` | ≥ 80% |
| Vulnerabilities | `pip-audit` on requirements.txt | Zero known CVEs |

---

## RAG Application

**How it works:**
1. `embed_docs.py` reads every `.txt` from `docs/` → stores vectors in ChromaDB  
2. `POST /query?q=<question>` retrieves the closest doc chunk by vector similarity  
3. **Mock mode** (`USE_MOCK_LLM=1`) — returns the retrieved chunk directly (used in Docker + CI)  
4. **Production mode** — passes context + question to Ollama (`tinyllama`) for a generated answer

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/query?q=<text>` | RAG query → returns AI answer |
| `GET` | `/metrics` | Prometheus metrics endpoint |
| `GET` | `/docs` | Swagger UI |
| `GET` | `/api/docker-status` | Live running container stats |
| `GET` | `/api/pipeline-status` | CI/CD pipeline info |
| `GET` | `/api/deployments` | Recent deployment history |
| `GET` | `/api/auto-triggers` | Auto-trigger event timeline |

---

## Monitoring & Observability

### Prometheus Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `rag_queries_total` | Counter | Total RAG queries processed |
| `rag_query_duration_seconds` | Histogram | Per-query latency (p50/p95/p99) |

### Grafana Dashboard

Pre-built dashboard auto-loads at http://localhost:3001 (admin/admin):

- **API Requests Per Second** — `rate(rag_queries_total[1m])`
- **p95 Query Latency** — `histogram_quantile(0.95, rate(rag_query_duration_seconds_bucket[5m]))`
- **Total Queries** — running counter stat
- **Average Query Duration** — mean response time stat

### Useful PromQL Queries

```promql
rag_queries_total
rate(rag_queries_total[1m])
histogram_quantile(0.95, rate(rag_query_duration_seconds_bucket[5m])) * 1000
rate(rag_query_duration_seconds_sum[1m]) / rate(rag_query_duration_seconds_count[1m])
```

---

## Demo Checklist

### 1 — Docker Validation
```bash
docker-compose up --build
docker ps                   # 4 containers: devops-backend, devops-frontend, devops-prometheus, devops-grafana
curl http://localhost:8000/docs     # Swagger UI loads
curl http://localhost:3000          # Dashboard loads
```

### 2 — CI/CD Pipeline Demo
```bash
# Edit any file in docs/ and push to main
echo "Updated: $(date)" >> docs/k8s.txt
git add docs/k8s.txt
git commit -m "demo: trigger full CI pipeline"
git push origin main
# GitHub Actions: lint → unit-tests → security → integration → build (all green)
```

### 3 — Monitoring Demo
```bash
# Send a few queries (generates Prometheus metrics)
curl -X POST "http://localhost:8000/query?q=What%20is%20Docker"
curl -X POST "http://localhost:8000/query?q=What%20is%20Kubernetes"

# Open Grafana → http://localhost:3001 → RAG API Monitoring
# Metrics appear within 15 seconds (Prometheus scrape interval)
```

---

## Running Locally (Without Docker)

```bash
# Setup
python -m venv .venv
source .venv/bin/activate           # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install pytest pytest-cov httpx ruff pip-audit

# Build vector store
python embed_docs.py

# Start backend in mock mode
export USE_MOCK_LLM=1               # Windows: $env:USE_MOCK_LLM="1"
uvicorn app:app --host 127.0.0.1 --port 8000

# Run unit tests
pytest tests/test_app.py -v --cov=app --cov-report=term-missing

# Run semantic/integration tests (server must be running)
python tests/semantic_test.py

# Lint and security
ruff check .
ruff format --check .
pip-audit --requirement requirements.txt
```

---

## Changes Made in This Session

| Area | What Changed |
|------|-------------|
| **Lint fix** | Removed unused `FileResponse` import; moved `backend.api` import to top of `app.py` |
| **Code style** | Reformatted `app.py` and `backend/api.py` with ruff (trailing commas, line length) |
| **Frontend fix** | Changed query URL from hardcoded `http://localhost:8000/query` → relative `/query` so Nginx proxy is used |
| **Grafana fix** | Updated datasource references from deprecated string `"Prometheus"` to object `{"type":"prometheus","uid":"prometheus"}` for Grafana 10+ |
| **Grafana fix** | Added explicit `uid: prometheus` to `datasource.yml` |
| **Modularization** | Moved `semantic_test.py` → `tests/semantic_test.py`; deleted orphan `embed.py` |
| **CI update** | Updated `ci.yml` to run `python tests/semantic_test.py` from new location |
| **README** | Full rewrite with architecture diagram, demo checklist, PromQL queries, CI/CD table |

---

## Future Scope

1. **AI-Powered Deployment Decisions** — ML models to predict deployment risks
2. **Multi-Cloud Deployment** — AWS, Azure, GCP via Terraform modules
3. **GitOps with ArgoCD** — Git as single source of truth for infrastructure state
4. **Serverless & Edge** — AWS Lambda, Cloud Functions support
5. **DevSecOps** — SAST/DAST + compliance checks integrated into the pipeline
