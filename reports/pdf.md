# RAG API with Automated DevOps Pipeline

---

## Slide 1 — Title

# RAG API with Automated DevOps Pipeline

**Domain:** DevOps

| Name | Register No |
|------|:-----------:|
| Abisheck A M | 23BCS007 |
| Abinesh B | 23BCS006 |
| Dharun S | 23BCS034 |
| Jeevan Kumar S | 23BCS064 |

---

## Slide 2 — Problem Statement

### Why Did We Build This?

Manual software deployment is broken in three ways:

**It is slow and repetitive.**
Every time code changes, someone manually builds, tests, and uploads the application. The same steps, done by hand, every single time.

**It is error-prone.**
Humans miss steps. A skipped test or a wrong config file can break production. There is nothing in the process that stops bad code from going live.

**There is no visibility.**
After a deployment, teams are in the dark. They don't know how the application is performing, when it slows down, or when something breaks — unless a user reports it.

> ✗ Time-consuming & repetitive
> ✗ Error-prone & inconsistent
> ✗ Hard to scale across teams
> ✗ No real-time observability
> ✗ AI systems go stale without fresh data

---

## Slide 3 — Solution

### What We Built

We built a system where everything — testing, security scanning, building, packaging — happens automatically the moment a developer pushes code.

**An AI-Powered Q&A System**
Users type a question. The system searches through documents stored in ChromaDB, passes the relevant content to an LLM (Groq — llama-3.1-8b-instant), and returns a clear, grounded answer.

**A Fully Automated CI/CD Pipeline**
Every `git push` triggers:
- Code quality check (Ruff)
- Unit tests with 80% coverage requirement (pytest)
- Security vulnerability scan (pip-audit)
- End-to-end integration test in mock mode
- Docker image build and push to GHCR

**One-Command Startup**
```bash
docker compose up --build
```
Starts the backend, frontend, vector database, and monitoring all at once.

**Live Monitoring — No Setup Needed**
Prometheus scrapes metrics automatically. Grafana dashboards load on their own. The team can see query counts, response times, and errors in real time.

> ✓ Automated CI/CD pipeline
> ✓ AI-powered RAG Q&A system
> ✓ One-command Docker deploy
> ✓ Built-in monitoring and alerts


---

## Slide 4 — Tech Stack

### Tools & Technologies

| Layer | Tool | What It Does |
|---|---|---|
| Backend API | FastAPI (Python 3.11) | Handles queries, exposes API and metrics |
| Reverse Proxy | Nginx (Alpine) | Routes web traffic, serves the frontend |
| Vector Database | ChromaDB | Stores and retrieves document embeddings |
| AI / LLM | Azure OpenAI + Microsoft AI Foundry | Primary LLM provider — enterprise-grade model hosting |
| AI / LLM Fallback | Groq API (Free Open Tier) | Fallback LLM using llama-3.1-8b-instant — free tier, fast inference |
| Containerization | Docker + Compose | Packages and runs all five services together |
| CI/CD Pipeline | GitHub Actions | Runs tests, security checks, and Docker builds automatically |
| Metrics | Prometheus | Scrapes API performance data every 15 seconds |
| Dashboards | Grafana (v10.4.3) | Displays live charts and monitoring panels |
| Code Quality | Ruff | Lints and formats Python code on every commit |
| Testing | pytest + pytest-cov | Runs tests and measures coverage (min 80%) |
| Security | pip-audit | Scans dependencies for known vulnerabilities (CVEs) |
| Image Registry | GHCR | Stores built Docker images with version tags |

### LLM Strategy

The system uses **Azure OpenAI** (via Microsoft AI Foundry) as the primary LLM for production-grade, reliable AI responses. As a **fallback**, **Groq API** (free open tier) is used — providing fast LLM inference using `llama-3.1-8b-instant` at zero cost. This ensures the system keeps working even when the primary provider is unavailable.

### Knowledge Base Used by the RAG System

| Document | Content |
|---|---|
| `Devops.txt` | DevOps concepts and RAG fundamentals |
| `k8s.txt` | Kubernetes architecture and terms |
| `nextwork.txt` | NextWork platform documentation |
| `CI_AND_TESTING.md` | CI/CD and automated testing practices |

---

## Slide 5 — Architecture

### How the System Works — End to End

**When a user asks a question:**

```
User types a question in the browser
          ↓
    Nginx (Port 3000)
    Forwards the request to FastAPI
          ↓
    FastAPI (Port 8000)
    Searches ChromaDB for relevant documents
          ↓
    ChromaDB
    Returns the most matching document chunks
          ↓
    Azure OpenAI / Groq (Fallback)
    Reads context + question, writes an answer
          ↓
    JSON response sent back to the browser
```

**When a developer pushes code:**

```
git push
    ↓  GitHub Actions starts automatically
    ↓
Stage 1 — Lint (Ruff)           Zero style violations required
    ↓
Stage 2 — Unit Tests (pytest)   Minimum 80% coverage required
    ↓
Stage 3 — Security (pip-audit)  Zero CVEs allowed
    ↓
Stage 4 — Integration Tests     Full API tested in mock mode
    ↓
Stage 5 — Docker Build & Push   Images pushed to GHCR
```

**The Docker stack — five containers running together:**

| Container | Port | Role |
|---|---|---|
| `backend` | 8000 | FastAPI RAG server |
| `frontend` | 3000 | Nginx web UI + proxy |
| `chromadb` | — | Vector database |
| `prometheus` | 9090 | Metrics collection |
| `grafana` | 3001 | Live dashboards |

**Monitoring flow:**

```
FastAPI /metrics endpoint
    → Prometheus scrapes every 15 seconds
    → Grafana displays live dashboards
```


---

## Slide 6 — Pros & Cons

### Pros — What Works Well

| Advantage | Why It Matters |
|---|---|
| Fully automated pipeline | One `git push` does everything — no manual steps from code to Docker image |
| Security on every push | pip-audit stops known vulnerabilities before any image is built |
| Monitoring out of the box | Prometheus and Grafana are pre-configured — dashboards load automatically |
| Free LLM fallback | Groq free tier ensures the AI keeps working even if the primary LLM is unavailable |

### Cons — Current Limitations

| Limitation | What It Means |
|---|---|
| Final deployment is manual | Images are pushed automatically but running them on a server still requires manual steps |
| No auto-scaling | Docker Compose does not scale containers up or down based on traffic |
| Knowledge base needs restart | New documents require re-running `embed_docs.py` and restarting the backend |
| Grafana alerts don't notify | Dashboards show data but alerts are not sent to Slack, email, or any channel |

---

## Slide 7 — Conclusion

### What We Built and What We Learned

We built a complete, working DevOps system from scratch — one that automates everything a developer would otherwise do by hand.

**What we achieved:**

- A RAG question-answering system using Azure OpenAI with Groq as a free-tier fallback
- A 5-stage automated CI/CD pipeline: lint, unit tests, security scan, integration test, Docker build
- A 5-container Docker stack that starts with one command and monitors itself automatically
- Code quality, 80% test coverage, and security enforced on every single commit
- Docker images pushed to GHCR with `:latest` and commit SHA tags for full traceability
- Real-time Grafana dashboards showing query counts, response times, and system health

**What we learned:**

- How to write multi-stage GitHub Actions workflows with conditional job execution
- Why AI systems need a mock mode to be testable in CI without expensive infrastructure
- How Docker containers on a private network communicate using service names as hostnames
- How Prometheus scrapes metrics and how Grafana auto-provisions dashboards from config files
- That good DevOps pipelines enforce standards automatically — they don't rely on people to remember

**What comes next:**

| Future Plan | What It Would Add |
|---|---|
| Kubernetes | Auto-scaling, self-healing, and zero-downtime rolling updates |
| Full auto-deployment | Containers deployed to the server automatically after a successful build |
| GitOps with ArgoCD | Infrastructure managed entirely through Git |
| Alert routing | Grafana alerts sent to Slack or email when something breaks |


---

**Thank You — Team 8 | Questions?**
