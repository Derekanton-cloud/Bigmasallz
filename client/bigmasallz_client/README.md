## SynthxAI Frontend

This app is the visual command center for the Synthetic Dataset Generator backend. Describe the dataset you need, review auto-generated schemas, launch jobs, track progress, and download CSV/JSON/Parquet outputs—all from a single page.

### Prerequisites

- Node.js 20+
- Backend API running (see `../../server/README.md`)
- `.env.local` with the backend URL:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8080
```

### Installation & Development

```bash
npm install
npm run dev
# open http://localhost:3000
```

During development, the UI polls the backend every 2 seconds while a job is running. Progress and telemetry metrics update automatically.

### Production Build

```bash
npm run build   # TypeScript + Next.js production build
npm start       # Serve the compiled app
```

If you see a Turbopack root warning, set `turbopack.root` in `next.config.ts` or keep a single `package-lock.json` in the workspace. On Windows, clean stale artifacts with `rm -rf .next` if a locked directory triggers an EPERM error.

### End-to-End Flow

1. **Narrative** – Describe the dataset in plain English.
2. **Suggest schema** – The backend proposes columns, types, sample values, and constraint hints.
3. **Refine fields** – Edit column names, data types, descriptions, uniqueness, and examples.
4. **Generate dataset** – Creates a job, auto-starts chunk generation, and monitors progress.
5. **Review preview** – Displays the first 5 rows for CSV/JSON outputs.
6. **Download** – Fetch the merged dataset using the provided link.

### Key Files

| File | Purpose |
| --- | --- |
| `app/page.tsx` | Main orchestration page (schema extraction, job lifecycle, preview) |
| `app/components/SchemaArchitect.tsx` | Form for configuring dataset blueprint |
| `app/components/DatasetPreview.tsx` | Shows stats, sample rows, and download button |
| `app/components/SynthesisTimeline.tsx` | Displays progress steps and LLM metrics |

### Troubleshooting

- **Schema extraction fails** – Ensure the backend has a valid `GEMINI_API_KEY`.
- **Preview empty** – JSON/Parquet outputs only show samples the UI can parse; download for full data.
- **Windows EPERM during build** – `rm -rf .next` before `npm run build`.

Happy dataset crafting! 🎛️
