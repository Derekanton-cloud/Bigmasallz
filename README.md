# Bigmasallz – Synthetic Dataset Studio

Build realistic datasets from natural language prompts using a FastAPI backend powered by Gemini and a Next.js control surface. This repo contains everything you need to extract schemas, launch generation jobs, monitor progress, and download finished CSV/JSON/Parquet files.

## 📦 Repository Layout

```
├── server/                # FastAPI + MCP backend (Python)
│   ├── src/               # Core services, API routers, job manager
│   ├── tests/             # Pytest suite covering models & validators
│   └── main.py            # Entry point (MCP server or API server)
└── client/                # Next.js 16 frontend (React 19)
	└── bigmasallz_client/ # App router, Tailwind styling, UI components
```

## 🔑 Prerequisites

- **Python** 3.10 or newer (3.13 tested)
- **Node.js** 20+ (Next.js 16 requirement)
- **Google Gemini API key** (set `GEMINI_API_KEY`)
- macOS, Linux, or Windows (tested on Windows 11)

## ⚙️ Environment Variables

| Variable | Location | Purpose |
| --- | --- | --- |
| `GEMINI_API_KEY` | Backend (`server/.env` or shell) | Authenticates Gemini schema/dataset calls |
| `NEXT_PUBLIC_API_BASE_URL` | Frontend (`client/bigmasallz_client/.env.local`) | URL of the FastAPI server, e.g. `http://localhost:8080` |

> Copy `server/.env.example` to `.env` and set `GEMINI_API_KEY` before starting the backend.

## 🚀 Quickstart

### 1. Backend (FastAPI)

```bash
cd server
python -m pip install -e .
python main.py api --host 0.0.0.0 --port 8080
```

This exposes:

- `POST /schema/extract` – convert a natural language description into a schema
- `POST /jobs` – create and auto-start a generation job
- `GET /jobs/{id}/progress` – poll real-time status
- `POST /jobs/{id}/merge` – merge chunks when finished
- `GET /jobs/{id}/download` – stream the merged dataset file

Background generation runs automatically when `auto_start=true` (the default from the UI).

### 2. Frontend (Next.js)

```bash
cd client/bigmasallz_client
npm install
echo "NEXT_PUBLIC_API_BASE_URL=http://localhost:8080" > .env.local
npm run dev
```

Open `http://localhost:3000` and follow the flow:

1. Describe your dataset in the narrative panel or chat.
2. Click **Suggest schema** to let the agent draft columns.
3. Adjust fields, row count, chunk size, and format.
4. Hit **Generate dataset** and watch progress/telemetry update in real time.
5. Download the final file from the Dataset Preview card.

Schema edits propagate instantly, and previews are shown for CSV/JSON outputs (first 5 records).

## ✅ Validation

Run automated checks before committing:

```bash
# Backend (from /server)
python -m pytest

# Frontend (from /client/bigmasallz_client)
npm run build  # also runs TypeScript checks
```

> On Windows you may need to clear cached builds with `rm -rf .next` if a previous Turbopack process locked the directory.

## 🌐 Manual Smoke Test

1. Start the backend API (`python main.py api --port 8080`).
2. Start the frontend (`npm run dev`).
3. Visit the UI, describe a dataset, auto-generate the schema, and launch a job.
4. Wait for completion, inspect the preview, and download the output file.

If you do not have a Gemini key, the extraction/generation steps will return configuration errors; set `GEMINI_API_KEY` in a `.env` file or export it in your shell before launching the API.

## 🧠 Architecture Highlights

- **Generation service** orchestrates schema validation, chunking, and dataset merging.
- **Job manager** tracks progress, supports pause/resume/cancel, and stores metadata on disk.
- **MCP integration** allows the same backend to run as an MCP server for broader tooling.
- **UI orchestration** handles schema drafting, job creation, progress polling, telemetry, and download actions in a single page.

For deeper implementation details, see `server/ARCHITECTURE.md` and `server/README_FULL.md`.

## 🤝 Contributing

1. Fork the repo & create a feature branch.
2. Update or add tests (`pytest`, `npm run build`).
3. Submit a PR describing the dataset scenario you enabled.

---

Built with ❤️ by the HACKMAN team. Need help? Check `server/SETUP.md` or open an issue.