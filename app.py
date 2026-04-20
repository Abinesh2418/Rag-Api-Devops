import os
from fastapi import FastAPI
from fastapi.responses import FileResponse
import chromadb

# Mock LLM mode for CI testing
USE_MOCK_LLM = os.getenv("USE_MOCK_LLM", "0") == "1"

if not USE_MOCK_LLM:
    import ollama

app = FastAPI()
chroma = chromadb.PersistentClient(path="./db")
collection = chroma.get_or_create_collection("docs")

# Import and register dashboard routes from backend
from backend.api import register_dashboard_routes
register_dashboard_routes(app)


@app.post("/query")
def query(q: str):
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
