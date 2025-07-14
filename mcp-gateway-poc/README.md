# MCP Gateway - Streamable HTTP Protocol Only

## 🌊 **Streamable HTTP Protocol Implementation**

This is a specialized version of the MCP Gateway that **exclusively** supports the **Streamable HTTP protocol** for connecting to backend MCP servers. **SSE (Server-Sent Events) transport has been deprecated as of June 2025** in favor of the more robust Streamable HTTP protocol using the `/mcp` endpoint.

## 🎯 **Key Features**

### **Protocol Specification**
- **Protocol**: Streamable HTTP using `/mcp` endpoint
- **Transport**: HTTP/HTTPS only  
- **Streaming**: Real-time bidirectional communication
- **Standards**: Compliant with MCP 2025-06-18 specification
- **Note**: SSE deprecated as of June 2025

### **Core Capabilities**
- ✅ **Streamable HTTP Only**: Clean implementation using `/mcp` endpoint
- ✅ **HTTP Transport**: Standard HTTP/HTTPS for efficient communication
- ✅ **Tool Aggregation**: Unified namespace for tools across multiple HTTP servers
- ✅ **Real-time Health Monitoring**: Continuous connection health checks
- ✅ **Enterprise Security**: API key authentication and request logging
- ✅ **REST Management API**: Full CRUD operations for server management

## 🏗️ **Architecture**

```
┌─────────────────┐    HTTP/JSON-RPC    ┌─────────────────┐
│   MCP Client    │ ───────────────────► │  MCP Gateway    │
│                 │                      │   :8001/mcp     │
└─────────────────┘                      └─────────────────┘
                                                   │
                                         Streamable HTTP
                                                   │
                    ┌──────────────────────────────┼──────────────────────────────┐
                    │                              │                              │
                    ▼                              ▼                              ▼
            ┌─────────────────┐           ┌─────────────────┐           ┌─────────────────┐
            │ Backend Server  │           │ Backend Server  │           │ Backend Server  │
            │ :8000/mcp       │           │ :8080/mcp       │           │ :8081/mcp       │
            │ Namespace: crm  │           │ Namespace: api  │           │ Namespace: demo │
            └─────────────────┘           └─────────────────┘           └─────────────────┘
```

### **Protocol Flow**
1. **Gateway Startup**: Connects to all configured HTTP servers at their `/mcp` endpoints
2. **Capability Discovery**: Discovers tools/prompts/resources via Streamable HTTP
3. **Client Connection**: External clients connect to gateway's `/mcp` endpoint
4. **Tool Routing**: Requests routed to appropriate backend via Streamable HTTP
5. **Real-time Monitoring**: Continuous health checks and reconnection

## 🚀 **Quick Start**

### **1. Install Dependencies**
```bash
cd backend
pip install -r requirements.txt
```

### **2. Configure Streamable HTTP Servers**
```bash
# Create environment configuration  
cp .env.template .env

# Configure your Streamable HTTP servers (connects to /mcp endpoint)
export MCP_SERVERS="demo:http://localhost:8000:demo,api:http://localhost:8080:api"
export GATEWAY_PORT="8001"  # Use different port if your server is on 8000
```

### **3. Start Gateway**
```bash
python run_gateway.py
```

### **4. Test Streamable HTTP Connection**
```bash
# Test MCP endpoint
curl -H "Authorization: Bearer gateway-dev-key-123" \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' \
     http://localhost:8001/mcp

# Check protocol info
curl http://localhost:8001/api/protocol
```

## ⚙️ **Configuration**

### **Environment Variables**

#### **Required - Server Configuration**
```bash
# Streamable HTTP servers (required) - Gateway connects to /mcp endpoint
MCP_SERVERS="name1:http://server1:port:namespace1,name2:https://server2:port:namespace2"

# Example - Your MCP server runs on 127.0.0.1:8000:
MCP_SERVERS="myserver:http://127.0.0.1:8000:myns"
GATEWAY_PORT="8001"  # Different port to avoid conflict
```

#### **Optional - Gateway Settings**
```bash
# Gateway server
GATEWAY_HOST="0.0.0.0"
GATEWAY_PORT="8001"

# Authentication
GATEWAY_API_KEY="your-secure-api-key"
UI_TOKEN="your-ui-token"

# HTTP timeouts
HTTP_CONNECT_TIMEOUT="30"
HTTP_REQUEST_TIMEOUT="60"
HTTP_STREAM_TIMEOUT="300"

# Monitoring
HEALTH_CHECK_INTERVAL="30"
MAX_RETRIES="3"
```

## 🔧 **Backend Server Requirements**

### **Streamable HTTP Server Specification**
Your backend MCP servers must support the following:

#### **1. HTTP Endpoint Structure**
```
http://your-server:port/          # Base endpoint
http://your-server:port/mcp       # MCP endpoint (not /sse - deprecated)
```

#### **2. MCP Protocol Support**
- JSON-RPC 2.0 over HTTP
- Streamable HTTP for real-time responses  
- Standard MCP methods: `initialize`, `tools/list`, `tools/call`, etc.

#### **3. Example Server Implementation**
```python
# Basic Streamable HTTP MCP server
from fastapi import FastAPI

app = FastAPI()

@app.post("/mcp")
async def mcp_endpoint(request):
    # Handle MCP JSON-RPC over Streamable HTTP
    # Implementation details...
    pass
```

## 📊 **Management Interface**

### **REST API Endpoints**
```bash
# Gateway status and protocol info
GET /api/status
GET /api/protocol

# Server management
GET /api/servers              # List all Streamable HTTP servers
POST /api/servers             # Add new Streamable HTTP server
DELETE /api/servers/{id}      # Remove server

# Tool catalog
GET /api/tools                # Get aggregated tools from all servers
POST /api/tools/execute       # Execute tool for testing

# Activity monitoring
GET /api/activity             # Get activity log
```

### **Add Streamable HTTP Server**
```bash
curl -H "Authorization: Bearer ui-dev-token-456" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "new-server",
       "endpoint": "https://new-server.com:8080",
       "namespace": "newns"
     }' \
     http://localhost:8001/api/servers
```

## 🔍 **Monitoring & Debugging**

### **Health Checks**
The gateway performs continuous health monitoring:
- **HTTP Connectivity**: Regular ping tests to backend `/mcp` endpoints
- **Stream Status**: Monitor Streamable HTTP connection health
- **Tool Availability**: Verify tool discovery and execution
- **Auto-reconnection**: Automatic reconnection on failures

### **Activity Logging**
All operations are logged with structured data:
```json
{
  "timestamp": "2025-07-14T10:30:00Z",
  "event_type": "tool_called",
  "details": "Calling tool crm.get_customer via Streamable HTTP",
  "server_id": "crm-server",
  "tool_name": "crm.get_customer",
  "transport": "streamable-http",
  "success": true
}
```

### **Protocol Information**
Check supported protocol details:
```bash
curl http://localhost:8001/api/protocol
```

Response:
```json
{
  "protocol": "streamable-http",
  "transport": "http",
  "description": "Streamable HTTP protocol (SSE deprecated as of June 2025)",
  "supported_schemes": ["http", "https"],
  "mcp_version": "2025-06-18",
  "endpoint_path": "/mcp"
}
```

## 🚦 **Troubleshooting**

### **Common Issues**

#### **Connection Failures**
```bash
# Check if backend server supports /mcp endpoint
curl -H "Content-Type: application/json" \
     -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
     http://your-server:port/mcp

# NOT /sse (deprecated) - use /mcp
```

#### **Protocol Validation**
```bash
# Verify gateway protocol mode
curl http://localhost:8001/api/protocol

# Expected response should show:
# "protocol": "streamable-http"
# "endpoint_path": "/mcp"
```

#### **Port Conflicts**
```bash
# If your MCP server runs on port 8000, configure gateway on different port:
export GATEWAY_PORT="8001"
export MCP_SERVERS="myserver:http://127.0.0.1:8000:myns"
```

### **Debug Logging**
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python run_gateway.py
```

## 🎯 **For Your Use Case**

Since your MCP server runs on `127.0.0.1:8000`, configure like this:

```bash
# .env file
GATEWAY_PORT="8001"  # Different port to avoid conflict
MCP_SERVERS="myserver:http://127.0.0.1:8000:myns"
```

**Result:**
- Gateway runs on `http://localhost:8001`
- Gateway connects to your server at `http://127.0.0.1:8000/mcp`
- External clients connect to gateway at `http://localhost:8001/mcp`

## 📈 **Benefits of Streamable HTTP**

### **Modern Protocol**
- **SSE Deprecated**: Using latest MCP specification (June 2025)
- **HTTP Native**: Standard web protocols and tooling
- **Scalable**: Easy horizontal scaling and load balancing
- **Debuggable**: Standard HTTP debugging tools work

### **Enterprise Ready**
- **HTTPS Support**: Secure transport for production
- **Load Balancing**: Standard HTTP load balancer compatibility
- **Monitoring**: HTTP metrics and health check integration
- **Security**: Standard TLS/SSL encryption support

This Streamable HTTP implementation provides a robust, modern, and enterprise-ready foundation for MCP server aggregation using the latest protocol specifications.