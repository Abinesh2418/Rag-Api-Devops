# RAG API – Automated Testing & DevOps Pipeline

This project is a small **Retrieval-Augmented Generation (RAG) API** built with **FastAPI** and **ChromaDB**, wrapped in a **GitHub Actions CI/CD pipeline** that demonstrates:

- Automated unit and semantic tests
- Quality gates (lint + coverage)
- Security checks (dependency auditing)
- Staging deployment via Docker images
- Failure notifications (PR comments + email)

The goal is to model a **real DevOps loop** for an AI/RAG service.

---

## Application Overview

- **API**: `app.py` exposes a single endpoint:
  - `POST /query?q=...` – returns an answer built from the embedded docs.
- **Vector store**: `embed_docs.py`:
  - Reads `.txt` files from `docs/`
  - Stores them in a `chromadb` collection.
- **LLM behavior**:
  - In **mock mode** (`USE_MOCK_LLM=1`), the API returns the retrieved context directly.
  - In **production mode**, it calls **Ollama** (model `tinyllama`) to answer using the retrieved context.

The CI pipeline mainly tests the **RAG behavior** in mock mode so we can run reliably in GitHub Actions without external LLM dependencies.

---

## CI/CD Pipeline Overview

The workflow lives in `[.github/workflows/ci.yml](.github/workflows/ci.yml)` and runs on:

- **Every `push`**
- **Every `pull_request`**

Jobs (in logical order):

1. `path-filter`
2. `lint`
3. `unit-tests`
4. `security`
5. `integration` (semantic tests)
6. `build` (staging Docker image)
7. `notify` (failure notifications)

All jobs are **additive** – none of the original app behavior is changed by CI.

---

## Jobs and When They Run

### 1. `path-filter` (change detection)

**Purpose**: Decide if heavy RAG/semantic tests should run.

- Runs on **every push and PR**.
- Uses `dorny/paths-filter` to set a flag `rag_changed` to `true` if any of these change:
  - `docs/**`
  - `app.py`
  - `embed_docs.py`

**Output**:

- `needs.path-filter.outputs.rag_changed == 'true'` → RAG-related files changed.
- `== 'false'` → only non-RAG files changed (e.g., docs/CI-only changes).

This output is consumed by the `integration` job.

---

### 2. `lint` (style & static checks)

**Tool**: [Ruff](https://github.com/astral-sh/ruff)  
**Config**: `[pyproject.toml](pyproject.toml)` (`[tool.ruff]` + `[tool.ruff.format]`)

- Runs on **every push and PR**.
- Steps:
  - `ruff check .`
  - `ruff format --check .`

**Quality gate**:

- If Ruff finds errors or formatting drift → **job fails** → **workflow fails**.

**Where to see output**:

- Actions → run → `lint` job:
  - `Run Ruff check` / `Run Ruff format check` steps show exact violations.

---

### 3. `unit-tests` (fast API tests + coverage)

**Test files**:

- `tests/test_app.py` – FastAPI `TestClient` tests for `/query`
- `tests/conftest.py` – Fixtures:
  - Sets `USE_MOCK_LLM=1` so Ollama is not required.
  - Mocks `chromadb` collection for deterministic behavior.

**What it does**:

- Installs production + test deps from `requirements.txt` plus `pytest`, `pytest-cov`, `httpx`.
- Runs:

```bash
pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=xml
coverage report --fail-under=80
```

**Quality gate**:

- If **any test fails** → job fails.
- If **coverage < 80% for `app.py`** → `coverage report --fail-under=80` fails.

**Where to see output**:

- Actions → run → `unit-tests` job:
  - Pytest output (test names, pass/fail).
  - Coverage table for `app.py` with missing lines if any.

---

### 4. `security` (dependency vulnerability scanning)

**Tool**: [`pypa/gh-action-pip-audit`](https://github.com/pypa/gh-action-pip-audit)  
**Input**: `requirements.txt`

- Runs on **every push and PR**.
- Installs deps from `requirements.txt`.
- Runs `pip-audit` against the dependency list.

**Quality gate**:

- If any dependency has a known CVE → `security` **fails** → workflow fails.

**Where to see output**:

- Actions → run → `security` job → `Run pip-audit for vulnerability scanning`:
  - Lists packages, versions, vulnerability IDs (e.g., CVE-XXXX-YYYY), and severities.

---

### 5. `integration` (semantic RAG tests)

This is where the **end-to-end RAG behavior** is tested.

**What it does**:

1. Installs deps from `requirements.txt`.
2. Runs `python embed_docs.py`:
   - Rebuilds embeddings from all `.txt` files in `docs/`.
3. Starts the API in **mock mode**:
   - `USE_MOCK_LLM=1 uvicorn app:app --host 0.0.0.0 --port 8000 &`
   - Waits a few seconds for the server.
4. Runs `python semantic_test.py`:
   - Sends HTTP POST requests to `/query` and asserts that answers contain key concepts
     (e.g., `"container"` for Kubernetes, `"maximus"` for NextWork).

**When it runs**:

```yaml
if: github.event_name == 'pull_request' || needs.path-filter.outputs.rag_changed == 'true'
```

- **Always on PRs** (regardless of which files changed).
- On **pushes only when** any of:
  - `docs/**`
  - `app.py`
  - `embed_docs.py`
  changed (so `rag_changed == 'true'`).

**Outputs / meaning**:

- ✅ `integration` green:
  - RAG embeddings + API + semantic tests all passed.
  - Changes did not degrade answer quality for the tested queries.
- ⛔ `integration` red:
  - Something broke in:
    - embeddings (`embed_docs.py`)
    - API behavior (`app.py`)
    - or semantic expectations (`semantic_test.py`).

---

### 6. `build` (staging Docker image)

**Purpose**: Build a **staging Docker image** and push it to **GitHub Container Registry**.

**Dockerfile**: `[Dockerfile](Dockerfile)`:

- Installs dependencies from `requirements.txt`.
- Copies `app.py`, `embed_docs.py`, and `docs/`.
- Runs `python embed_docs.py` at build time.
- Exposes port 8000 and runs:

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

**When it runs**:

```yaml
build:
  needs: [path-filter, lint, unit-tests, security, integration]
  if: github.event_name == 'push' && (github.ref == 'refs/heads/staging' || github.ref == 'refs/heads/main')
```

- Event **must** be a `push` to **`staging`** or **`main`**.
- All CI jobs (`path-filter`, `lint`, `unit-tests`, `security`, `integration`) must have **succeeded**.

**What it does**:

- Logs in to `ghcr.io` using `GITHUB_TOKEN`.
- Uses `docker/metadata-action` to generate tags:
  - `staging-<commit-sha>`
  - `staging-latest`
- Uses `docker/build-push-action` to:
  - Build the image from the repository
  - Push to:
    - `ghcr.io/<owner>/<repo>:staging-<sha>`
    - `ghcr.io/<owner>/<repo>:staging-latest`

**Where to see output**:

- Actions → run → `build` job:
  - Shows build logs and `Pushed` lines with image tags.
- GitHub → repo → **Packages**:
  - Shows the container image and available tags.

**How to run the staging image locally**:

```bash
docker pull ghcr.io/<owner>/<repo>:staging-latest
docker run -p 8000:8000 ghcr.io/<owner>/<repo>:staging-latest
```

---

### 7. `notify` (failure notifications)

**Purpose**: When the workflow fails, post a **short summary comment on the PR**.

**When it runs**:

```yaml
notify:
  needs: [path-filter, lint, unit-tests, security, integration]
  if: failure()
```

- Runs only when the **overall workflow fails**.
- Gathers which `needs.*.result` values are `"failure"`.
- If the event is a PR, uses `actions/github-script` to create a comment.

**Example PR comment**:

```markdown
## CI Pipeline Failed

The following job(s) failed:
- lint
- unit-tests

**Workflow Run:** https://github.com/<owner>/<repo>/actions/runs/<id>
**Commit:** <sha>
**Branch:** <branch>

Please check the workflow logs for details.
```

In addition, you enabled **GitHub’s built-in email notifications**:

- GitHub → Settings → Notifications → Actions → “Email (Failed workflows only)”
- You receive an email whenever a workflow run fails.

---

## Summary: Which Features Trigger When?

| Event / Condition                                    | path-filter | lint | unit-tests | security | integration | build | notify |
|------------------------------------------------------|------------|------|------------|----------|------------|-------|--------|
| **PR (any files)**                                  | ✅          | ✅    | ✅          | ✅        | ✅          | ❌     | ⛔ only if failure |
| **Push to feature/test branch (no RAG changes)**    | ✅          | ✅    | ✅          | ✅        | ❌ (skipped) | ❌     | ⛔ only if failure |
| **Push to feature/test branch (RAG files changed)** | ✅          | ✅    | ✅          | ✅        | ✅          | ❌     | ⛔ only if failure |
| **Push to `staging`/`main` (no RAG changes)**       | ✅          | ✅    | ✅          | ✅        | ❌ (skipped) | ❌     | ⛔ only if failure |
| **Push to `staging`/`main` (RAG files changed)**    | ✅          | ✅    | ✅          | ✅        | ✅          | ✅     | ⛔ only if failure |

Legend:

- ✅ – job runs
- ❌ – job never runs for this case (by design)
- ⛔ – job runs **only if** there is a failure upstream (`if: failure()`)

---

## Running Things Locally

### 1. Setup

```bash
python -m venv .venv
source .venv/bin/activate  # PowerShell: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install pytest pytest-cov httpx ruff pip-audit
```

### 2. Rebuild embeddings

```bash
python embed_docs.py
```

### 3. Start the API (mock mode)

```bash
export USE_MOCK_LLM=1  # PowerShell: $env:USE_MOCK_LLM="1"
uvicorn app:app --host 127.0.0.1 --port 8000
```

### 4. Run semantic tests

In another terminal (with the venv active):

```bash
python semantic_test.py
```

### 5. Run unit tests with coverage

```bash
pytest tests/ -v --cov=app --cov-report=term-missing
coverage report --fail-under=80
```

### 6. Run lint and security checks

```bash
ruff check .
ruff format --check .
pip-audit --requirement requirements.txt
```

---

## What This Project Demonstrates

End-to-end, this repository shows how to:

- Build a small **RAG API** with FastAPI + ChromaDB.
- Add **semantic tests** that assert answer quality using real queries.
- Use **GitHub Actions** to:
  - Run linting and unit tests on every push and PR.
  - Enforce **coverage thresholds** and style checks as **quality gates**.
  - Run **integration tests** only when relevant files change.
  - Run **security checks** on dependencies.
  - Build and push a **staging Docker image** on successful `staging`/`main` pushes.
  - Send **notifications** (PR comments + email) when runs fail.

This is a template for treating an AI/RAG service like a real production system with solid DevOps practices.
