# Automate DevOps Workflows with AI

> **Team 08** | Domain: DevOps
> Abinesh B · Abisheck A M · Dharun S · Jeevan Kumar S
> Guide: Mrs Nivetha R (Assistant Professor I)

A fully automated CI/CD pipeline that detects code changes, builds the application inside containers, runs automated tests, and deploys — all without manual intervention. The core application is a **RAG (Retrieval-Augmented Generation) API** powered by **Azure OpenAI (GPT-4o)** with **Redis caching**.

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
          ┌───────────────────┴───────────────────┐
    Backend Container                   Frontend Container
    FastAPI  :8000                      Nginx    :3000
          │
    ┌─────┴──────┐
  Redis         Prometheus ──► Grafana
  :6379           :9090          :3001
  (cache)
```

**Technology Stack:**

| Layer | Tool | Purpose |
|-------|------|---------|
| Version Control | Git & GitHub | Branching, webhooks, source management |
| CI/CD | GitHub Actions | Automated build → test → deploy pipeline |
| Containerization | Docker + Docker Compose | Identical environments everywhere |
| Backend API | FastAPI | RAG query engine with in-memory knowledge base |
| LLM | Azure OpenAI (GPT-4o) | Generates answers from retrieved context |
| Cache | Redis 7 | Query result caching — skips LLM on repeat questions |
| Frontend | Nginx | Dashboard UI + reverse proxy to backend |
| Monitoring | Prometheus + Grafana | Real-time metrics and auto-provisioned dashboards |

---

## How It Works

```
User Question
      │
      ▼
  Redis Cache ──► Cache Hit? ──► Return cached answer instantly
      │ miss
      ▼
  In-memory DOCS (keyword match: kubernetes, docker, cicd, jenkins...)
      │
      ▼
  Azure OpenAI GPT-4o (context + question → generated answer)
      │
      ▼
  Store answer in Redis (TTL: 1 hour)
      │
      ▼
  Return answer + Prometheus metrics increment
```

---

## Project Structure

```
.
├── app.py                          # FastAPI entry point — /query, /metrics, dashboard routes
├── embed_docs.py                   # Document embedding utility
├── requirements.txt                # Python dependencies
├── pyproject.toml                  # Ruff + pytest + coverage configuration
├── docker-compose.yml              # Orchestrates all 6 containers
│
├── backend/                        # Backend module
│   ├── __init__.py
│   ├── api.py                      # Dashboard API routes (docker-status, pipeline-status, etc.)
│   ├── Dockerfile                  # python:3.11-slim image
│   └── .env                        # Azure OpenAI credentials (not committed to git)
│
├── frontend/                       # Frontend module
│   ├── index.html                  # Interactive DevOps dashboard UI
│   ├── nginx.conf                  # Reverse proxy: /query, /api/, /metrics → backend
│   └── Dockerfile                  # nginx:alpine image
│
├── docs/                           # RAG knowledge base documents
│   ├── k8s.txt                     # Kubernetes documentation
│   ├── Devops.txt                  # DevOps concepts
│   ├── nextwork.txt                # NextWork content
│   └── CI_AND_TESTING.md           # CI/CD documentation
│
├── monitoring/                     # Observability stack
│   ├── prometheus.yml              # Scrapes backend:8000/metrics every 15s
│   └── grafana/
│       └── provisioning/
│           ├── datasources/        # Auto-provisions Prometheus datasource
│           └── dashboards/         # Pre-built RAG API dashboard (JSON)
│
├── tests/                          # All tests
│   ├── conftest.py                 # Fixtures: mock Azure OpenAI client
│   ├── test_app.py                 # Unit tests — FastAPI TestClient for /query
│   └── semantic_test.py            # Integration tests — live RAG quality assertions
│
└── .github/
    └── workflows/
        └── ci.yml                  # Full CI/CD pipeline definition
```

---

## Services & Access URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| Dashboard UI | http://localhost:3000 | — |
| Backend API (Swagger) | http://localhost:8000/docs | — |
| Prometheus | http://localhost:9090 | — |
| Grafana | http://localhost:3001 | admin / admin |
| Redis | localhost:6379 | — |

---

## Quick Start

### Prerequisites
- Docker Desktop running
- Azure OpenAI credentials (already in `backend/.env`)

```bash
# Start all 6 services (backend, frontend, redis, prometheus, grafana + network)
docker-compose up --build

# Ask a question
curl -X POST "http://localhost:8000/query?q=What%20is%20Kubernetes"

# Ask the same question again — served from Redis cache
curl -X POST "http://localhost:8000/query?q=What%20is%20Kubernetes"

# View raw Prometheus metrics
curl http://localhost:8000/metrics | grep rag_
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/query?q=<text>` | RAG query → returns AI-generated answer |
| `GET` | `/metrics` | Prometheus metrics endpoint |
| `GET` | `/docs` | Swagger UI |
| `GET` | `/api/docker-status` | Live running container stats |
| `GET` | `/api/pipeline-status` | CI/CD pipeline info |
| `GET` | `/api/deployments` | Recent deployment history |
| `GET` | `/api/auto-triggers` | Auto-trigger event timeline |

### Supported Query Topics

| Keyword in question | Context used |
|---------------------|-------------|
| `kubernetes`, `k8s` | Kubernetes — pods, deployments, services, minikube |
| `docker` | Docker — containers, images, Dockerfile, compose |
| `ci`, `cd`, `pipeline` | GitHub Actions CI/CD pipeline |
| `jenkins` | Jenkins automation server |
| anything else | All docs combined (fallback) |

---

## AI Self-Healing CI/CD Pipeline

The most important feature of this project. When unit tests fail, instead of stopping and waiting for a human to read logs and fix the code manually, the pipeline **automatically triggers an AI repair agent**.

### The Two-Pass Loop

```
PASS 1 — Broken code
  push → unit-tests FAIL
              │
              ▼
         ai-repair job
         ├── Re-runs tests, captures failure output
         ├── Sends failure log + app.py to Azure GPT-4o
         ├── AI diagnoses the bug and writes a corrected app.py
         ├── Commits fix to new branch: ai-fix/run-<id>
         └── Opens Pull Request with full failure context

         ↓ Human reviews the AI's PR — inspects diff, merges if correct ↓

PASS 2 — Corrected code
  merge → fresh CI run → unit-tests PASS → build → deploy
```

### Why it's safe
The AI never commits directly to main. Every fix goes through a pull request — the **human-in-the-loop gate**. This protects against the AI fixing the wrong thing or introducing a new bug.

### What the AI is scoped to do
- Read the pytest failure output (last 3000 chars)
- Read `app.py`, `tests/test_app.py`, `tests/conftest.py`
- Fix **only the lines in `app.py`** causing the failure
- Output the complete corrected file — no restructuring, no side effects

---

## CI/CD Pipeline

The workflow at [`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs on **every push and pull request**.

### Job Flow

```
push / PR
   │
   ├── path-filter     Detect if docs/, app.py, embed_docs.py changed
   ├── lint            ruff check + ruff format --check
   ├── unit-tests      pytest + coverage ≥ 80%
   │       │
   │       └── FAIL? → ai-repair  ← AI reads failure, fixes app.py, opens PR
   │                               (human reviews + merges → triggers Pass 2)
   ├── security        pip-audit CVE scan on requirements.txt
   │
   ├── integration     Start API → run semantic_test.py
   │   └── runs when: PR (always) | push with docs/app.py changed
   │
   ├── build           Docker build + push to ghcr.io
   │   └── runs when: push to main or staging + all jobs above passed
   │
   └── notify          Posts PR comment listing failed jobs
       └── runs when: any job fails
```

### Trigger Matrix

| Trigger | lint | unit-tests | security | integration | build |
|---------|------|------------|----------|-------------|-------|
| PR (any files) | ✅ | ✅ | ✅ | ✅ | ❌ |
| Push — non-RAG files | ✅ | ✅ | ✅ | ❌ skipped | ❌ |
| Push — `docs/` or `app.py` changed | ✅ | ✅ | ✅ | ✅ | ❌ |
| Push to **main** — `docs/` changed | ✅ | ✅ | ✅ | ✅ | ✅ |

### Quality Gates

| Gate | Tool | Threshold |
|------|------|-----------|
| Code style | `ruff check` + `ruff format --check` | Zero violations |
| Test coverage | `pytest --cov=app` | ≥ 80% |
| Vulnerabilities | `pip-audit` | Zero known CVEs |

### GitHub Secrets Required

Go to **Repo → Settings → Secrets and variables → Actions** and add:

| Secret | Value |
|--------|-------|
| `AZURE_OPENAI_API_KEY` | Your Azure OpenAI API key |
| `AZURE_OPENAI_ENDPOINT` | `https://<your-resource>.cognitiveservices.azure.com/` |

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
# Total queries
rag_queries_total

# Request rate (per minute)
rate(rag_queries_total[1m])

# p95 latency in milliseconds
histogram_quantile(0.95, rate(rag_query_duration_seconds_bucket[5m])) * 1000

# Average response time
rate(rag_query_duration_seconds_sum[1m]) / rate(rag_query_duration_seconds_count[1m])
```

---

## Redis Caching

Redis caches query answers to avoid redundant Azure OpenAI API calls.

- Cache key: MD5 hash of the question string
- TTL: 1 hour per entry
- Persistence: `appendonly yes` with a named Docker volume (`redis-data`)
- First request: calls Azure OpenAI → stores in Redis → returns answer
- Repeat request: reads from Redis instantly, no LLM call

```bash
# Inspect Redis cache
docker exec -it devops-redis redis-cli KEYS "*"
docker exec -it devops-redis redis-cli TTL <key>
```

---

## Running Locally (Without Docker)

```bash
# Setup virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1        # Windows PowerShell

pip install -r requirements.txt
pip install pytest pytest-cov httpx ruff pip-audit

# Set Azure OpenAI environment variables
$env:AZURE_OPENAI_API_KEY="your-key"
$env:AZURE_OPENAI_ENDPOINT="https://your-resource.cognitiveservices.azure.com/"
$env:AZURE_OPENAI_API_VERSION="2024-12-01-preview"
$env:AZURE_OPENAI_MODEL="gpt-4o"

# Start backend
uvicorn app:app --host 127.0.0.1 --port 8000

# Run unit tests
pytest tests/test_app.py -v --cov=app --cov-report=term-missing

# Lint and security
ruff check .
ruff format --check .
pip-audit --requirement requirements.txt
```

---

## Demo Checklist

### 1 — Docker Validation
```bash
docker-compose up --build
docker ps   # 6 containers: backend, frontend, redis, prometheus, grafana + network
curl http://localhost:8000/docs       # Swagger UI
curl http://localhost:3000            # Dashboard UI
```

### 2 — RAG Query Demo
```bash
# First call — hits Azure OpenAI
curl -X POST "http://localhost:8000/query?q=What%20is%20Kubernetes"

# Second call — served from Redis cache (instant)
curl -X POST "http://localhost:8000/query?q=What%20is%20Kubernetes"
```

### 3 — CI/CD Pipeline Demo
```bash
# Edit a doc file and push → triggers all 6 CI jobs
echo "Updated: $(Get-Date)" >> docs/k8s.txt
git add docs/k8s.txt
git commit -m "demo: trigger full CI pipeline"
git push origin main
# GitHub Actions: lint → unit-tests → security → integration → build → all green
```

### 4 — Monitoring Demo
```bash
# Generate metrics
for i in 1..5 { curl -X POST "http://localhost:8000/query?q=What%20is%20Docker" }

# Open Grafana → http://localhost:3001 → RAG API Monitoring
# Metrics appear within 15 seconds
```

---

## Future Scope

1. **Kubernetes Manifests** — Deploy all services on Minikube with HPA and Ingress
2. **Helm Chart** — Package the full stack as a distributable Helm chart
3. **GitOps with ArgoCD** — Git as single source of truth for k8s state
4. **Multi-Cloud** — AWS/Azure/GCP deployment via Terraform modules
5. **DevSecOps** — SAST/DAST scanning integrated into the pipeline
6. **Expanded RAG** — Add Terraform, Helm, Azure docs to the knowledge base
