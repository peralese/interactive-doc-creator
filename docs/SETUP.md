# Setup Guide - Interactive Document Creator

## Prerequisites

- **Python**: 3.10 or higher
- **Node.js**: 18 or higher (for frontend)
- **Git**: For version control
- **Optional**: Ollama for local LLM (recommended for privacy)

## Backend Setup

### 1. Clone and Navigate

```bash
cd /home/peralese/Projects/interactive-doc-creator
```

### 2. Create Virtual Environment

```bash
cd backend
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
nano .env  # or use your preferred editor
```

**Minimum required settings**:
```env
# For local development with Ollama
LLM_DEFAULT_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3

# Whisper settings
WHISPER_MODEL=base
WHISPER_DEVICE=cpu
```

### 5. Initialize Database

The database will be created automatically on first run. To manually initialize:

```bash
# The database is created when you first start the server
# Location: ./data/sessions.db (SQLite)
```

### 6. Start the Backend Server

```bash
# From the backend directory
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The server will start at:
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/api/docs
- **Health Check**: http://localhost:8000/health

## Frontend Setup

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The Vite development server proxies API requests
to the backend on port 8000.

## Ollama Setup (Recommended)

For local LLM without API costs:

### 1. Install Ollama

```bash
# Linux
curl -fsSL https://ollama.com/install.sh | sh

# macOS
brew install ollama

# Windows
# Download from https://ollama.com/download
```

### 2. Start Ollama Service

```bash
ollama serve
```

### 3. Pull a Model

```bash
# Recommended: Llama 3 (4.7GB)
ollama pull llama3

# Or smaller model for testing
ollama pull llama3:8b

# Or larger for better quality
ollama pull llama3:70b
```

### 4. Test Ollama

```bash
curl http://localhost:11434/api/generate -d '{
  "model": "llama3",
  "prompt": "Hello, how are you?"
}'
```

## Whisper Setup

Whisper models are downloaded automatically on first use. Models are cached in `~/.cache/huggingface/`.

**Model sizes**:
- `tiny`: 39M parameters, ~75MB
- `base`: 74M parameters, ~142MB (recommended for development)
- `small`: 244M parameters, ~466MB
- `medium`: 769M parameters, ~1.5GB
- `large`: 1550M parameters, ~2.9GB

To pre-download a model:

```python
from faster_whisper import WhisperModel

model = WhisperModel("base", device="cpu", compute_type="int8")
```

## Verification

### 1. Check Backend Health

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "app": "Interactive Document Creator",
  "version": "0.1.0"
}
```

### 2. List Templates

```bash
curl http://localhost:8000/api/templates/
```

### 3. Create a Test Session

```bash
curl -X POST http://localhost:8000/api/sessions/ \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": "project-overview-v1",
    "metadata": {"test": true}
  }'
```

## Troubleshooting

### Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or use a different port
uvicorn app.main:app --reload --port 8001
```

### Database Errors

```bash
# Remove and recreate database
rm data/sessions.db
# Restart server to recreate
```

### Import Errors

```bash
# Ensure virtual environment is activated
which python  # Should show path to venv

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Ollama Connection Issues

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Restart Ollama
pkill ollama
ollama serve
```

### Whisper Model Download Issues

```bash
# Clear cache and retry
rm -rf ~/.cache/huggingface/hub/models--guillaumekln--faster-whisper-*

# Or set custom cache directory
export HF_HOME=/path/to/cache
```

## Development Workflow

### 1. Activate Environment

```bash
cd backend
source venv/bin/activate
```

### 2. Make Changes

Edit files in `app/` directory

### 3. Run Tests

```bash
pytest
```

### 4. Format Code

```bash
black app/
ruff check app/ --fix
```

### 5. Type Check

```bash
mypy app/
```

### 6. Restart Server

The server auto-reloads with `--reload` flag, but for major changes:

```bash
# Stop server (Ctrl+C)
# Restart
uvicorn app.main:app --reload
```

## Next Steps

After setup is complete:

1. **Explore the API**: Visit http://localhost:8000/api/docs
2. **Review Templates**: Check `templates/` directory
3. **Read the Plan**: See `docs/INTERACTIVE_DOC_CREATOR_PLAN.md`
4. **Continue Development**: Begin Phase 3 requirements ingestion

## Production Deployment

For production deployment, see [DEPLOYMENT.md](DEPLOYMENT.md) (coming soon).

Key considerations:
- Use PostgreSQL instead of SQLite
- Set `DEBUG=false`
- Use proper secret keys
- Configure CORS properly
- Use HTTPS
- Set up monitoring
- Configure backups

## Support

For issues or questions:
- Check the [README.md](../README.md)
- Review the [Plan](INTERACTIVE_DOC_CREATOR_PLAN.md)
- Open an issue on GitHub
