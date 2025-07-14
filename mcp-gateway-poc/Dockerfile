FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ ./backend/
COPY run_gateway.py ./
COPY README.md ./

# Create non-root user
RUN useradd --create-home --shell /bin/bash gateway
RUN chown -R gateway:gateway /app
USER gateway

# Expose port (changed to 8001 to avoid conflicts with MCP servers on 8000)
EXPOSE 8001

# Health check (updated for new port)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/api/health || exit 1

# Set environment variables
ENV PYTHONPATH=/app/backend
ENV GATEWAY_HOST=0.0.0.0
ENV GATEWAY_PORT=8001

# Add label for protocol info
LABEL description="MCP Gateway - Streamable HTTP Protocol Only (SSE deprecated June 2025)"
LABEL protocol="streamable-http"
LABEL transport="http"
LABEL mcp_version="2025-06-18"

# Run the application
CMD ["python", "run_gateway.py"]