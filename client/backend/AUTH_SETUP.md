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

1. **Token Acquisition**: Client automatically gets Azure AD tokens using client credentials flow
2. **Token Caching**: Tokens are cached and refreshed automatically before expiration
3. **Automatic Injection**: Bearer tokens are added to tool calls for authenticated servers
4. **Fallback**: Servers without auth config work normally without tokens

## Testing

1. **With Auth Disabled**: Set `"enabled": false` in server auth config - tools work without tokens
2. **With Auth Enabled**: Set `"enabled": true` - client will acquire and send bearer tokens
3. **Invalid Credentials**: Tools will fail with 401/403 errors if token acquisition fails

## Changes Made

- ✅ `auth_manager.py` - New token management module
- ✅ `main.py` - Added authentication support and AuthenticatedMCPClient wrapper
- ✅ `chat_handler.py` - Updated to use authenticated client
- ✅ `mcp_config.json` - Added auth configuration for calculator server
- ✅ `.env.example` - Added authentication environment variables
- ✅ Health endpoint now shows authentication status

## Architecture

```
Client Request → AuthenticatedMCPClient → Token Manager → Azure AD
                                        ↓
                Tool Call + Bearer Token → MCP Server → Role Validation
```

The minimal integration preserves all existing functionality while adding authentication as an optional layer.
