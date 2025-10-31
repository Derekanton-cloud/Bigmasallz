# SynthX.AI Backend

FastAPI service orchestrating Gemini-powered LangChain agents to generate synthetic datasets with human-in-the-loop schema approval, ChromaDB deduplication, and live telemetry.

## Getting Started

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp ../.env ./.env  # or configure environment variables
uvicorn app.main:app --reload
```

## Docker

```bash
docker compose up --build
```

- `server` exposes FastAPI on `http://localhost:8080`
- `client` serves the Next.js UI on `http://localhost:3000`
- `chromadb` hosts the deduplication vector store on `http://localhost:8000`

## Key Commands

- `poetry run pytest` *(if you add tests)*
- `uvicorn app.main:app --host 0.0.0.0 --port 8080`

See `docs/architecture.md` and `docs/workflow.md` for deeper background.
