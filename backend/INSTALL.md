# Installation Guide

## Quick Install (Recommended)

Use the minimal requirements file which excludes PDF generation (can be added later):

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements-minimal.txt
```

This installs everything except PDF generation support.

## Full Install (with PDF Support)

PDF generation requires system libraries. Install them first:

### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install -y ffmpeg libavcodec-dev libavformat-dev libavdevice-dev \
    libavutil-dev libavfilter-dev libswscale-dev libswresample-dev
```

### macOS
```bash
brew install ffmpeg pkg-config
```

### Windows
Download and install FFmpeg from https://ffmpeg.org/download.html

Then install Python packages:
```bash
pip install -r requirements-minimal.txt
pip install -r requirements-pdf.txt
```

## Verify Installation

```bash
# Test basic imports
python -c "import fastapi, sqlalchemy, pydantic"

# Test LLM providers
python -c "import openai, anthropic, ollama"

# Test Whisper
python -c "from faster_whisper import WhisperModel"

# Test PDF (if installed)
python -c "import weasyprint"
```

## Troubleshooting

### Issue: weasyprint installation fails

**Solution**: Use `requirements-minimal.txt` instead. PDF generation is optional and can be added later.

### Issue: faster-whisper fails to install

**Solution**: Make sure you have a C++ compiler installed:
- Ubuntu/Debian: `sudo apt-get install build-essential`
- macOS: `xcode-select --install`
- Windows: Install Visual Studio Build Tools

### Issue: ollama package not found

**Solution**: Update pip and try again:
```bash
pip install --upgrade pip
pip install ollama
```

## What Gets Installed

### Core (requirements-minimal.txt)
- FastAPI web framework
- SQLAlchemy database ORM
- Pydantic data validation
- OpenAI, Anthropic, Ollama clients
- faster-whisper for speech-to-text
- python-docx for Word documents
- markdown for Markdown generation

### Optional (requirements-pdf.txt)
- weasyprint for PDF generation

### Development (included in minimal)
- pytest for testing
- black for code formatting
- ruff for linting
- mypy for type checking

## Next Steps

After installation:
1. Copy `.env.example` to `.env`
2. Configure your LLM provider settings
3. Run the server: `./run.sh` or `uvicorn app.main:app --reload`