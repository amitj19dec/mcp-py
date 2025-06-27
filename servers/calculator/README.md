# Authenticated Calculator MCP Server

This is a production-ready calculator MCP server with decoupled Azure AD authentication using the official MCP Python SDK.

## Architecture

- **auth_module.py**: Completely decoupled authentication logic
- **calculator_mcp_server.py**: Original calculator server (unchanged)
- **authenticated_calculator_server.py**: Main application that combines both
- **Backward Compatible**: Can run with or without authentication

## Quick Start

### 1. Setup Environment

```bash
# Copy environment template
cp .env.example .env

# Edit with your Azure AD values
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
MCP_SERVER_URL=https://your-server.com:8000
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the Server

```bash
# With authentication (default)
python authenticated_calculator_server.py

# Without authentication (original mode)
ENABLE_AUTH=false python authenticated_calculator_server.py

# Or use the original server directly
python calculator_mcp_server.py
```

## Endpoints

### Public Endpoints
- `GET /health` - Health check
- `GET /.well-known/oauth-protected-resource` - RFC 9728 metadata

### Protected Endpoints (require Azure AD token)
- `POST /mcp` - Main MCP endpoint for all tools/resources/prompts

## Authentication Flow

1. Client requests protected endpoint → 401 with WWW-Authenticate header
2. Client fetches `/.well-known/oauth-protected-resource`
3. Metadata points to Azure AD authorization server
4. Client performs OAuth 2.1 flow with Azure AD
5. Client includes Bearer token in subsequent requests

## Docker Deployment

```bash
# Build image
docker build -t calculator-mcp-auth .

# Run locally
docker run -p 8000:8000 \
  -e AZURE_TENANT_ID=your-tenant-id \
  -e AZURE_CLIENT_ID=your-client-id \
  -e MCP_SERVER_URL=http://localhost:8000 \
  calculator-mcp-auth

# Deploy to Azure Container Instance
az container create \
  --name calculator-mcp \
  --resource-group mygroup \
  --image calculator-mcp-auth \
  --environment-variables \
    AZURE_TENANT_ID=$TENANT_ID \
    AZURE_CLIENT_ID=$CLIENT_ID \
    MCP_SERVER_URL=https://calculator.eastus.azurecontainer.io:8000 \
  --ports 8000
```

## Configuration Options

- `ENABLE_AUTH=true/false` - Enable/disable authentication
- `AZURE_TENANT_ID` - Azure AD tenant ID
- `AZURE_CLIENT_ID` - Azure AD application client ID  
- `MCP_SERVER_URL` - Public URL of the server
- `REQUIRED_SCOPES` - Comma-separated list of required scopes
- `MCP_HOST/MCP_PORT` - Server bind address

## Features

- ✅ **Decoupled Architecture**: Auth and business logic completely separated
- ✅ **Official SDK**: Uses `mcp[cli]>=1.9.4` with proper `TokenVerifier`
- ✅ **RFC 9728 Compliant**: Protected Resource Metadata endpoint
- ✅ **Azure AD Integration**: JWKS validation, scope checking
- ✅ **Backward Compatible**: Can run with or without auth
- ✅ **Production Ready**: Health checks, CORS, error handling
- ✅ **Container Ready**: Docker support with health checks
