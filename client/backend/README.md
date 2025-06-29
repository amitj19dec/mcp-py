# Enhanced MCP Client Backend with Authentication Support

Python backend using FastMCP 2.0 with Azure AD authentication support that loads all MCP server details on startup and provides Azure OpenAI chat integration for dynamic tool calling with Role-Based Access Control (RBAC) awareness.

## 🔐 Authentication Features

- **Azure AD Integration**: OAuth 2.1 client credentials flow using MSAL
- **RBAC Awareness**: Filters tools based on user permissions
- **Token Management**: Automatic token caching and refresh
- **Discovery Support**: RFC 9728 Protected Resource Metadata discovery
- **Permission Checking**: Pre-execution authorization validation
- **Multiple Auth Types**: Azure AD, static bearer tokens, or no authentication

## Quick Start

### 1. Install dependencies:
```bash
pip install -r requirements.txt
```

### 2. Configure environment variables in `.env` file:
```bash
# Copy the example and fill in your credentials
cp .env.example .env
# Edit .env with your Azure OpenAI and Azure AD details
```

**Required Environment Variables:**
```bash
# Azure OpenAI (for chat functionality)
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here

# Azure AD (for MCP server authentication)
AZURE_TENANT_ID=your-tenant-id-here
AZURE_CLIENT_ID=your-client-id-here
AZURE_CLIENT_SECRET=your-client-secret-here
```

### 3. Configure MCP servers with authentication in `mcp_config.json`:
```json
{
  "servers": [
    {
      "name": "calculator",
      "url": "http://localhost:8000/mcp",
      "description": "RBAC-protected calculator with mathematical operations",
      "auth": {
        "type": "azure_ad",
        "tenant_id": "${AZURE_TENANT_ID}",
        "client_id": "${AZURE_CLIENT_ID}",
        "client_secret": "${AZURE_CLIENT_SECRET}",
        "scope": "api://calculator-mcp-server/.default"
      }
    },
    {
      "name": "public-server",
      "url": "http://localhost:8002/mcp",
      "description": "Public server without authentication",
      "auth": {
        "type": "none"
      }
    }
  ]
}
```

### 4. Start the backend:
```bash
python main.py
```

Backend runs on `http://localhost:8001`

## 🚀 What It Does

### On Startup:
- ✅ Connects to all configured MCP servers with authentication
- ✅ Discovers server authentication requirements via RFC 9728
- ✅ Acquires Azure AD tokens using client credentials flow
- ✅ Loads **all tools, resources, and prompts** with permission filtering
- ✅ Caches accessible tools based on user roles
- ✅ Initializes Azure OpenAI chat handler
- ✅ Shows detailed auth status in logs

### Enhanced API Endpoints:

| Endpoint | Description |
|----------|-------------|
| `GET /` | Summary including authentication status |
| `POST /chat` | **RBAC-aware chat with AI** (only uses accessible tools) |
| `GET /chat/status` | Check chat functionality with auth info |
| `GET /auth/status` | Authentication status for all servers |
| `POST /auth/refresh/{server}` | Refresh tokens for specific server |
| `GET /auth/context/{server}` | Get detailed auth context |
| `GET /servers` | All server details with auth information |
| `GET /tools` | All accessible tools from all servers |
| `GET /tools/accessible/{server}` | Tools accessible to current user |
| `POST /tools/call` | Execute tool with auth and permission checks |
| `GET /config` | Current MCP configuration (secrets masked) |
| `POST /config/reload` | Reload config and refresh authentication |
| `GET /health` | Health check with authentication status |

### Enhanced Chat Example:
```json
{
  "response": "I'll calculate that for you. 15 × 23 = 345, and 345 + 45 = 390.",
  "tool_calls_made": [
    {
      "server": "calculator",
      "tool": "multiply", 
      "arguments": {"a": 15, "b": 23},
      "result": "345",
      "authenticated": true
    },
    {
      "server": "calculator",
      "tool": "add",
      "arguments": {"a": 345, "b": 45}, 
      "result": "390",
      "authenticated": true
    }
  ],
  "reasoning": "Used 2 authenticated tool(s)",
  "permission_errors": []
}
```

### Authentication Status Example:
```json
{
  "message": "Enhanced MCP Client Backend with Authentication",
  "servers_loaded": 2,
  "auth_enabled_servers": 1,
  "auth_server_names": ["calculator"],
  "accessible_tools": 3,
  "total_tools": 5,
  "chat_available": true
}
```

## 🔑 Authentication Types

### 1. Azure AD (Recommended)
```json
{
  "auth": {
    "type": "azure_ad",
    "tenant_id": "${AZURE_TENANT_ID}",
    "client_id": "${AZURE_CLIENT_ID}",
    "client_secret": "${AZURE_CLIENT_SECRET}",
    "scope": "api://server-app-id/.default"
  }
}
```

**Features:**
- OAuth 2.1 client credentials flow
- Automatic token refresh
- JWKS-based token validation
- Role-based authorization

### 2. Static Bearer Token
```json
{
  "auth": {
    "type": "bearer_token",
    "static_token": "your-bearer-token-here"
  }
}
```

**Use Cases:**
- Development and testing
- Simple API key authentication
- Non-Azure AD environments

### 3. No Authentication
```json
{
  "auth": {
    "type": "none"
  }
}
```

**Use Cases:**
- Public MCP servers
- Local development
- Internal trusted networks

## 🛡️ RBAC Features

### Permission-Aware Tool Discovery
- **Automatic Filtering**: Only shows tools user can access
- **Role Hierarchy**: Supports inherited permissions
- **Real-Time Checking**: Validates permissions before tool execution
- **Graceful Degradation**: Handles permission errors elegantly

### Chat Integration with RBAC
- **Smart Tool Selection**: AI only uses accessible tools
- **Permission Errors**: Clear feedback when access denied
- **Alternative Suggestions**: Suggests available tools when possible
- **Context Awareness**: Adapts responses based on user permissions

### Authorization Context API
```bash
# Get user's authorization context
curl http://localhost:8001/auth/context/calculator
```

Response:
```json
{
  "server_name": "calculator",
  "auth_context": {
    "user_roles": ["MCP.PowerUser"],
    "effective_roles": ["MCP.PowerUser", "MCP.BasicUser"],
    "accessible_tools": ["add", "subtract", "multiply", "divide"]
  },
  "auth_type": "azure_ad",
  "scope": "api://calculator-mcp-server/.default"
}
```

## 🧪 Testing Authentication

### Check Authentication Status
```bash
# Get auth status for all servers
curl http://localhost:8001/auth/status

# Get specific server auth context
curl http://localhost:8001/auth/context/calculator
```

### Test Tool Access with Different Roles
```bash
# This works for BasicUser+ roles
curl -X POST http://localhost:8001/tools/call \
  -H "Content-Type: application/json" \
  -d '{"server_name": "calculator", "tool_name": "add", "arguments": {"a": 5, "b": 3}}'

# This requires PowerUser+ roles  
curl -X POST http://localhost:8001/tools/call \
  -H "Content-Type: application/json" \
  -d '{"server_name": "calculator", "tool_name": "multiply", "arguments": {"a": 7, "b": 6}}'

# This requires Admin role
curl -X POST http://localhost:8001/tools/call \
  -H "Content-Type: application/json" \
  -d '{"server_name": "calculator", "tool_name": "calculate_expression", "arguments": {"expression": "2 + 3 * 4"}}'
```

### Test RBAC-Aware Chat
```bash
# Chat that automatically filters tools by permissions
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Calculate 15 times 23 plus 45"}'
```

## 🔄 Token Management

### Automatic Token Refresh
- **Background Refresh**: Tokens refreshed before expiration
- **Failure Recovery**: Automatic retry with new tokens
- **Cache Management**: Efficient token caching per server

### Manual Token Refresh
```bash
# Refresh tokens for specific server
curl -X POST http://localhost:8001/auth/refresh/calculator

# Reload entire configuration with fresh tokens
curl -X POST http://localhost:8001/config/reload
```

## 🏗️ Architecture

### Authentication Flow
1. **Startup**: Load config → Discover auth requirements → Acquire tokens
2. **Tool Discovery**: Get capabilities → Filter by permissions → Cache accessible tools
3. **Chat Request**: User message → Filter available tools → Execute with auth → Return response
4. **Token Management**: Monitor expiration → Refresh proactively → Handle failures

### Key Components
- **`auth_client.py`**: Azure AD integration using MSAL
- **`enhanced_mcp_client.py`**: FastMCP wrapper with auth support
- **`main.py`**: FastAPI backend with RBAC-aware endpoints
- **`chat_handler.py`**: Enhanced chat with permission filtering

## 🚨 Error Handling

### Authentication Errors
- **401 Unauthorized**: Token invalid or expired
- **403 Forbidden**: Permission denied for specific tool
- **Configuration Errors**: Missing or invalid auth settings

### Permission Errors in Chat
```json
{
  "response": "I tried to use the advanced calculation tool, but you don't have permission. I can help with basic addition and subtraction instead.",
  "tool_calls_made": [],
  "permission_errors": ["Permission denied for calculator.calculate_expression"],
  "reasoning": "1 permission error(s)"
}
```

## 📊 Monitoring and Debugging

### Health Check with Auth Status
```bash
curl http://localhost:8001/health
```

Response:
```json
{
  "status": "healthy",
  "servers_loaded": 2,
  "healthy_servers": 1,
  "auth_enabled_servers": 1,
  "auth_status": {
    "calculator": true,
    "public-server": false
  },
  "chat_available": true
}
```

### Debug Authentication Issues
```bash
# Check overall auth status
curl http://localhost:8001/auth/status

# Get detailed auth context for specific server
curl http://localhost:8001/auth/context/calculator

# Test specific tool permissions
curl http://localhost:8001/tools/accessible/calculator
```

### Common Issues and Solutions

#### 1. Token Acquisition Fails
```
Error: Failed to acquire token: AADSTS70002: The request body must contain the following parameter: 'client_secret'
```
**Solution**: Check `AZURE_CLIENT_SECRET` in environment variables

#### 2. Permission Denied
```
Error: Permission denied for tool 'calculate_expression'. Required roles: ['MCP.Admin']
```
**Solution**: Verify user has required roles in Azure AD app registration

#### 3. Server Discovery Fails
```
Warning: Failed to discover auth requirements for http://localhost:8000/mcp
```
**Solution**: Ensure MCP server is running and accessible

## 🎯 Demo Scenarios

### Scenario 1: Role-Based Tool Access
1. **BasicUser**: Can only use `add` and `subtract`
2. **PowerUser**: Can use `add`, `subtract`, `multiply`, `divide`
3. **Admin**: Can use all tools including `calculate_expression`

### Scenario 2: Multi-Server Environment
1. **Public Server**: No authentication required
2. **Protected Server**: Azure AD authentication with RBAC
3. **Chat Integration**: Seamlessly uses tools from both servers

### Scenario 3: Permission Error Handling
1. **User requests advanced operation**
2. **System checks permissions**
3. **Graceful denial with alternatives**

## 🔮 Future Enhancements

### Planned Features
- **User Impersonation**: Support for user-delegated permissions
- **Token Introspection**: Enhanced token validation
- **Audit Logging**: Comprehensive access logging
- **Dynamic Permissions**: Runtime permission updates
- **Multi-Tenant Support**: Tenant-specific configurations

### Integration Possibilities
- **Microsoft Graph**: Access to M365 data
- **Azure Key Vault**: Secure credential storage
- **Azure Monitor**: Enhanced observability
- **Conditional Access**: Policy-based access control

## 📚 References

- [Model Context Protocol Specification](https://modelcontextprotocol.io/specification/)
- [Azure AD Authentication Documentation](https://docs.microsoft.com/en-us/azure/active-directory/)
- [MSAL Python Documentation](https://msal-python.readthedocs.io/)
- [RFC 9728: OAuth 2.0 Protected Resource Metadata](https://datatracker.ietf.org/doc/rfc9728/)
- [FastMCP Documentation](https://fastmcp.io/)

---

**Note**: This is an enhanced reference implementation demonstrating Azure AD authentication integration with MCP clients. For production use, consider additional security measures such as certificate-based authentication, enhanced monitoring, and comprehensive audit logging.
