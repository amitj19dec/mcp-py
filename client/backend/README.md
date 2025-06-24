# MCP Client Backend - Demo

Simple Python backend using FastMCP 2.0 that loads all MCP server details on startup.

## Quick Start

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Configure MCP servers in `client/mcp_config.json`:**
```json
{
  "servers": [
    {
      "name": "calculator",
      "url": "http://localhost:8000/mcp",
      "description": "Calculator with mathematical operations"
    },
    {
      "name": "file-system",
      "url": "http://localhost:8002/mcp",
      "description": "File system operations"
    }
  ]
}
```

3. **Start the backend:**
```bash
python main.py
```

Backend runs on `http://localhost:8001`

## What It Does

### On Startup:
- ✅ Connects to all configured MCP servers
- ✅ Loads **all tools, resources, and prompts**
- ✅ Stores everything in memory for fast access
- ✅ Shows summary in logs

### API Endpoints:

| Endpoint | Description |
|----------|-------------|
| `GET /` | Summary of loaded servers and capabilities |
| `GET /servers` | All server details (tools, resources, prompts) |
| `GET /servers/{name}` | Specific server details |
| `GET /tools` | All tools from all servers |
| `GET /resources` | All resources from all servers |
| `GET /prompts` | All prompts from all servers |
| `POST /tools/call` | Execute a tool |
| `GET /config` | Current MCP configuration from JSON file |
| `POST /config/reload` | Reload configuration from file and reconnect |
| `GET /health` | Health check |

### Example Response:
```json
{
  "servers_loaded": 1,
  "total_tools": 14,
  "total_resources": 1,
  "total_prompts": 0,
  "server_names": ["calculator"]
}
```
