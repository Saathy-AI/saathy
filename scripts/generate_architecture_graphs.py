#!/usr/bin/env python3
"""
Generate architecture graphs for the Saathy repository.

This script creates comprehensive visual representations of the Saathy AI copilot
architecture, from high-level system overview to detailed component relationships.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import graphviz
from graphviz import Digraph

# Add the src directory to the path to import saathy modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from saathy.config import get_settings


class ArchitectureGraphGenerator:
    """Generate comprehensive architecture graphs for Saathy."""
    
    def __init__(self, output_dir: str = "docs/graphs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.settings = get_settings()
        
    def generate_all_graphs(self):
        """Generate all architecture graphs."""
        print("Generating Saathy architecture graphs...")
        
        graphs = [
            ("system_overview", self._create_system_overview_graph),
            ("application_layer", self._create_application_layer_graph),
            ("connector_framework", self._create_connector_framework_graph),
            ("chunking_system", self._create_chunking_system_graph),
            ("vector_database", self._create_vector_database_graph),
            ("embedding_service", self._create_embedding_service_graph),
            ("data_flow", self._create_data_flow_graph),
            ("configuration", self._create_configuration_graph),
            ("deployment", self._create_deployment_graph),
            ("monitoring", self._create_monitoring_graph),
            ("api_endpoints", self._create_api_endpoints_graph),
            ("dependencies", self._create_dependencies_graph),
        ]
        
        for name, generator_func in graphs:
            print(f"Generating {name} graph...")
            try:
                graph = generator_func()
                self._save_graph(graph, name)
                print(f"✓ Generated {name}.png")
            except Exception as e:
                print(f"✗ Failed to generate {name}: {e}")
        
        print(f"\nAll graphs saved to: {self.output_dir}")
    
    def _save_graph(self, graph: Digraph, name: str):
        """Save graph as PNG file."""
        output_path = self.output_dir / f"{name}.png"
        graph.render(str(output_path), format='png', cleanup=True)
    
    def _create_system_overview_graph(self) -> Digraph:
        """Create high-level system architecture graph."""
        dot = Digraph(comment='Saathy System Overview')
        dot.attr(rankdir='TB')
        
        # External Systems
        with dot.subgraph(name='cluster_external') as c:
            c.attr(label='External Systems', style='filled', color='lightgrey')
            c.node('github', 'GitHub')
            c.node('slack', 'Slack')
            c.node('openai', 'OpenAI API')
        
        # Saathy Core
        with dot.subgraph(name='cluster_saathy') as c:
            c.attr(label='Saathy AI Copilot', style='filled', color='lightblue')
            c.node('api', 'FastAPI Application')
            c.node('conn', 'Connector Framework')
            c.node('chunk', 'Chunking System')
            c.node('emb', 'Embedding Service')
            c.node('vec', 'Vector Database Layer')
            c.node('telem', 'Telemetry & Observability')
        
        # Infrastructure
        with dot.subgraph(name='cluster_infra') as c:
            c.attr(label='Infrastructure', style='filled', color='lightgreen')
            c.node('nginx', 'Nginx Reverse Proxy')
            c.node('qdrant', 'Qdrant Vector DB')
            c.node('jaeger', 'Jaeger Tracing')
            c.node('prometheus', 'Prometheus Metrics')
            c.node('grafana', 'Grafana Dashboards')
        
        # Connections
        dot.edge('github', 'api')
        dot.edge('slack', 'api')
        dot.edge('openai', 'emb')
        
        dot.edge('api', 'conn')
        dot.edge('api', 'chunk')
        dot.edge('api', 'emb')
        dot.edge('api', 'vec')
        dot.edge('api', 'telem')
        
        dot.edge('conn', 'chunk')
        dot.edge('chunk', 'emb')
        dot.edge('emb', 'vec')
        
        dot.edge('vec', 'qdrant')
        dot.edge('telem', 'jaeger')
        dot.edge('telem', 'prometheus')
        dot.edge('prometheus', 'grafana')
        
        dot.edge('nginx', 'api')
        
        return dot
    
    def _create_application_layer_graph(self) -> Digraph:
        """Create application layer architecture graph."""
        dot = Digraph(comment='Saathy Application Layer')
        dot.attr(rankdir='TB')
        
        # API Layer
        with dot.subgraph(name='cluster_api') as c:
            c.attr(label='API Layer', style='filled', color='lightblue')
            c.node('main', '__main__.py')
            c.node('api', 'api.py')
            c.node('config', 'config.py')
            c.node('scheduler', 'scheduler.py')
        
        # Core Services
        with dot.subgraph(name='cluster_services') as c:
            c.attr(label='Core Services', style='filled', color='lightgreen')
            c.node('chunking', 'chunking/')
            c.node('connectors', 'connectors/')
            c.node('embedding', 'embedding/')
            c.node('vector', 'vector/')
            c.node('telemetry', 'telemetry.py')
        
        # External Dependencies
        with dot.subgraph(name='cluster_deps') as c:
            c.attr(label='External Dependencies', style='filled', color='lightgrey')
            c.node('fastapi', 'FastAPI')
            c.node('uvicorn', 'Uvicorn')
            c.node('pydantic', 'Pydantic Settings')
            c.node('apscheduler', 'APScheduler')
            c.node('otel', 'OpenTelemetry')
        
        # Connections
        dot.edge('main', 'api')
        dot.edge('api', 'config')
        dot.edge('api', 'scheduler')
        dot.edge('api', 'chunking')
        dot.edge('api', 'connectors')
        dot.edge('api', 'embedding')
        dot.edge('api', 'vector')
        dot.edge('api', 'telemetry')
        
        dot.edge('main', 'fastapi')
        dot.edge('main', 'uvicorn')
        dot.edge('config', 'pydantic')
        dot.edge('scheduler', 'apscheduler')
        dot.edge('telemetry', 'otel')
        
        return dot
    
    def _create_connector_framework_graph(self) -> Digraph:
        """Create connector framework architecture graph."""
        dot = Digraph(comment='Saathy Connector Framework')
        dot.attr(rankdir='TB')
        
        # Connector Base
        with dot.subgraph(name='cluster_base') as c:
            c.attr(label='Connector Base', style='filled', color='lightblue')
            c.node('base', 'base.py')
            c.node('content', 'content_processor.py')
        
        # Specific Connectors
        with dot.subgraph(name='cluster_connectors') as c:
            c.attr(label='Specific Connectors', style='filled', color='lightgreen')
            c.node('github', 'github_connector.py')
            c.node('slack', 'slack_connector.py')
        
        # External APIs
        with dot.subgraph(name='cluster_external') as c:
            c.attr(label='External APIs', style='filled', color='lightgrey')
            c.node('gh_api', 'GitHub API')
            c.node('sl_api', 'Slack API')
        
        # Processing Pipeline
        with dot.subgraph(name='cluster_pipeline') as c:
            c.attr(label='Processing Pipeline', style='filled', color='lightyellow')
            c.node('chunk', 'Chunking System')
            c.node('emb', 'Embedding Service')
            c.node('vec', 'Vector Storage')
        
        # Connections
        dot.edge('base', 'github')
        dot.edge('base', 'slack')
        dot.edge('content', 'github')
        dot.edge('content', 'slack')
        
        dot.edge('github', 'gh_api')
        dot.edge('slack', 'sl_api')
        
        dot.edge('github', 'chunk')
        dot.edge('slack', 'chunk')
        dot.edge('chunk', 'emb')
        dot.edge('emb', 'vec')
        
        return dot
    
    def _create_chunking_system_graph(self) -> Digraph:
        """Create chunking system architecture graph."""
        dot = Digraph(comment='Saathy Chunking System')
        dot.attr(rankdir='TB')
        
        # Chunking Processor
        with dot.subgraph(name='cluster_processor') as c:
            c.attr(label='Chunking Processor', style='filled', color='lightblue')
            c.node('proc', 'processor.py')
            c.node('strat', 'strategies.py')
        
        # Strategy Implementations
        with dot.subgraph(name='cluster_strategies') as c:
            c.attr(label='Strategy Implementations', style='filled', color='lightgreen')
            c.node('fixed', 'fixed_size.py')
            c.node('semantic', 'semantic.py')
            c.node('document', 'document.py')
            c.node('code', 'code.py')
            c.node('email', 'email.py')
            c.node('meeting', 'meeting.py')
            c.node('slack_msg', 'slack_message.py')
            c.node('git', 'git_commit.py')
        
        # Core Components
        with dot.subgraph(name='cluster_core') as c:
            c.attr(label='Core Components', style='filled', color='lightyellow')
            c.node('interfaces', 'interfaces.py')
            c.node('models', 'models.py')
            c.node('exceptions', 'exceptions.py')
        
        # Utilities
        with dot.subgraph(name='cluster_utils') as c:
            c.attr(label='Utilities', style='filled', color='lightpink')
            c.node('cache', 'chunk_cache.py')
            c.node('merger', 'chunk_merger.py')
            c.node('detector', 'content_detector.py')
            c.node('hash', 'hash_utils.py')
            c.node('quality', 'quality_validator.py')
        
        # Analysis
        with dot.subgraph(name='cluster_analysis') as c:
            c.attr(label='Analysis', style='filled', color='lightcyan')
            c.node('analyzer', 'analyzer.py')
            c.node('visualizer', 'visualizer.py')
        
        # Connections
        dot.edge('proc', 'strat')
        dot.edge('strat', 'fixed')
        dot.edge('strat', 'semantic')
        dot.edge('strat', 'document')
        dot.edge('strat', 'code')
        dot.edge('strat', 'email')
        dot.edge('strat', 'meeting')
        dot.edge('strat', 'slack_msg')
        dot.edge('strat', 'git')
        
        dot.edge('proc', 'interfaces')
        dot.edge('proc', 'models')
        dot.edge('proc', 'exceptions')
        
        dot.edge('proc', 'cache')
        dot.edge('proc', 'merger')
        dot.edge('proc', 'detector')
        dot.edge('proc', 'hash')
        dot.edge('proc', 'quality')
        
        dot.edge('proc', 'analyzer')
        dot.edge('analyzer', 'visualizer')
        
        return dot
    
    def _create_vector_database_graph(self) -> Digraph:
        """Create vector database layer architecture graph."""
        dot = Digraph(comment='Saathy Vector Database Layer')
        dot.attr(rankdir='TB')
        
        # Vector Layer
        with dot.subgraph(name='cluster_vector') as c:
            c.attr(label='Vector Layer', style='filled', color='lightblue')
            c.node('client', 'client.py')
            c.node('repo', 'repository.py')
            c.node('models', 'models.py')
            c.node('exceptions', 'exceptions.py')
            c.node('metrics', 'metrics.py')
        
        # Qdrant Database
        with dot.subgraph(name='cluster_qdrant') as c:
            c.attr(label='Qdrant Database', style='filled', color='lightgreen')
            c.node('collections', 'Collections')
            c.node('points', 'Points')
            c.node('search', 'Search API')
            c.node('cluster', 'Clustering')
        
        # Operations
        with dot.subgraph(name='cluster_ops') as c:
            c.attr(label='Operations', style='filled', color='lightyellow')
            c.node('insert', 'Insert Operations')
            c.node('search_op', 'Search Operations')
            c.node('update', 'Update Operations')
            c.node('delete', 'Delete Operations')
        
        # Connections
        dot.edge('client', 'repo')
        dot.edge('repo', 'models')
        dot.edge('repo', 'exceptions')
        dot.edge('repo', 'metrics')
        
        dot.edge('client', 'collections')
        dot.edge('client', 'points')
        dot.edge('client', 'search')
        dot.edge('client', 'cluster')
        
        dot.edge('repo', 'insert')
        dot.edge('repo', 'search_op')
        dot.edge('repo', 'update')
        dot.edge('repo', 'delete')
        
        return dot
    
    def _create_embedding_service_graph(self) -> Digraph:
        """Create embedding service architecture graph."""
        dot = Digraph(comment='Saathy Embedding Service')
        dot.attr(rankdir='TB')
        
        # Embedding Service
        with dot.subgraph(name='cluster_service') as c:
            c.attr(label='Embedding Service', style='filled', color='lightblue')
            c.node('service', 'service.py')
            c.node('models', 'models.py')
            c.node('preproc', 'preprocessing.py')
            c.node('chunk', 'chunking.py')
        
        # Model Registry
        with dot.subgraph(name='cluster_models') as c:
            c.attr(label='Model Registry', style='filled', color='lightgreen')
            c.node('mini', 'all-MiniLM-L6-v2')
            c.node('mpnet', 'all-mpnet-base-v2')
            c.node('multi', 'multilingual-e5-large')
            c.node('custom', 'Custom Models')
        
        # Preprocessing Pipeline
        with dot.subgraph(name='cluster_preproc') as c:
            c.attr(label='Preprocessing Pipeline', style='filled', color='lightyellow')
            c.node('clean', 'Text Cleaning')
            c.node('normalize', 'Normalization')
            c.node('tokenize', 'Tokenization')
            c.node('filter', 'Content Filtering')
        
        # External APIs
        with dot.subgraph(name='cluster_external') as c:
            c.attr(label='External APIs', style='filled', color='lightgrey')
            c.node('openai', 'OpenAI API')
            c.node('huggingface', 'HuggingFace')
            c.node('local', 'Local Models')
        
        # Connections
        dot.edge('service', 'models')
        dot.edge('service', 'preproc')
        dot.edge('service', 'chunk')
        
        dot.edge('models', 'mini')
        dot.edge('models', 'mpnet')
        dot.edge('models', 'multi')
        dot.edge('models', 'custom')
        
        dot.edge('preproc', 'clean')
        dot.edge('preproc', 'normalize')
        dot.edge('preproc', 'tokenize')
        dot.edge('preproc', 'filter')
        
        dot.edge('models', 'openai')
        dot.edge('models', 'huggingface')
        dot.edge('models', 'local')
        
        return dot
    
    def _create_data_flow_graph(self) -> Digraph:
        """Create data flow architecture graph."""
        dot = Digraph(comment='Saathy Data Flow')
        dot.attr(rankdir='LR')
        
        # Participants
        dot.node('user', 'User/Webhook')
        dot.node('api', 'FastAPI')
        dot.node('conn', 'Connector')
        dot.node('chunk', 'Chunking')
        dot.node('emb', 'Embedding')
        dot.node('vec', 'Vector DB')
        dot.node('qdrant', 'Qdrant')
        
        # Flow
        dot.edge('user', 'api', 'Content Input')
        dot.edge('api', 'conn', 'Process Content')
        dot.edge('conn', 'chunk', 'Chunk Content')
        dot.edge('chunk', 'emb', 'Generate Embeddings')
        dot.edge('emb', 'vec', 'Store Vectors')
        dot.edge('vec', 'qdrant', 'Database Operations')
        dot.edge('qdrant', 'vec', 'Results')
        dot.edge('vec', 'emb', 'Confirmation')
        dot.edge('emb', 'chunk', 'Embeddings')
        dot.edge('chunk', 'conn', 'Chunked Data')
        dot.edge('conn', 'api', 'Processed Content')
        dot.edge('api', 'user', 'Response')
        
        return dot
    
    def _create_configuration_graph(self) -> Digraph:
        """Create configuration architecture graph."""
        dot = Digraph(comment='Saathy Configuration')
        dot.attr(rankdir='TB')
        
        # Configuration Sources
        with dot.subgraph(name='cluster_sources') as c:
            c.attr(label='Configuration Sources', style='filled', color='lightblue')
            c.node('env', 'Environment Variables')
            c.node('secrets', 'Secret Files')
            c.node('defaults', 'Default Values')
        
        # Settings Categories
        with dot.subgraph(name='cluster_settings') as c:
            c.attr(label='Settings Categories', style='filled', color='lightgreen')
            c.node('app', 'Application Settings')
            c.node('db', 'Database Settings')
            c.node('api', 'External API Settings')
            c.node('github', 'GitHub Settings')
            c.node('slack', 'Slack Settings')
            c.node('emb', 'Embedding Settings')
            c.node('obs', 'Observability Settings')
            c.node('server', 'Server Settings')
        
        # Configuration Management
        with dot.subgraph(name='cluster_management') as c:
            c.attr(label='Configuration Management', style='filled', color='lightyellow')
            c.node('settings', 'Settings Class')
            c.node('validation', 'Pydantic Validation')
            c.node('secure', 'Secret Management')
        
        # Connections
        dot.edge('env', 'settings')
        dot.edge('secrets', 'settings')
        dot.edge('defaults', 'settings')
        
        dot.edge('settings', 'validation')
        dot.edge('settings', 'secure')
        
        dot.edge('validation', 'app')
        dot.edge('validation', 'db')
        dot.edge('validation', 'api')
        dot.edge('validation', 'github')
        dot.edge('validation', 'slack')
        dot.edge('validation', 'emb')
        dot.edge('validation', 'obs')
        dot.edge('validation', 'server')
        
        return dot
    
    def _create_deployment_graph(self) -> Digraph:
        """Create deployment architecture graph."""
        dot = Digraph(comment='Saathy Deployment')
        dot.attr(rankdir='TB')
        
        # Environments
        with dot.subgraph(name='cluster_dev') as c:
            c.attr(label='Development Environment', style='filled', color='lightblue')
            c.node('dev_compose', 'docker-compose.dev.yml')
            c.node('dev_override', 'docker-compose.override.yml')
        
        with dot.subgraph(name='cluster_prod') as c:
            c.attr(label='Production Environment', style='filled', color='lightgreen')
            c.node('prod_compose', 'docker-compose.prod.yml')
            c.node('nginx', 'Nginx Configuration')
            c.node('ssl', 'SSL Certificates')
        
        with dot.subgraph(name='cluster_test') as c:
            c.attr(label='Testing Environment', style='filled', color='lightyellow')
            c.node('test_compose', 'docker-compose.test.yml')
            c.node('test_scripts', 'Test Scripts')
        
        # Infrastructure Services
        with dot.subgraph(name='cluster_infra') as c:
            c.attr(label='Infrastructure Services', style='filled', color='lightpink')
            c.node('qdrant', 'Qdrant Container')
            c.node('jaeger', 'Jaeger Container')
            c.node('prometheus', 'Prometheus Container')
            c.node('grafana', 'Grafana Container')
        
        # Application Container
        with dot.subgraph(name='cluster_app') as c:
            c.attr(label='Application Container', style='filled', color='lightcyan')
            c.node('saathy', 'Saathy App')
            c.node('uvicorn', 'Uvicorn Server')
            c.node('workers', 'Worker Processes')
        
        # Connections
        dot.edge('dev_compose', 'saathy')
        dot.edge('prod_compose', 'saathy')
        dot.edge('test_compose', 'saathy')
        
        dot.edge('prod_compose', 'nginx')
        dot.edge('nginx', 'ssl')
        
        dot.edge('saathy', 'uvicorn')
        dot.edge('uvicorn', 'workers')
        
        dot.edge('prod_compose', 'qdrant')
        dot.edge('prod_compose', 'jaeger')
        dot.edge('prod_compose', 'prometheus')
        dot.edge('prod_compose', 'grafana')
        
        return dot
    
    def _create_monitoring_graph(self) -> Digraph:
        """Create monitoring and observability architecture graph."""
        dot = Digraph(comment='Saathy Monitoring & Observability')
        dot.attr(rankdir='TB')
        
        # Application Telemetry
        with dot.subgraph(name='cluster_telemetry') as c:
            c.attr(label='Application Telemetry', style='filled', color='lightblue')
            c.node('otel', 'OpenTelemetry')
            c.node('traces', 'Distributed Traces')
            c.node('logs', 'Structured Logging')
            c.node('metrics', 'Application Metrics')
        
        # Infrastructure Monitoring
        with dot.subgraph(name='cluster_monitoring') as c:
            c.attr(label='Infrastructure Monitoring', style='filled', color='lightgreen')
            c.node('prometheus', 'Prometheus')
            c.node('grafana', 'Grafana')
            c.node('alerts', 'Alerting Rules')
        
        # Tracing System
        with dot.subgraph(name='cluster_tracing') as c:
            c.attr(label='Tracing System', style='filled', color='lightyellow')
            c.node('jaeger', 'Jaeger')
            c.node('trace_ui', 'Tracing UI')
            c.node('trace_storage', 'Trace Storage')
        
        # Health Checks
        with dot.subgraph(name='cluster_health') as c:
            c.attr(label='Health Checks', style='filled', color='lightpink')
            c.node('health', 'Health Endpoints')
            c.node('ready', 'Readiness Checks')
            c.node('liveness', 'Liveness Probes')
        
        # Connections
        dot.edge('otel', 'traces')
        dot.edge('otel', 'logs')
        dot.edge('otel', 'metrics')
        
        dot.edge('traces', 'jaeger')
        dot.edge('logs', 'prometheus')
        dot.edge('metrics', 'prometheus')
        
        dot.edge('jaeger', 'trace_ui')
        dot.edge('jaeger', 'trace_storage')
        
        dot.edge('prometheus', 'grafana')
        dot.edge('prometheus', 'alerts')
        
        dot.edge('health', 'ready')
        dot.edge('health', 'liveness')
        
        return dot
    
    def _create_api_endpoints_graph(self) -> Digraph:
        """Create API endpoints architecture graph."""
        dot = Digraph(comment='Saathy API Endpoints')
        dot.attr(rankdir='TB')
        
        # Health & Configuration
        with dot.subgraph(name='cluster_health') as c:
            c.attr(label='Health & Configuration', style='filled', color='lightblue')
            c.node('health', '/healthz')
            c.node('ready', '/readyz')
            c.node('config', '/config')
        
        # GitHub Connector
        with dot.subgraph(name='cluster_github') as c:
            c.attr(label='GitHub Connector', style='filled', color='lightgreen')
            c.node('gh_webhook', '/webhooks/github')
            c.node('gh_status', '/connectors/github/status')
            c.node('gh_sync', '/connectors/github/sync')
        
        # Slack Connector
        with dot.subgraph(name='cluster_slack') as c:
            c.attr(label='Slack Connector', style='filled', color='lightyellow')
            c.node('sl_status', '/connectors/slack/status')
            c.node('sl_start', '/connectors/slack/start')
            c.node('sl_stop', '/connectors/slack/stop')
            c.node('sl_channels', '/connectors/slack/channels')
            c.node('sl_process', '/connectors/slack/process')
        
        # Content Processing
        with dot.subgraph(name='cluster_content') as c:
            c.attr(label='Content Processing', style='filled', color='lightpink')
            c.node('process', '/process')
            c.node('chunk', '/chunk')
            c.node('embed', '/embed')
            c.node('search', '/search')
        
        # Vector Operations
        with dot.subgraph(name='cluster_vector') as c:
            c.attr(label='Vector Operations', style='filled', color='lightcyan')
            c.node('vec_insert', '/vectors/insert')
            c.node('vec_search', '/vectors/search')
            c.node('vec_update', '/vectors/update')
            c.node('vec_delete', '/vectors/delete')
        
        # Connections
        dot.edge('health', 'ready')
        dot.edge('ready', 'config')
        
        dot.edge('gh_webhook', 'gh_status')
        dot.edge('gh_status', 'gh_sync')
        
        dot.edge('sl_status', 'sl_start')
        dot.edge('sl_start', 'sl_stop')
        dot.edge('sl_stop', 'sl_channels')
        dot.edge('sl_channels', 'sl_process')
        
        dot.edge('process', 'chunk')
        dot.edge('chunk', 'embed')
        dot.edge('embed', 'search')
        
        dot.edge('vec_insert', 'vec_search')
        dot.edge('vec_search', 'vec_update')
        dot.edge('vec_update', 'vec_delete')
        
        return dot
    
    def _create_dependencies_graph(self) -> Digraph:
        """Create component dependencies graph."""
        dot = Digraph(comment='Saathy Dependencies')
        dot.attr(rankdir='TB')
        
        # Core Dependencies
        with dot.subgraph(name='cluster_core') as c:
            c.attr(label='Core Dependencies', style='filled', color='lightblue')
            c.node('fastapi', 'FastAPI')
            c.node('pydantic', 'Pydantic')
            c.node('uvicorn', 'Uvicorn')
            c.node('apscheduler', 'APScheduler')
        
        # External Services
        with dot.subgraph(name='cluster_external') as c:
            c.attr(label='External Services', style='filled', color='lightgreen')
            c.node('qdrant', 'Qdrant Client')
            c.node('openai', 'OpenAI')
            c.node('github', 'GitHub API')
            c.node('slack', 'Slack API')
        
        # AI/ML Libraries
        with dot.subgraph(name='cluster_ai') as c:
            c.attr(label='AI/ML Libraries', style='filled', color='lightyellow')
            c.node('sentence_transformers', 'Sentence Transformers')
            c.node('torch', 'PyTorch')
            c.node('transformers', 'Transformers')
        
        # Utilities
        with dot.subgraph(name='cluster_utils') as c:
            c.attr(label='Utilities', style='filled', color='lightpink')
            c.node('logging', 'Logging')
            c.node('asyncio', 'asyncio')
            c.node('typing', 'typing')
            c.node('os', 'os')
        
        # Development Tools
        with dot.subgraph(name='cluster_dev') as c:
            c.attr(label='Development Tools', style='filled', color='lightcyan')
            c.node('poetry', 'Poetry')
            c.node('pre_commit', 'pre-commit')
            c.node('pytest', 'pytest')
            c.node('black', 'black')
        
        # Connections
        dot.edge('fastapi', 'pydantic')
        dot.edge('fastapi', 'uvicorn')
        dot.edge('fastapi', 'apscheduler')
        
        dot.edge('qdrant', 'fastapi')
        dot.edge('openai', 'fastapi')
        dot.edge('github', 'fastapi')
        dot.edge('slack', 'fastapi')
        
        dot.edge('sentence_transformers', 'torch')
        dot.edge('torch', 'transformers')
        
        dot.edge('logging', 'fastapi')
        dot.edge('asyncio', 'fastapi')
        dot.edge('typing', 'fastapi')
        dot.edge('os', 'fastapi')
        
        dot.edge('poetry', 'fastapi')
        dot.edge('pre_commit', 'fastapi')
        dot.edge('pytest', 'fastapi')
        dot.edge('black', 'fastapi')
        
        return dot


def main():
    """Main function to generate all architecture graphs."""
    generator = ArchitectureGraphGenerator()
    generator.generate_all_graphs()


if __name__ == "__main__":
    main()