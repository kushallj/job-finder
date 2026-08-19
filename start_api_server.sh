#!/bin/bash
# Start the FastAPI server

cd "$(dirname "$0")"

echo "🚀 Starting Job Finder API Server..."
echo "📍 Server will be available at: http://localhost:8000"
echo "📚 API docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Start server with uvicorn
python main.py
