# Multi-stage Dockerfile for Saathy FastAPI service

# Builder stage
FROM python:3.11-slim AS builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.11-slim AS runtime

# Install runtime dependencies (include bash for start.sh)
RUN apt-get update && apt-get install -y \
    curl bash \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash app

# Set working directory
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY src/ ./src/

# Copy startup script
COPY start.sh ./start.sh

# Set Python path to include the src directory
ENV PYTHONPATH=/app/src:$PYTHONPATH

# Normalize line endings (handle Windows CRLF) and make executable
RUN sed -i 's/\r$//' start.sh && chmod +x start.sh

# Change ownership to app user
RUN chown -R app:app /app

# Switch to non-root user
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

# Run the application using the startup script
CMD ["./start.sh"]
