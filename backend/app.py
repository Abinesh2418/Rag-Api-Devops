import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from openai import AzureOpenAI
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from backend.api import register_dashboard_routes

azure_client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
)

# In-memory knowledge base — no ChromaDB/ONNX download needed
DOCS = {
    "kubernetes": (
        "Kubernetes is a large-scale container orchestration tool used to manage containers at scale. "
        "In a Kubernetes ecosystem, Minikube acts as your local sandbox cluster for practice, while Kubectl "
        "is the command-line tool you use to manage it. Your application code runs inside a Pod (the smallest unit), "
        "but because individual Pods are temporary, you use a Deployment to ensure the correct number of copies are "
        "always running and healthy. A Service acts as a stable front door or load balancer so users can always reach your app."
    ),
    "docker": (
        "Docker is a platform for packaging and running applications inside containers. A container bundles the application "
        "code, runtime, libraries, and dependencies together so it runs the same everywhere — on a laptop, server, or cloud. "
        "Docker uses a Dockerfile to define the image, and docker-compose to run multi-container applications. "
        "It solves the 'works on my machine' problem by ensuring consistent environments across development, testing, and production."
    ),
    "cicd": (
        "CI/CD stands for Continuous Integration and Continuous Deployment. CI automatically builds and tests code every time "
        "a developer pushes a change, catching bugs early. CD automatically deploys passing builds to staging or production. "
        "This project uses GitHub Actions as the CI/CD tool — it runs linting, unit tests, and integration tests on every push "
        "and pull request, then deploys automatically when all checks pass."
    ),
    "jenkins": (
        "Jenkins is an open-source automation server used to build CI/CD pipelines. It automatically builds, tests, and deploys "
        "applications whenever code changes are pushed. Jenkins uses a Jenkinsfile to define pipeline stages such as Build, Test, "
        "and Deploy. It supports hundreds of plugins for integration with tools like Docker, Kubernetes, GitHub, and Slack. "
        "Jenkins is self-hosted, giving teams full control over their automation infrastructure."
    ),
}


def get_context(q: str) -> str:
    q_lower = q.lower()
    if "kubernetes" in q_lower or "k8s" in q_lower:
        return DOCS["kubernetes"]
    if "docker" in q_lower:
        return DOCS["docker"]
    if "ci" in q_lower or "cd" in q_lower or "cicd" in q_lower or "pipeline" in q_lower:
        return DOCS["cicd"]
    if "jenkins" in q_lower:
        return DOCS["jenkins"]
    # fallback — combine all docs
    return " ".join(DOCS.values())


app = FastAPI(title="Automate DevOps Workflows with AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rag_queries_total = Counter("rag_queries_total", "Total number of queries")
rag_query_duration_seconds = Histogram(
    "rag_query_duration_seconds", "Query duration in seconds"
)

register_dashboard_routes(app)


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/query")
def query(q: str):
    with rag_query_duration_seconds.time():
        rag_queries_total.inc()
        context = get_context(q)

        try:
            response = azure_client.chat.completions.create(
                model=os.getenv("AZURE_OPENAI_MODEL", "gpt-4o"),
                messages=[
                    {
                        "role": "system",
                        "content": "You are a DevOps assistant. Answer questions clearly and concisely based on the provided context.",
                    },
                    {
                        "role": "user",
                        "content": f"Context:\n{context}\n\nQuestion: {q}\n\nAnswer clearly and concisely:",
                    },
                ],
                timeout=30,
            )
            return {"answer": response.choices[0].message.content}
        except Exception as e:
            raise HTTPException(status_code=200, detail={"answer": f"Error: {str(e)}"})