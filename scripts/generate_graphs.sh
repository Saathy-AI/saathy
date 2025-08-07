#!/bin/bash

# Generate architecture graphs for Saathy repository
# This script installs dependencies and generates comprehensive architecture graphs

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🚀 Generating Saathy Architecture Graphs"
echo "========================================"

# Check if we're in the right directory
if [ ! -f "$PROJECT_ROOT/pyproject.toml" ]; then
    echo "❌ Error: Not in Saathy project root directory"
    echo "Please run this script from the project root or scripts directory"
    exit 1
fi

# Install graph generation dependencies
echo "📦 Installing graph generation dependencies..."
pip install -r "$SCRIPT_DIR/requirements-graphs.txt"

# Check if graphviz is installed on the system
if ! command -v dot &> /dev/null; then
    echo "⚠️  Warning: Graphviz 'dot' command not found"
    echo "Please install Graphviz:"
    echo "  Ubuntu/Debian: sudo apt-get install graphviz"
    echo "  macOS: brew install graphviz"
    echo "  Windows: Download from https://graphviz.org/download/"
    echo ""
    echo "Continuing without image generation..."
fi

# Generate the graphs
echo "🎨 Generating architecture graphs..."
cd "$PROJECT_ROOT"
python "$SCRIPT_DIR/generate_architecture_graphs.py"

echo ""
echo "✅ Graph generation complete!"
echo "📁 Graphs saved to: docs/graphs/"
echo ""
echo "📋 Generated graphs:"
echo "  • system_overview.png - High-level system architecture"
echo "  • application_layer.png - Application layer structure"
echo "  • connector_framework.png - Connector framework"
echo "  • chunking_system.png - Chunking system architecture"
echo "  • vector_database.png - Vector database layer"
echo "  • embedding_service.png - Embedding service"
echo "  • data_flow.png - Data flow sequence"
echo "  • configuration.png - Configuration management"
echo "  • deployment.png - Deployment architecture"
echo "  • monitoring.png - Monitoring & observability"
echo "  • api_endpoints.png - API endpoints"
echo "  • dependencies.png - Component dependencies"
echo ""
echo "📖 View the markdown documentation: docs/architecture_graphs.md"