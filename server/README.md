# Synthetic Dataset Generator 🚀

Generate large, realistic datasets using natural language and LLMs (Google Gemini or GitHub Copilot / Claude Sonnet). Serve it as either an MCP tool, a FastMCP service, or a standalone FastAPI backend for the SynthxAI web UI.

## Quick Start

```bash
# 1. Install dependencies (includes pytest & utilities)
python -m pip install -e .

# 2. Configure LLM credentials
cp .env.example .env
# edit .env and set either GEMINI_API_KEY or COPILOT_API_KEY
# set GENERATION_PROVIDER=copilot to switch to Copilot

# 3a. Start as an MCP server (for tool integrations)
python main.py server

# 3b. Start the public API (for the Next.js frontend)
python main.py api --host 0.0.0.0 --port 8080

# 3c. Start the FastMCP Copilot server
python main.py fastmcp
```

## What It Does

Describe your dataset in plain English → Get a complete, realistic dataset in CSV/JSON/Parquet format.

**Example**: "Generate 10,000 sales records with customer names, products, amounts ($10-$1000), and dates"

## Key Features

- 🗣️ Natural language schema extraction (Gemini or Copilot)
- 📊 Generate 10K+ row datasets
- 🔄 Resumable jobs (pause/resume/retry)
- ✅ Field validation & constraints
- 🎯 Uniqueness guarantees
- 📁 Multiple formats (CSV, JSON, Parquet)
- 📈 Progress tracking

## Documentation

- **Full Guide**: [README_FULL.md](README_FULL.md)
- **Setup**: [SETUP.md](SETUP.md)
- **Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md)
- **Summary**: [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)

## Project Flow

1. **Schema Parsing**: User describes data → LLM extracts a structured schema
2. **Job Setup**: Confirm schema → Set parameters → Create job (`POST /jobs`)
3. **Generation**: Background worker generates chunks automatically and updates progress (`GET /jobs/{id}/progress`)
4. **Download**: Merge chunks (`POST /jobs/{id}/merge`) → Stream the dataset (`GET /jobs/{id}/download`)

## MCP Tools

| Tool | Purpose |
|------|---------|
| `extract_schema` | Natural language → Schema |
| `create_job` | Setup generation job |
| `generate_chunk` | Generate data chunk |
| `get_job_progress` | Check progress |
| `control_job` | Pause/resume/cancel |
| `list_jobs` | View all jobs |
| `run_job` | Trigger background run if auto-start is disabled |
| `merge_and_download` | Get final dataset |
| `validate_schema` | Validate schema |

## FastMCP Copilot Server

Need GitHub Copilot to generate very large datasets? Launch the dedicated FastMCP server:

```bash
GENERATION_PROVIDER=copilot python main.py fastmcp
```

Expose the `generate_dataset` tool to any MCP-compatible runtime. Provide a schema and row count, and the server orchestrates chunked generation, optional row streaming, and final dataset merging. Set `include_rows=true` in the tool arguments to receive the generated rows directly in the response (handy for small batches).

## Requirements

- Python 3.10+
- One of:
    - Google Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))
    - GitHub Copilot API key with Claude Sonnet access (set `COPILOT_API_KEY` and `GENERATION_PROVIDER=copilot`)

## Installation

```bash
# Install dependencies
pip install -e .

# Setup environment
cp .env.example .env
# Edit .env and add GEMINI_API_KEY or COPILOT_API_KEY

# Create directories
mkdir -p temp output logs
```

### Configure LLM credentials

Copy `.env.example` to `.env` and populate the credentials for your preferred provider.

#### Gemini (default)

```bash
cp .env.example .env
# open .env in your editor and set GEMINI_API_KEY
```

You can also export the key directly when running in CI:

```bash
export GEMINI_API_KEY="your-real-key"
```

#### GitHub Copilot / Claude Sonnet

```bash
cp .env.example .env
# set COPILOT_API_KEY and GENERATION_PROVIDER=copilot
```

Optional shell export:

```bash
export COPILOT_API_KEY="ghu_xxx"
export GENERATION_PROVIDER=copilot
```

## Usage Example

```python
# 1. Extract schema
extract_schema(
    user_input="Generate 5000 user profiles with name, email, age (18-80), and country"
)

# 2. Create job
create_job(
    schema={...},
    total_rows=5000,
    chunk_size=1000,
    output_format="csv"
)

# 3. Generate chunks
for chunk_id in range(5):
    generate_chunk(job_id="...", chunk_id=chunk_id)

# 4. Download dataset
merge_and_download(job_id="...")
```

## Project Structure

```
├── src/                  # Source code
│   ├── api/             # Gemini API client
│   ├── core/            # Core models & job manager
│   ├── mcp_server/      # MCP server
│   ├── storage/         # Storage handlers
│   └── utils/           # Utilities
├── tests/               # Test suite
├── examples/            # Usage examples
├── main.py              # Entry point
└── pyproject.toml       # Dependencies
```

## Configuration

Edit `.env`:

```bash
GEMINI_API_KEY=
GEMINI_MODEL=gemini-1.5-pro
COPILOT_API_KEY=
COPILOT_MODEL=claude-3.5-sonnet
DEFAULT_CHUNK_SIZE=1000
STORAGE_TYPE=disk
RATE_LIMIT_REQUESTS_PER_MINUTE=60
GENERATION_PROVIDER=gemini
```

## Supported Field Types

String, Integer, Float, Boolean, Date, DateTime, Email, Phone, UUID, Enum, JSON, Array

## Field Constraints

Unique, Nullable, Min/Max values, Min/Max length, Pattern, Enum values, Format

## Output Formats

- **CSV**: Comma-separated values
- **JSON**: JSON array of objects
- **Parquet**: Columnar format (efficient for large data)

## Testing

```bash
# Install dev dependencies (optional if you used python -m pip install -e .)
python -m pip install -e ".[dev]"

# Run tests
python -m pytest

# Run examples
python examples/usage_examples.py
```

## Troubleshooting

**Import errors?**
```bash
pip install -e .
```

**API key errors?**
- Check `.env` has valid `GEMINI_API_KEY`
- Get key from https://makersuite.google.com/

**Memory issues?**
```bash
# In .env
STORAGE_TYPE=disk
DEFAULT_CHUNK_SIZE=500
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes and add tests
4. Submit a pull request

## License

MIT License

## Support

- 📖 Read the docs: `README_FULL.md`
- 🐛 Found a bug? Open an issue
- 💡 Feature request? Open an issue
- ❓ Questions? Check `SETUP.md` or open a discussion

---

**Made with ❤️ by the HACKMAN Team**

**Status**: ✅ Production Ready | **Version**: 0.1.0
