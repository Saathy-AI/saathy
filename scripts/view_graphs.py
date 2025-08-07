#!/usr/bin/env python3
"""
Interactive graph viewer for Saathy architecture graphs.

This script creates a simple web interface to view the generated architecture graphs.
"""

import os
import sys
from pathlib import Path
from typing import List, Dict
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading
import time

# Add the src directory to the path to import saathy modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class GraphViewer:
    """Web-based graph viewer for Saathy architecture graphs."""
    
    def __init__(self, graphs_dir: str = "docs/graphs", port: int = 8080):
        self.graphs_dir = Path(graphs_dir)
        self.port = port
        self.server = None
        self.server_thread = None
        
    def get_available_graphs(self) -> List[Dict[str, str]]:
        """Get list of available graph files."""
        graphs = []
        
        if not self.graphs_dir.exists():
            return graphs
            
        for png_file in self.graphs_dir.glob("*.png"):
            name = png_file.stem.replace("_", " ").title()
            graphs.append({
                "name": name,
                "filename": png_file.name,
                "path": str(png_file.relative_to(self.graphs_dir))
            })
        
        return sorted(graphs, key=lambda x: x["name"])
    
    def create_html_page(self) -> str:
        """Create HTML page for viewing graphs."""
        graphs = self.get_available_graphs()
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Saathy Architecture Graphs</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
        }}
        .header p {{
            margin: 10px 0 0 0;
            opacity: 0.9;
            font-size: 1.1em;
        }}
        .content {{
            padding: 30px;
        }}
        .graph-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}
        .graph-card {{
            border: 1px solid #e1e5e9;
            border-radius: 8px;
            overflow: hidden;
            transition: transform 0.2s, box-shadow 0.2s;
            background: white;
        }}
        .graph-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
        }}
        .graph-card h3 {{
            margin: 0;
            padding: 15px 20px;
            background: #f8f9fa;
            border-bottom: 1px solid #e1e5e9;
            font-size: 1.1em;
            color: #333;
        }}
        .graph-card img {{
            width: 100%;
            height: 200px;
            object-fit: cover;
            display: block;
        }}
        .graph-card .description {{
            padding: 15px 20px;
            color: #666;
            font-size: 0.9em;
            line-height: 1.4;
        }}
        .no-graphs {{
            text-align: center;
            padding: 40px;
            color: #666;
        }}
        .instructions {{
            background: #e3f2fd;
            border: 1px solid #2196f3;
            border-radius: 6px;
            padding: 15px;
            margin-bottom: 20px;
        }}
        .instructions h3 {{
            margin: 0 0 10px 0;
            color: #1976d2;
        }}
        .instructions p {{
            margin: 0;
            color: #1565c0;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: #666;
            border-top: 1px solid #e1e5e9;
            background: #f8f9fa;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏗️ Saathy Architecture Graphs</h1>
            <p>Comprehensive visual representations of the Saathy AI copilot architecture</p>
        </div>
        
        <div class="content">
"""
        
        if not graphs:
            html += """
            <div class="no-graphs">
                <h2>📊 No Graphs Found</h2>
                <p>No architecture graphs have been generated yet.</p>
                <p>Run the graph generation script first:</p>
                <code>./scripts/generate_graphs.sh</code>
            </div>
            """
        else:
            html += """
            <div class="instructions">
                <h3>📋 Instructions</h3>
                <p>Click on any graph to view it in full size. Use browser back button to return to this page.</p>
            </div>
            
            <div class="graph-grid">
            """
            
            for graph in graphs:
                description = self._get_graph_description(graph["name"])
                html += f"""
                <div class="graph-card">
                    <h3>{graph["name"]}</h3>
                    <a href="{graph["path"]}" target="_blank">
                        <img src="{graph["path"]}" alt="{graph["name"]}" loading="lazy">
                    </a>
                    <div class="description">
                        {description}
                    </div>
                </div>
                """
            
            html += """
            </div>
            """
        
        html += """
        </div>
        
        <div class="footer">
            <p>Generated by Saathy Architecture Graph Generator</p>
            <p>View source code and documentation in the project repository</p>
        </div>
    </div>
</body>
</html>
        """
        
        return html
    
    def _get_graph_description(self, graph_name: str) -> str:
        """Get description for a specific graph."""
        descriptions = {
            "System Overview": "High-level system architecture showing external systems, core components, and infrastructure.",
            "Application Layer": "Detailed view of the FastAPI application structure and core services.",
            "Connector Framework": "Extensible connector system with GitHub and Slack integrations.",
            "Chunking System": "Modular chunking strategies for different content types.",
            "Vector Database": "Vector storage implementation with Qdrant integration.",
            "Embedding Service": "Embedding model management and preprocessing pipeline.",
            "Data Flow": "Sequence diagram showing data flow through the system.",
            "Configuration": "Configuration management and settings architecture.",
            "Deployment": "Containerized deployment with Docker Compose.",
            "Monitoring": "Observability stack with telemetry and monitoring.",
            "Api Endpoints": "Complete API endpoint mapping and relationships.",
            "Dependencies": "Component dependency relationships and libraries."
        }
        
        return descriptions.get(graph_name, "Architecture graph showing system components and relationships.")
    
    def start_server(self):
        """Start the HTTP server."""
        os.chdir(self.graphs_dir.parent)  # Change to docs directory
        
        class CustomHandler(SimpleHTTPRequestHandler):
            def end_headers(self):
                self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                self.send_header('Pragma', 'no-cache')
                self.send_header('Expires', '0')
                super().end_headers()
        
        self.server = HTTPServer(('localhost', self.port), CustomHandler)
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()
        
        print(f"🌐 Server started at http://localhost:{self.port}")
    
    def stop_server(self):
        """Stop the HTTP server."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            print("🛑 Server stopped")
    
    def create_index_html(self):
        """Create index.html file for the graphs directory."""
        html_content = self.create_html_page()
        index_path = self.graphs_dir / "index.html"
        
        with open(index_path, 'w') as f:
            f.write(html_content)
        
        print(f"📄 Created index.html at {index_path}")
        return index_path
    
    def view_graphs(self, open_browser: bool = True):
        """View graphs in web browser."""
        if not self.graphs_dir.exists():
            print("❌ Graphs directory not found. Please generate graphs first:")
            print("   ./scripts/generate_graphs.sh")
            return
        
        # Create index.html
        index_path = self.create_index_html()
        
        # Start server
        self.start_server()
        
        # Wait a moment for server to start
        time.sleep(1)
        
        # Open browser
        if open_browser:
            url = f"http://localhost:{self.port}/graphs/"
            print(f"🌐 Opening browser to {url}")
            webbrowser.open(url)
        
        try:
            print("🔄 Server running. Press Ctrl+C to stop.")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 Shutting down...")
        finally:
            self.stop_server()


def main():
    """Main function to view graphs."""
    import argparse
    
    parser = argparse.ArgumentParser(description="View Saathy architecture graphs")
    parser.add_argument("--port", type=int, default=8080, help="Port for web server (default: 8080)")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser automatically")
    parser.add_argument("--graphs-dir", default="docs/graphs", help="Directory containing graphs (default: docs/graphs)")
    
    args = parser.parse_args()
    
    viewer = GraphViewer(graphs_dir=args.graphs_dir, port=args.port)
    viewer.view_graphs(open_browser=not args.no_browser)


if __name__ == "__main__":
    main()