# Saathy Architecture Graphs

This directory contains comprehensive visual representations of the Saathy AI copilot architecture, from high-level system overview to detailed component relationships.

## 📊 Available Graphs

### 1. System Overview (`system_overview.png`)
High-level system architecture showing the overall components and their relationships:
- External systems (GitHub, Slack, OpenAI)
- Saathy core components
- Infrastructure services

### 2. Application Layer (`application_layer.png`)
Detailed view of the application structure:
- API layer components
- Core services
- External dependencies

### 3. Connector Framework (`connector_framework.png`)
Extensible connector system architecture:
- Base connector interface
- Specific connectors (GitHub, Slack)
- Processing pipeline

### 4. Chunking System (`chunking_system.png`)
Modular chunking strategies and components:
- Chunking processor
- Strategy implementations
- Core components and utilities
- Analysis tools

### 5. Vector Database Layer (`vector_database.png`)
Vector storage implementation:
- Vector layer components
- Qdrant database integration
- CRUD operations

### 6. Embedding Service (`embedding_service.png`)
Embedding model management:
- Service components
- Model registry
- Preprocessing pipeline
- External API integrations

### 7. Data Flow (`data_flow.png`)
Sequence diagram showing data flow through the system:
- Content input processing
- Chunking and embedding
- Vector storage operations

### 8. Configuration (`configuration.png`)
Configuration management architecture:
- Configuration sources
- Settings categories
- Validation and security

### 9. Deployment (`deployment.png`)
Containerized deployment architecture:
- Environment configurations
- Infrastructure services
- Application containerization

### 10. Monitoring & Observability (`monitoring.png`)
Observability stack architecture:
- Application telemetry
- Infrastructure monitoring
- Tracing system
- Health checks

### 11. API Endpoints (`api_endpoints.png`)
Complete API endpoint mapping:
- Health and configuration endpoints
- Connector endpoints
- Content processing endpoints
- Vector operation endpoints

### 12. Dependencies (`dependencies.png`)
Component dependency relationships:
- Core dependencies
- External services
- AI/ML libraries
- Development tools

## 🛠️ Generating Graphs

### Prerequisites

1. **Python Dependencies**: The script will automatically install required Python packages
2. **Graphviz**: Required for image generation
   ```bash
   # Ubuntu/Debian
   sudo apt-get install graphviz
   
   # macOS
   brew install graphviz
   
   # Windows
   # Download from https://graphviz.org/download/
   ```

### Quick Start

Run the generation script from the project root:

```bash
./scripts/generate_graphs.sh
```

Or manually:

```bash
# Install dependencies
pip install -r scripts/requirements-graphs.txt

# Generate graphs
python scripts/generate_architecture_graphs.py
```

### Output

Graphs are saved as PNG files in `docs/graphs/` directory.

## 📖 Documentation

- **Markdown Documentation**: `docs/architecture_graphs.md` - Contains all graphs in Mermaid format
- **Generated Images**: `docs/graphs/` - PNG files for each architecture view

## 🔧 Customization

The graph generation script (`scripts/generate_architecture_graphs.py`) can be customized to:

- Modify graph styles and colors
- Add new architecture views
- Change output formats
- Adjust graph layouts

## 📋 Graph Types

### Mermaid Graphs (Markdown)
- Rendered directly in GitHub/GitLab
- Version controlled
- Easy to edit and maintain

### PNG Images (Generated)
- High-quality visual output
- Suitable for presentations
- Standalone files

## 🎯 Usage Scenarios

1. **Architecture Documentation**: Include in technical documentation
2. **Onboarding**: Help new developers understand the system
3. **Presentations**: Use in technical presentations
4. **Planning**: Visualize system changes and improvements
5. **Troubleshooting**: Understand component relationships

## 🔄 Maintenance

- Update graphs when architecture changes
- Regenerate images after significant modifications
- Keep markdown documentation in sync with code
- Review graphs during code reviews

## 📞 Support

For issues with graph generation or architecture questions:

1. Check the script output for error messages
2. Verify Graphviz installation
3. Review Python dependencies
4. Consult the main project documentation