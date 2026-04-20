import os

import chromadb
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from backend.api import register_dashboard_routes

USE_MOCK_LLM = os.getenv("USE_MOCK_LLM", "0") == "1"

if not USE_MOCK_LLM:
    import ollama

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

chroma = chromadb.PersistentClient(path="./db")
collection = chroma.get_or_create_collection("docs")

rag_queries_total = Counter("rag_queries_total", "Total number of queries")
rag_query_duration_seconds = Histogram(
    "rag_query_duration_seconds", "Query duration in seconds"
)

register_dashboard_routes(app)


# Metrics endpoint for Prometheus
@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/query")
def query(q: str):
    with rag_query_duration_seconds.time():
        rag_queries_total.inc()
        results = collection.query(query_texts=[q], n_results=1)
        context = results["documents"][0][0] if results["documents"] else ""

        if USE_MOCK_LLM:
            # In mock mode, return the retrieved context directly
            return {"answer": context}

        # In production mode, use Ollama
        answer = ollama.generate(
            model="tinyllama",
            prompt=f"Context:\n{context}\n\nQuestion: {q}\n\nAnswer clearly and concisely:",
        )

        return {"answer": answer["response"]}
