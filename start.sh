#!/bin/bash
set -e

echo "Starting Saathy application..."

# Debug: Check Python path
echo "PYTHONPATH: $PYTHONPATH"

# Debug: Check if we can import the module
echo "Testing module import..."
python -c "import saathy; print('saathy module imported successfully')" || {
    echo "Failed to import saathy module"
    echo "Available files in /app/src:"
    ls -la /app/src/
    echo "Available files in /app/src/saathy:"
    ls -la /app/src/saathy/
    exit 1
}

# Debug: Check if we can import the API
echo "Testing API import..."
python -c "from saathy.api import app; print('API imported successfully')" || {
    echo "Failed to import API"
    exit 1
}

echo "Starting uvicorn server..."
exec uvicorn saathy.api:app --host 0.0.0.0 --port 8000 