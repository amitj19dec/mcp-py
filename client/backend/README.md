# MCP Client Backend with Chat Integration

Python backend using FastMCP 2.0 that loads all MCP server details on startup and provides Azure OpenAI chat integration for dynamic tool calling.

## Quick Start

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Configure Azure OpenAI in `.env` file:**
```bash
# Copy the example and fill in your credentials
cp .env.example .env
# Edit .env with your Azure OpenAI details
```

3. **Configure MCP servers in `/Users/amitj/Documents/code2.0/mcp-py/client/mcp_config.json`:**
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

4. **Start the backend:**
```bash
python main.py
```

Backend runs on `http://localhost:8001`

## What It Does

### On Startup:
- ✅ Connects to all configured MCP servers
- ✅ Loads **all tools, resources, and prompts**
- ✅ Stores everything in memory for fast access
- ✅ Initializes Azure OpenAI chat handler
- ✅ Shows summary in logs

### API Endpoints:

| Endpoint | Description |
|----------|-------------|
| `GET /` | Summary of loaded servers and capabilities |
| `POST /chat` | **Chat with AI that can use MCP tools** |
| `GET /chat/status` | Check if chat functionality is available |
| `GET /servers` | All server details (tools, resources, prompts) |
| `GET /servers/{name}` | Specific server details |
| `GET /tools` | All tools from all servers |
| `GET /resources` | All resources from all servers |
| `GET /prompts` | All prompts from all servers |
| `POST /tools/call` | Execute a tool directly |
| `GET /config` | Current MCP configuration from JSON file |
| `POST /config/reload` | Reload configuration from file and reconnect |
| `GET /health` | Health check |

### Chat Example:
```json
{
  "response": "I'll calculate that for you. 15 × 23 = 345, and 345 + 45 = 390.",
  "tool_calls_made": [
    {
      "server": "calculator",
      "tool": "multiply", 
      "arguments": {"a": 15, "b": 23},
      "result": "345"
    },
    {
      "server": "calculator",
      "tool": "add",
      "arguments": {"a": 345, "b": 45}, 
      "result": "390"
    }
  ],
  "reasoning": "Used 2 tool(s)"
}
```

### Server Summary Example:
```json
{
  "message": "MCP Client Backend with Chat - Demo",
  "servers_loaded": 1,
  "total_tools": 5,
  "total_resources": 1,
  "total_prompts": 1,
  "server_names": ["calculator"],
  "chat_available": true
}
```

## Demo Points for Leadership

1. **"AI chat interface that automatically uses our tools"**
   - User: "Calculate 15 * 23 + 45"
   - AI automatically uses calculator tools and gives result

2. **"One interface, unlimited capabilities"**
   - Same chat can do math, check weather, manage files
   - Just add MCP servers to JSON config

3. **"No frontend changes needed"**
   - Add new AI capabilities by configuring servers
   - Chat interface automatically discovers new tools

4. **"Intelligent tool selection"**
   - AI decides which tools to use based on user request
   - Combines multiple tools for complex tasks

## Chat Testing

```bash
# Test chat endpoint
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Calculate 15 times 23 plus 45"}'

# Check chat status
curl http://localhost:8001/chat/status

# Test direct tool call
curl -X POST http://localhost:8001/tools/call \
  -H "Content-Type: application/json" \
  -d '{"server_name": "calculator", "tool_name": "add", "arguments": {"a": 5, "b": 3}}'
```

## Demo Flow

1. **Show Overview**: `GET http://localhost:8001/`
2. **Demo Chat**: 
   - "Calculate 25 * 16"
   - "What's 100 divided by 8?"
   - "Calculate (15 + 25) * 2"
3. **Show Tool Discovery**: `GET http://localhost:8001/tools`
4. **Add New Server**: Edit JSON config, reload
5. **Show Scaling**: Same chat now has new capabilities

## Directory Structure
```
backend/
├── main.py              # Main application with chat
├── chat_handler.py      # Azure OpenAI integration
├── requirements.txt     # Dependencies
├── .env.example        # Environment template
├── .env               # Your Azure OpenAI credentials
└── README.md          # This file
```

## For Frontend Integration

The chat endpoint accepts:
```json
{"message": "Your question here"}
```

Returns:
```json
{
  "response": "AI response with tool results",
  "tool_calls_made": [...],
  "reasoning": "Explanation of tools used"
}
```

Perfect for building a React chat interface that just sends messages and displays responses!
