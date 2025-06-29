# RBAC-Protected Calculator MCP Server

This is a production-ready calculator MCP server with decoupled Azure AD authentication and granular Role-Based Access Control (RBAC) using the official MCP Python SDK.

## Architecture

- **auth_module.py**: Completely decoupled authentication logic with RBAC engine
- **calculator_mcp_server.py**: Original calculator server (unchanged)
- **authenticated_calculator_server.py**: Main application with RBAC integration
- **Backward Compatible**: Can run with or without authentication
- **Tool-Level Authorization**: Each operation requires specific roles

## RBAC Implementation

### Role Hierarchy
```
MCP.Admin (inherits all)
├── calculate_expression (Admin only)
├── MCP.PowerUser (inherits BasicUser)
│   ├── multiply
│   ├── divide
│   └── MCP.BasicUser
│       ├── add
│       └── subtract
```

### Tool Permissions
- **Basic Operations** (`MCP.BasicUser`): `add`, `subtract`
- **Advanced Operations** (`MCP.PowerUser`): `multiply`, `divide` + basic
- **Admin Operations** (`MCP.Admin`): `calculate_expression` + all others

## Azure AD Setup

### 1. Server App Registration
```bash
# Create app registration for MCP server
az ad app create --display-name "Calculator MCP Server" \
  --identifier-uris "api://calculator-mcp-server"

# Add app roles
az ad app update --id <server-app-id> --app-roles @app-roles.json
```

**app-roles.json**:
```json
[
  {
    "allowedMemberTypes": ["Application"],
    "description": "Basic calculator operations",
    "displayName": "MCP Basic User",
    "id": "11111111-1111-1111-1111-111111111111",
    "isEnabled": true,
    "value": "MCP.BasicUser"
  },
  {
    "allowedMemberTypes": ["Application"],
    "description": "Advanced calculator operations",
    "displayName": "MCP Power User",
    "id": "22222222-2222-2222-2222-222222222222",
    "isEnabled": true,
    "value": "MCP.PowerUser"
  },
  {
    "allowedMemberTypes": ["Application"],
    "description": "All calculator operations including expression evaluation",
    "displayName": "MCP Admin",
    "id": "33333333-3333-3333-3333-333333333333",
    "isEnabled": true,
    "value": "MCP.Admin"
  }
]
```

### 2. Client App Registration
```bash
# Create app registration for MCP client
az ad app create --display-name "Calculator MCP Client"

# Add API permissions to server app
az ad app permission add --id <client-app-id> \
  --api <server-app-id> \
  --api-permissions <role-id>=Role

# Grant admin consent
az ad app permission admin-consent --id <client-app-id>
```

### 3. Token Request
```bash
# Get access token with client credentials flow
curl -X POST "https://login.microsoftonline.com/<tenant-id>/oauth2/v2.0/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=<client-app-id>" \
  -d "client_secret=<client-secret>" \
  -d "scope=api://<server-app-id>/.default"
```

## Quick Start

### 1. Setup Environment

```bash
# Copy environment template
cp .env.example .env

# Edit with your Azure AD values
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-server-app-client-id
MCP_SERVER_URL=https://your-server.com:8000
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the Server

```bash
# With RBAC authentication (default)
python authenticated_calculator_server.py

# Without authentication (original mode)
ENABLE_AUTH=false python authenticated_calculator_server.py

# Or use the original server directly
python calculator_mcp_server.py
```

## Endpoints

### Public Endpoints
- `GET /health` - Health check with RBAC status
- `GET /.well-known/oauth-protected-resource` - RFC 9728 metadata with RBAC info

### Protected Endpoints (require Azure AD token with appropriate roles)
- `POST /mcp` - Main MCP endpoint for all tools/resources/prompts
- `GET /auth/info` - Get user's authorization context and accessible tools

## RBAC Authorization Flow

1. **Discovery Phase**:
   - Client requests protected endpoint → 401 with WWW-Authenticate header
   - Client fetches `/.well-known/oauth-protected-resource`
   - Metadata includes RBAC information and required roles per tool

2. **Authorization Phase**:
   - Client performs OAuth 2.1 client credentials flow with Azure AD
   - Azure AD issues access token with assigned app roles in `roles` claim

3. **Request Processing**:
   - Client includes Bearer token in Authorization header
   - Server validates token and extracts roles
   - Request-level authorization check (user has valid token)

4. **Tool Execution**:
   - When specific tool is invoked, tool-level authorization check
   - RBAC engine verifies user roles against tool requirements
   - Role inheritance applied (Admin inherits PowerUser + BasicUser)
   - Tool executed if authorized, 403 Forbidden if not

## Testing RBAC

### Check Authorization Context
```bash
# Get user's accessible tools and permissions
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/auth/info
```

### Test Tool Access
```bash
# This will work for BasicUser+ roles
curl -X POST "http://localhost:8000/mcp" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"method": "tools/call", "params": {"name": "add", "arguments": {"a": 5, "b": 3}}}'

# This requires PowerUser+ roles  
curl -X POST "http://localhost:8000/mcp" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"method": "tools/call", "params": {"name": "multiply", "arguments": {"a": 7, "b": 6}}}'

# This requires Admin role
curl -X POST "http://localhost:8000/mcp" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"method": "tools/call", "params": {"name": "calculate_expression", "arguments": {"expression": "2 + 3 * 4"}}}'
```

## Docker Deployment

```bash
# Build image
docker build -t calculator-mcp-rbac .

# Run locally
docker run -p 8000:8000 \
  -e AZURE_TENANT_ID=your-tenant-id \
  -e AZURE_CLIENT_ID=your-client-id \
  -e MCP_SERVER_URL=http://localhost:8000 \
  calculator-mcp-rbac

# Deploy to Azure Container Instance
az container create \
  --name calculator-mcp-rbac \
  --resource-group mygroup \
  --image calculator-mcp-rbac \
  --environment-variables \
    AZURE_TENANT_ID=$TENANT_ID \
    AZURE_CLIENT_ID=$CLIENT_ID \
    MCP_SERVER_URL=https://calculator.eastus.azurecontainer.io:8000 \
  --ports 8000
```

## Configuration Options

- `ENABLE_AUTH=true/false` - Enable/disable authentication
- `AZURE_TENANT_ID` - Azure AD tenant ID
- `AZURE_CLIENT_ID` - Azure AD server app client ID  
- `MCP_SERVER_URL` - Public URL of the server
- `REQUIRED_SCOPES` - Comma-separated list of required scopes for request-level auth
- `TOOL_PERMISSIONS` - Custom tool permission mappings (optional)
- `MCP_HOST/MCP_PORT` - Server bind address

## RBAC Features

- ✅ **Tool-Level Authorization**: Each MCP tool has specific role requirements
- ✅ **Role Hierarchy**: Higher roles inherit lower role permissions automatically
- ✅ **Decoupled Architecture**: RBAC logic completely separated from business logic
- ✅ **Azure AD Integration**: Uses app roles from Azure AD token claims
- ✅ **RFC 9728 Enhanced**: Protected Resource Metadata includes RBAC information
- ✅ **Granular Error Messages**: Specific error messages indicating required roles
- ✅ **Authorization Context**: API to check user's accessible tools and permissions
- ✅ **Dynamic Configuration**: Runtime configuration of tool permissions via environment
- ✅ **Comprehensive Logging**: Detailed authorization decision logging
- ✅ **Production Ready**: Health checks, CORS, error handling with RBAC status

## Security Considerations

### Token Validation
- JWT signature validation against Azure AD JWKS
- Audience validation (must match server app client ID)
- Expiration and not-before time validation
- Issuer validation (Azure AD tenant)

### Authorization
- Request-level: Valid token with minimum required scopes
- Tool-level: Specific role requirements per operation
- Role inheritance: Prevents privilege escalation
- Comprehensive error handling without information leakage

### Monitoring
- All authorization decisions are logged
- Health endpoint includes RBAC status
- Authorization context API for debugging access issues
- Detailed error messages for troubleshooting

## Troubleshooting

### Common Issues

1. **403 Forbidden on tool execution**:
   - Check token contains required roles in `roles` claim
   - Verify app registration has correct app roles defined
   - Ensure admin consent granted for client app

2. **401 Unauthorized**:
   - Verify token audience matches server app client ID
   - Check token expiration and validity
   - Ensure proper Authorization header format

3. **Tool not found in RBAC policies**:
   - Check tool name matches exactly (case-sensitive)
   - Verify RBAC engine initialization
   - Review custom TOOL_PERMISSIONS configuration

### Debug Endpoints

```bash
# Check server health and RBAC status
curl http://localhost:8000/health

# Get RBAC metadata
curl http://localhost:8000/.well-known/oauth-protected-resource

# Check user authorization context
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/auth/info
```

---

**Note**: This is a reference implementation demonstrating RBAC integration with MCP servers. For production use, consider additional security measures such as rate limiting, input validation, and comprehensive audit logging.
