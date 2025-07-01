# Calculator MCP Server with Tool-Level Authorization

A basic calculator MCP (Model Context Protocol) server that provides arithmetic operations with JWT-based role authorization following the latest MCP specification (June 2025).

## Features

- **Role-Based Access Control**: Tool-level authorization using Azure AD app roles
- **Basic Operations**: Add, subtract, multiply, divide
- **Expression Evaluation**: Calculate mathematical expressions  
- **MCP Compliant**: Implements latest MCP specification with Streamable HTTP transport
- **Containerized**: Ready for deployment in Azure Container Instances
- **Demo Mode**: Can run without authentication for testing

## Authorization Model

### App Roles
- **MCP.User**: Basic calculator user
  - Access: `add`, `subtract` operations only
- **MCP.Admin**: Administrator
  - Access: All operations (`add`, `subtract`, `multiply`, `divide`, `calculate_expression`)

### Tools Available by Role

| Tool | MCP.User | MCP.Admin |
|------|----------|-----------|
| add(a, b) | ✅ | ✅ |
| subtract(a, b) | ✅ | ✅ |
| multiply(a, b) | ❌ | ✅ |
| divide(a, b) | ❌ | ✅ |
| calculate_expression(expr) | ❌ | ✅ |

## Quick Start

### Prerequisites
- Python 3.10 or higher
- Azure AD tenant (for authentication)
- MCP client that supports Bearer token authentication

### Local Development

1. **Clone and setup**:
```bash
cd /path/to/calculator
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Configure environment**:
```bash
cp .env.example .env
# Edit .env with your Azure AD configuration
```

3. **Run in demo mode (no auth)**:
```bash
ENABLE_AUTH=false python calculator_mcp_server.py
```

4. **Run with authentication**:
```bash
ENABLE_AUTH=true python calculator_mcp_server.py
```

### Azure Container Instance Deployment

1. **Build and push to Azure Container Registry**:
```bash
az acr build --registry myregistry --image calculator-mcp:latest .
```

2. **Deploy to Azure Container Instance**:
```bash
az container create \
  --resource-group myResourceGroup \
  --name calculator-mcp \
  --image myregistry.azurecr.io/calculator-mcp:latest \
  --ports 8000 \
  --environment-variables \
    MCP_TRANSPORT=streamable-http \
    MCP_PORT=8000 \
    ENABLE_AUTH=true \
    AZURE_TENANT_ID=your-tenant-id \
    AZURE_CLIENT_ID=your-client-id \
  --cpu 1 --memory 1
```

## Authentication Setup

### Azure AD Configuration

1. **Create Server App Registration**:
   - Register new application for MCP server
   - Define app roles: `MCP.User`, `MCP.Admin`
   - Note the Application (client) ID

2. **Create Client App Registration**:
   - Register new application for MCP client
   - Add API permissions pointing to server app
   - Assign app roles and grant admin consent

3. **Token Request**:
```bash
curl -X POST https://login.microsoftonline.com/{tenant-id}/oauth2/v2.0/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id={client-id}&client_secret={client-secret}&scope=api://{server-client-id}/.default&grant_type=client_credentials"
```

### MCP Client Configuration

For MCP clients, configure with Bearer token authentication:

```json
{
  "mcpServers": {
    "calculator": {
      "transport": "streamable-http",
      "url": "https://your-aci-instance.azurecontainer.io/mcp",
      "headers": {
        "Authorization": "Bearer your-jwt-token"
      }
    }
  }
}
```

## API Examples

### With MCP.User Role
```javascript
// Allowed operations
add(5, 3)        // ✅ Returns: {"operation": "addition", "result": 8, ...}
subtract(10, 4)  // ✅ Returns: {"operation": "subtraction", "result": 6, ...}

// Denied operations  
multiply(7, 6)   // ❌ AuthorizationError: Insufficient permissions
```

### With MCP.Admin Role
```javascript
// All operations allowed
add(5, 3)                          // ✅
subtract(10, 4)                    // ✅  
multiply(7, 6)                     // ✅
divide(15, 3)                      // ✅
calculate_expression("2 + 3 * 4")  // ✅ Returns: {"result": 14, ...}
```

## Resources

- **calculator://info** - Get server capabilities based on user permissions

## Prompts

- **math_helper** - Interactive math assistance prompt (customized per user role)

## Security Features

- **JWT Token Validation**: Validates Azure AD issued tokens
- **Role-Based Authorization**: Tool access based on app roles
- **Audience Validation**: Ensures tokens are intended for this server
- **Request Context Isolation**: Secure per-request authorization context
- **Comprehensive Logging**: Audit trail for access attempts

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ENABLE_AUTH` | No | `false` | Enable/disable authentication |
| `AZURE_TENANT_ID` | Yes* | - | Azure AD tenant ID |
| `AZURE_CLIENT_ID` | Yes* | - | Server app registration client ID |
| `MCP_HOST` | No | `0.0.0.0` | Server host |
| `MCP_PORT` | No | `8000` | Server port |
| `LOG_LEVEL` | No | `INFO` | Logging level |

*Required only when `ENABLE_AUTH=true`

## Error Responses

### Authorization Errors
```json
{
  "error": "Authorization Failed",
  "message": "Insufficient permissions. Required roles: ['MCP.Admin']", 
  "required_roles": ["MCP.Admin"],
  "help": "Contact your administrator to request the required roles for this operation."
}
```

### Invalid Token
```json
{
  "error": "Authorization Failed",
  "message": "Missing or invalid authorization header",
  "required_roles": [],
  "help": "Contact your administrator to request the required roles for this operation."
}
```

## Development Notes

- **Demo Mode**: Set `ENABLE_AUTH=false` for testing without Azure AD
- **Token Caching**: JWKS keys are cached for performance
- **Context Variables**: Request context is isolated per request
- **Error Handling**: Comprehensive error handling with user-friendly messages
- **Logging**: Detailed logging for debugging and audit trails

## Compliance

This implementation follows:
- MCP Specification (June 2025)
- OAuth 2.1 with PKCE
- RFC 8707 (Resource Indicators)  
- RFC 9728 (Protected Resource Metadata)
- Azure AD App Roles standard