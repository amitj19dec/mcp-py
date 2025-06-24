# MCP Client Frontend

Simple React frontend for the MCP Powered Chat demo.

## Quick Start

1. **Install dependencies:**
```bash
npm install
```

2. **Start the development server:**
```bash
npm start
```

Frontend runs on `http://localhost:3000` and proxies API calls to the backend on `http://localhost:8001`.

## Features

### 🏠 Dashboard
- Overview of connected servers and available tools
- Quick stats display
- Navigation to all sections

### 🖥️ Server Management
- View all connected MCP servers
- Server status indicators
- Drill down into individual server details
- Reload servers configuration

### 🔧 Tool Browser
- Browse all tools from all servers
- Search and filter tools
- Test tools with interactive dialogs
- Parameter validation and execution

### 💬 Chat Interface
- Simple chat UI like ChatGPT/Claude
- AI automatically selects and uses MCP tools
- Shows which tools were used
- Real-time responses

### 📁 Resources & Prompts
- Browse available resources and prompts
- Organized by server
- Clean, searchable interface

## UI Design

- **Clean white background** - Professional appearance
- **Simple components** - Easy to understand and modify
- **Minimal dialogs** - No complex overlays or animations
- **Responsive grid layout** - Works on different screen sizes
- **Clear navigation** - Breadcrumbs and back buttons

## Demo Flow

1. **Start at Dashboard** - Show overview stats
2. **Browse Servers** - Click to see connected services
3. **Explore Tools** - Show auto-discovered capabilities
4. **Test Tools** - Interactive tool execution
5. **Chat Interface** - AI that uses tools automatically
6. **Add New Server** - Live configuration reload

## Components

- `Dashboard.js` - Main overview page
- `ServersList.js` - All connected servers
- `ServerDetails.js` - Individual server info
- `AllTools.js` - Tool browser with search
- `ChatInterface.js` - AI chat with tool integration
- `ToolDialog.js` - Interactive tool testing popup

## API Integration

All components fetch data from the backend API:
- `GET /api/` - Dashboard summary
- `GET /api/servers` - Server list
- `GET /api/tools` - All tools
- `POST /api/chat` - Chat with AI
- `POST /api/tools/call` - Direct tool execution

Perfect for demonstrating MCP capabilities to leadership!
