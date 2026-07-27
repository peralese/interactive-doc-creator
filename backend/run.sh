#!/bin/bash
# Quick start script for Interactive Document Creator backend

set -e

echo "🚀 Interactive Document Creator - Backend Startup"
echo "=================================================="
echo ""

# Check if virtual environment exists
if [ -d "venv" ]; then
    VENV_DIR="venv"
elif [ -d ".venv" ]; then
    VENV_DIR=".venv"
else
    echo "❌ Virtual environment not found!"
    echo "Please run setup first:"
    echo "  python -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements-minimal.txt"
    exit 1
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    cp .env.example .env
    echo "✅ Created .env file. Please review and update settings."
    echo ""
fi

# Activate virtual environment
echo "🔧 Activating virtual environment ($VENV_DIR)..."
source $VENV_DIR/bin/activate

# Check if dependencies are installed
if ! python -c "import fastapi" 2>/dev/null; then
    echo "❌ Dependencies not installed!"
    echo "Installing dependencies..."
    echo ""
    echo "Note: Using requirements-minimal.txt (PDF generation excluded)"
    echo "To add PDF support later, install system libraries and run:"
    echo "  pip install -r requirements-pdf.txt"
    echo ""
    pip install -r requirements-minimal.txt
fi

# Create data directories if they don't exist
mkdir -p ../data/audio ../data/sessions

echo "✅ Environment ready!"
echo ""
echo "📊 Starting FastAPI server..."
echo "   API: http://localhost:8000"
echo "   Docs: http://localhost:8000/api/docs"
echo "   Health: http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Made with Bob
