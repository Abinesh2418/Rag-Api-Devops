import json
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from openai import AzureOpenAI
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from backend.api import (
    get_deployment_history,
    get_docker_status,
    get_pipeline_status,
    register_dashboard_routes,
)

print("[STARTUP] Initializing Azure OpenAI client...")
azure_client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
)
print(
    f"[STARTUP] Azure OpenAI client ready — endpoint: {os.getenv('AZURE_OPENAI_ENDPOINT')}"
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
print(f"[STARTUP] Knowledge base loaded — {len(DOCS)} topics: {list(DOCS.keys())}")

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_docker_status",
            "description": "Get current Docker container health and running container count",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_pipeline_status",
            "description": "Get the latest CI/CD pipeline run status and stages",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_deployment_history",
            "description": "Get recent deployment history with timestamps and status",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]

TOOL_FN_MAP = {
    "get_docker_status": get_docker_status,
    "get_pipeline_status": get_pipeline_status,
    "get_deployment_history": get_deployment_history,
}


def get_context(q: str) -> str:
    q_lower = q.lower()
    if "kubernetes" in q_lower or "k8s" in q_lower:
        print("[CONTEXT] Matched topic: kubernetes")
        return DOCS["kubernetes"]
    if "docker" in q_lower:
        print("[CONTEXT] Matched topic: docker")
        return DOCS["docker"]
    if "ci" in q_lower or "cd" in q_lower or "cicd" in q_lower or "pipeline" in q_lower:
        print("[CONTEXT] Matched topic: cicd")
        return DOCS["cicd"]
    if "jenkins" in q_lower:
        print("[CONTEXT] Matched topic: jenkins")
        return DOCS["jenkins"]
    print("[CONTEXT] No topic matched — using full knowledge base (fallback)")
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
print("[STARTUP] FastAPI app ready — all routes registered")


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/query")
def query(q: str):
    print(f"[QUERY] Received: '{q}'")
    with rag_query_duration_seconds.time():
        rag_queries_total.inc()
        context = get_context(q)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a DevOps assistant. Answer questions clearly and concisely. "
                    "Use tools for live system data (container health, pipeline status, deployments) "
                    "and the provided context for conceptual questions."
                ),
            },
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {q}\n\nAnswer clearly and concisely:",
            },
        ]

        print(
            f"[AI] Calling Azure OpenAI — model: {os.getenv('AZURE_OPENAI_MODEL', 'gpt-4o')}"
        )
        try:
            response = azure_client.chat.completions.create(
                model=os.getenv("AZURE_OPENAI_MODEL", "gpt-4o"),
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                timeout=30,
            )

            msg = response.choices[0].message

            if msg.tool_calls:
                print(f"[TOOL] {len(msg.tool_calls)} tool call(s) requested")
                messages.append(msg)
                for tc in msg.tool_calls:
                    fn_name = tc.function.name
                    print(f"[TOOL] Executing: {fn_name}")
                    result = TOOL_FN_MAP[fn_name]()
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": json.dumps(result),
                        }
                    )

                print("[AI] Second pass with tool results...")
                response = azure_client.chat.completions.create(
                    model=os.getenv("AZURE_OPENAI_MODEL", "gpt-4o"),
                    messages=messages,
                    timeout=30,
                )

            return {"response": response.choices[0].message.content}
        except Exception as e:
            print(f"[ERROR] Azure OpenAI failed: {e}")
            return {"answer": f"Error: {str(e)}"}