# 🚀 Complete Demo Setup Instructions

## Prerequisites

1. **Calculator MCP server running** on `http://localhost:8000/mcp`
2. **Python backend dependencies** installed
3. **Azure OpenAI credentials** (optional, for chat)

## Quick Start

### 1. Start the Backend
```bash
cd /Users/amitj/Documents/code2.0/mcp-py/client/backend

# Install dependencies (if not done already)
pip install -r requirements.txt

# Configure Azure OpenAI (optional)
# Edit .env file with your credentials

# Start backend
python main.py
```
**Backend runs on http://localhost:8001**

### 2. Start the Frontend
```bash
cd /Users/amitj/Documents/code2.0/mcp-py/client/frontend

# Install dependencies
npm install

# Start frontend
npm start
```
**Frontend runs on http://localhost:3000**

## Demo Flow

1. **Open** http://localhost:3000
2. **Dashboard** - Shows connected servers and stats
3. **MCP Servers** - View calculator server
4. **Server Details** - See 5 discovered tools
5. **All Tools** - Browse and test tools
6. **Chat Interface** - AI automatically uses tools

## Troubleshooting

### Backend Connection Issues
- Ensure backend is running on port 8001
- Check calculator server is running on port 8000
- Verify no port conflicts

### Chat Not Working
- Chat requires Azure OpenAI configuration
- Edit `/backend/.env` with credentials
- Restart backend after adding credentials

### Frontend Proxy Errors
- Ensure backend is started first
- Frontend proxies all API calls to backend
- Check browser console for error details

## Testing the Demo

### Basic Functionality
```bash
# Test backend directly
curl http://localhost:8001/

# Test chat status
curl http://localhost:8001/chat/status

# Test tool execution
curl -X POST http://localhost:8001/tools/call \
  -H "Content-Type: application/json" \
  -d '{"server_name": "calculator", "tool_name": "add", "arguments": {"a": 5, "b": 3}}'
```

### Chat Testing (requires Azure OpenAI)
```bash
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Calculate 15 times 23"}'
```

## Demo Script

1. **"This is our MCP Control Center"** → Dashboard
2. **"We're connected to AI services"** → MCP Servers
3. **"It discovered tools automatically"** → Server Details
4. **"Users don't need to learn interfaces"** → Chat
5. **"Watch AI use tools automatically"** → Live demo
6. **"Adding new services is just configuration"** → Show JSON config

Perfect for demonstrating the power of MCP to leadership! 🎯
