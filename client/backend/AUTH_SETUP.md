# MCP Client Authentication Setup Guide

## Overview
Your MCP client now supports tool-level authentication using Azure AD bearer tokens. This allows your client to authenticate with MCP servers that require role-based access control.

## Quick Setup

### 1. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your Azure AD details:

```bash
# MCP Authentication
MCP_CLIENT_ID=your-client-app-id
MCP_CLIENT_SECRET=your-client-secret
MCP_TENANT_ID=your-tenant-id
MCP_SERVER_SCOPE=api://your-server-app-id/.default
```

### 2. Update Server Configuration
In `mcp_config.json`, enable auth for servers that require it:

```json
{
  "servers": [
    {
      "name": "calculator",
      "url": "http://localhost:8000/mcp",
      "description": "Calculator with mathematical operations",
      "auth": {
        "enabled": true,
        "scope": "api://your-server-app-id/.default"
      }
    }
  ]
}
```

### 3. Test Authentication
Start your client and check the health endpoint:

```bash
curl http://localhost:8001/health
```

Look for:
- `"auth_configured": true` - Your Azure AD credentials are loaded
- `"auth_enabled_servers": ["calculator"]` - Shows which servers have auth enabled

## How It Works

1. **Auth Decision Logic**:
   - `"enabled": true` → Client MUST acquire token, fails if token acquisition fails
   - `"enabled": false` → Client skips authentication for this server
   - No auth config → Client skips authentication for this server

2. **Token Acquisition**: Client automatically gets Azure AD tokens using client credentials flow
3. **Token Caching**: Tokens are cached and refreshed automatically before expiration
4. **Automatic Injection**: Bearer tokens are added to tool calls for authenticated servers
5. **Error Handling**: Tool calls fail fast if auth is required but token cannot be acquired

## Testing

1. **Auth Disabled**: Set `"enabled": false` - tools work without tokens
2. **Auth Enabled with Valid Creds**: Set `"enabled": true` with valid Azure AD config - tools work with tokens
3. **Auth Enabled with Invalid Creds**: Set `"enabled": true` with missing/invalid Azure AD config - tools fail immediately
4. **No Auth Config**: Omit auth section entirely - tools work without tokens

## Configuration Examples

```json
{
  "servers": [
    {
      "name": "secure-server",
      "url": "http://localhost:8000/mcp",
      "auth": {
        "enabled": true,
        "scope": "api://server-app-id/.default"
      }
    },
    {
      "name": "public-server", 
      "url": "http://localhost:8001/mcp",
      "auth": {
        "enabled": false
      }
    },
    {
      "name": "legacy-server",
      "url": "http://localhost:8002/mcp"
      // No auth config = no authentication
    }
  ]
}
```

## Changes Made

- ✅ `auth_manager.py` - New token management module
- ✅ `main.py` - Replaced AuthenticatedMCPClient wrapper with `create_authenticated_client()` function using proper FastMCP 2.0 transport configuration
- ✅ `chat_handler.py` - Updated to use authenticated client
- ✅ `mcp_config.json` - Added auth configuration for calculator server
- ✅ `.env.example` - Added authentication environment variables
- ✅ Health endpoint now shows authentication status

## Architecture

```
Client Request → create_authenticated_client() → Token Manager → Azure AD
                                               ↓
            StreamableHttpTransport with Bearer Token → MCP Server → Role Validation
```

The implementation uses FastMCP 2.0's correct approach of configuring authentication at the transport level, not by modifying session internals.

## How Authentication Works

1. **Client Creation**: For each tool call, a new authenticated client is created using `create_authenticated_client()`
2. **Transport Configuration**: If auth is enabled, a `StreamableHttpTransport` is created with `Authorization: Bearer <token>` header
3. **Token Management**: Tokens are acquired via Azure AD client credentials flow and cached automatically
4. **Header Injection**: Headers are set at transport creation time, following FastMCP 2.0 best practices

The minimal integration preserves all existing functionality while adding authentication as an optional layer.
