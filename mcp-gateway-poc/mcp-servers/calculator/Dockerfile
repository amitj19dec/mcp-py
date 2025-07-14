# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables for Streamable HTTP protocol
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV MCP_TRANSPORT=streamable-http
ENV MCP_PORT=8000
ENV MCP_HOST=0.0.0.0

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better Docker layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY calculator.py .

# Create a non-root user for security
RUN useradd --create-home --shell /bin/bash mcp && \
    chown -R mcp:mcp /app
USER mcp

# Expose the port for Streamable HTTP protocol
EXPOSE 8000

# Add health check for /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Add labels for documentation
LABEL description="Calculator MCP Server - Streamable HTTP Protocol Only"
LABEL protocol="streamable-http"
LABEL transport="http"
LABEL mcp_version="2025-06-18"
LABEL mcp_endpoint="/mcp"
LABEL note="SSE deprecated as of June 2025"

# Run the MCP server with Streamable HTTP transport
CMD ["python", "calculator.py"]