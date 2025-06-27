# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables for Azure Container Instance
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV MCP_TRANSPORT=streamable-http
ENV MCP_PORT=8000
ENV MCP_HOST=0.0.0.0
ENV ENABLE_AUTH=true

# Azure AD Environment Variables (to be set during deployment)
ENV AZURE_TENANT_ID=""
ENV AZURE_CLIENT_ID=""

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better Docker layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY calculator_mcp_server.py .
COPY auth_module.py .
COPY authenticated_calculator_server.py .

# Create a non-root user for security
RUN useradd --create-home --shell /bin/bash mcp && \
    chown -R mcp:mcp /app
USER mcp

# Expose the port for Azure Container Instance
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the authenticated MCP server
CMD ["python", "authenticated_calculator_server.py"]
