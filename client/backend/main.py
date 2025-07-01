#!/usr/bin/env python3
"""
MCP Client Backend with Chat Integration
Loads all MCP server details and provides chat interface with dynamic tool calling.
"""

import asyncio
import logging
import json
import os
from typing import Dict, List, Any, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# FastMCP 2.0 imports
from fastmcp import Client

# Authentication
from auth_manager import TokenManager

# Chat functionality
from chat_handler import ChatHandler, ChatMessage, ChatResponse

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Data models
class MCPServerConfig(BaseModel):
    name: str
    url: str
    description: str = ""
    auth: Optional[Dict[str, Any]] = None

class ToolInfo(BaseModel):
    name: str
    description: str
    title: Optional[str] = None
    input_schema: Dict[str, Any] = {}
    annotations: Optional[Dict[str, Any]] = None  # Allow None

class ResourceInfo(BaseModel):
    uri: str
    name: str
    description: str = ""
    mime_type: str = ""

class PromptInfo(BaseModel):
    name: str
    description: str = ""
    arguments: List[Dict[str, Any]] = []

class ServerDetails(BaseModel):
    name: str
    description: str
    status: str
    tools: List[ToolInfo] = []
    resources: List[ResourceInfo] = []
    prompts: List[PromptInfo] = []

class ToolCallRequest(BaseModel):
    server_name: str
    tool_name: str
    arguments: Dict[str, Any] = {}

class ToolResult(BaseModel):
    success: bool
    result: Any = None
    error: Optional[str] = None

# Global storage for loaded server details
server_details: Dict[str, ServerDetails] = {}
mcp_clients: Dict[str, Client] = {}
chat_handler: Optional[ChatHandler] = None
token_manager = TokenManager()
server_auth_config: Dict[str, Dict] = {}

# Configuration file path
CONFIG_FILE_PATH = "/Users/amitj/Documents/code2.0/mcp-py/client/mcp_config.json"

# Authentication-aware MCP client wrapper
class AuthenticatedMCPClient:
    def __init__(self, base_client, server_name: str):
        self.base_client = base_client
        self.server_name = server_name
    
    async def __aenter__(self):
        self.session = await self.base_client.__aenter__()
        return self
    
    async def __aexit__(self, *args):
        return await self.base_client.__aexit__(*args)
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]):
        # Get token if auth is enabled for this server
        token = None
        if self.server_name in server_auth_config:
            auth_config = server_auth_config[self.server_name]
            if auth_config.get('enabled'):
                scope = auth_config.get('scope')
                if scope:
                    token = await token_manager.get_token(scope)
                    logger.info(f"🔐 Using token for {self.server_name}.{tool_name}")
        
        # Make the call with token if available
        if token:
            # Add authorization header to the session
            if hasattr(self.session, '_client') and hasattr(self.session._client, 'headers'):
                self.session._client.headers['Authorization'] = f'Bearer {token}'
        
        return await self.session.call_tool(tool_name, arguments)
    
    def __getattr__(self, name):
        return getattr(self.session, name)

def initialize_chat_handler():
    """Initialize Azure OpenAI chat handler."""
    global chat_handler
    
    try:
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4")
        
        if not azure_endpoint or not api_key:
            logger.warning("⚠️ Azure OpenAI credentials not found in environment. Chat functionality disabled.")
            logger.info("💡 Create a .env file with AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY")
            return
        
        chat_handler = ChatHandler(
            azure_endpoint=azure_endpoint,
            api_key=api_key,
            api_version=api_version,
            deployment_name=deployment_name
        )
        logger.info("✅ Chat handler initialized successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize chat handler: {e}")
        chat_handler = None

def load_mcp_config() -> List[MCPServerConfig]:
    """Load MCP server configuration from JSON file."""
    try:
        if not os.path.exists(CONFIG_FILE_PATH):
            logger.error(f"Config file not found: {CONFIG_FILE_PATH}")
            return []
        
        with open(CONFIG_FILE_PATH, 'r') as f:
            config_data = json.load(f)
        
        servers = []
        for server_config in config_data.get('servers', []):
            config = MCPServerConfig(
                name=server_config['name'],
                url=server_config['url'],
                description=server_config.get('description', ''),
                auth=server_config.get('auth')
            )
            servers.append(config)
            
            # Store auth config globally
            if config.auth:
                server_auth_config[config.name] = config.auth
        
        logger.info(f"📄 Loaded {len(servers)} server configs from {CONFIG_FILE_PATH}")
        return servers
        
    except Exception as e:
        logger.error(f"Failed to load config from {CONFIG_FILE_PATH}: {e}")
        return []

async def load_server_details(config: MCPServerConfig) -> ServerDetails:
    """Load complete server details - tools, resources, prompts."""
    try:
        logger.info(f"Loading details for {config.name}...")
        
        # Store auth config
        if config.auth:
            server_auth_config[config.name] = config.auth
        
        # Connect to MCP server using FastMCP 2.0 pattern
        client = Client(config.url)
        
        # Store client for later use
        mcp_clients[config.name] = client
        
        # Get tools using FastMCP 2.0 context manager
        tools = []
        resources = []
        prompts = []
        
        async with client as session:
            try:
                tools_response = await session.list_tools()
                
                # Handle different response formats
                if hasattr(tools_response, 'tools'):
                    tools_list = tools_response.tools
                elif isinstance(tools_response, list):
                    tools_list = tools_response
                else:
                    tools_list = []
                    
                for tool in tools_list:
                    tools.append(ToolInfo(
                        name=tool.name,
                        description=tool.description or "",
                        title=getattr(tool, 'title', tool.name),
                        input_schema=tool.inputSchema or {},
                        annotations=getattr(tool, 'annotations', None) or {}  # Handle None
                    ))
            except Exception as e:
                logger.warning(f"Could not load tools from {config.name}: {e}")
            
            # Get resources
            try:
                resources_response = await session.list_resources()
                # Handle different response formats
                if hasattr(resources_response, 'resources'):
                    resources_list = resources_response.resources
                elif isinstance(resources_response, list):
                    resources_list = resources_response
                else:
                    resources_list = []
                    
                for resource in resources_list:
                    resources.append(ResourceInfo(
                        uri=str(resource.uri),  # Convert to string
                        name=resource.name or str(resource.uri),
                        description=resource.description or "",
                        mime_type=resource.mimeType or ""
                    ))
            except Exception as e:
                logger.warning(f"Could not load resources from {config.name}: {e}")
            
            # Get prompts
            try:
                prompts_response = await session.list_prompts()
                # Handle different response formats
                if hasattr(prompts_response, 'prompts'):
                    prompts_list = prompts_response.prompts
                elif isinstance(prompts_response, list):
                    prompts_list = prompts_response
                else:
                    prompts_list = []
                    
                for prompt in prompts_list:
                    prompts.append(PromptInfo(
                        name=prompt.name,
                        description=prompt.description or "",
                        arguments=prompt.arguments or []
                    ))
            except Exception as e:
                logger.warning(f"Could not load prompts from {config.name}: {e}")
        
        details = ServerDetails(
            name=config.name,
            description=config.description,
            status="connected",
            tools=tools,
            resources=resources,
            prompts=prompts
        )
        
        logger.info(f"✅ Loaded {config.name}: {len(tools)} tools, {len(resources)} resources, {len(prompts)} prompts")
        return details
        
    except Exception as e:
        logger.error(f"❌ Failed to load {config.name}: {e}")
        return ServerDetails(
            name=config.name,
            description=config.description,
            status="error",
            tools=[],
            resources=[],
            prompts=[]
        )

async def load_all_servers():
    """Load details from all configured MCP servers."""
    logger.info("🚀 Loading all MCP server details...")
    
    # Load configuration from JSON file
    mcp_servers = load_mcp_config()
    
    if not mcp_servers:
        logger.warning("No MCP servers configured!")
        return
    
    for config in mcp_servers:
        details = await load_server_details(config)
        server_details[config.name] = details
    
    # Summary
    total_tools = sum(len(details.tools) for details in server_details.values())
    total_resources = sum(len(details.resources) for details in server_details.values())
    total_prompts = sum(len(details.prompts) for details in server_details.values())
    
    logger.info(f"📊 Summary: {len(server_details)} servers, {total_tools} tools, {total_resources} resources, {total_prompts} prompts")
    
    # Initialize chat handler after loading servers
    initialize_chat_handler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load all server details on startup."""
    # Startup
    await load_all_servers()
    
    yield
    
    # Shutdown
    logger.info("🧹 Cleaning up connections...")
    for client in mcp_clients.values():
        try:
            # FastMCP 2.0 clients handle cleanup automatically
            pass
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")

# Create FastAPI app
app = FastAPI(
    title="MCP Client Backend with Chat - Demo",
    description="MCP backend with Azure OpenAI chat integration for dynamic tool calling",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint with summary."""
    total_tools = sum(len(details.tools) for details in server_details.values())
    total_resources = sum(len(details.resources) for details in server_details.values())
    total_prompts = sum(len(details.prompts) for details in server_details.values())
    
    return {
        "message": "MCP Client Backend with Chat - Demo",
        "servers_loaded": len(server_details),
        "total_tools": total_tools,
        "total_resources": total_resources,
        "total_prompts": total_prompts,
        "server_names": list(server_details.keys()),
        "chat_available": chat_handler is not None
    }

# === CHAT ENDPOINTS ===

@app.post("/chat", response_model=ChatResponse)
async def chat_with_llm(request: ChatMessage):
    """Chat with LLM that can dynamically call MCP tools."""
    if not chat_handler:
        raise HTTPException(
            status_code=503, 
            detail="Chat functionality not available. Please check Azure OpenAI configuration."
        )
    
    try:
        # Get all available tools in the format needed for LLM
        all_tools = []
        for server_name, details in server_details.items():
            for tool in details.tools:
                tool_data = tool.dict()
                tool_data["server"] = server_name
                all_tools.append(tool_data)
        
        logger.info(f"🤖 Processing chat with {len(all_tools)} available tools")
        
        # Process chat with available tools
        response = await chat_handler.chat_with_tools(
            message=request.message,
            available_tools=all_tools,
            mcp_clients=mcp_clients
        )
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Chat processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")

@app.get("/chat/status")
async def chat_status():
    """Check if chat functionality is available."""
    return {
        "chat_available": chat_handler is not None,
        "azure_openai_configured": bool(os.getenv("AZURE_OPENAI_ENDPOINT") and os.getenv("AZURE_OPENAI_API_KEY")),
        "deployment_name": os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4"),
        "tools_available": sum(len(details.tools) for details in server_details.values())
    }

# === SERVER MANAGEMENT ENDPOINTS ===

@app.get("/servers", response_model=List[ServerDetails])
async def get_all_servers():
    """Get all loaded server details (tools, resources, prompts)."""
    return list(server_details.values())

@app.get("/servers/{server_name}", response_model=ServerDetails)
async def get_server_details(server_name: str):
    """Get specific server details."""
    if server_name not in server_details:
        raise HTTPException(404, f"Server {server_name} not found")
    
    return server_details[server_name]

@app.get("/tools")
async def get_all_tools():
    """Get all tools from all servers."""
    all_tools = []
    for server_name, details in server_details.items():
        for tool in details.tools:
            tool_data = tool.dict()
            tool_data["server"] = server_name
            all_tools.append(tool_data)
    
    return {"tools": all_tools, "total": len(all_tools)}

@app.get("/resources")
async def get_all_resources():
    """Get all resources from all servers."""
    all_resources = []
    for server_name, details in server_details.items():
        for resource in details.resources:
            resource_data = resource.dict()
            resource_data["server"] = server_name
            all_resources.append(resource_data)
    
    return {"resources": all_resources, "total": len(all_resources)}

@app.get("/prompts")
async def get_all_prompts():
    """Get all prompts from all servers."""
    all_prompts = []
    for server_name, details in server_details.items():
        for prompt in details.prompts:
            prompt_data = prompt.dict()
            prompt_data["server"] = server_name
            all_prompts.append(prompt_data)
    
    return {"prompts": all_prompts, "total": len(all_prompts)}

@app.post("/tools/call", response_model=ToolResult)
async def call_tool(request: ToolCallRequest):
    """Execute a tool on the specified server."""
    if request.server_name not in mcp_clients:
        raise HTTPException(404, f"Server {request.server_name} not connected")
    
    try:
        client = mcp_clients[request.server_name]
        auth_client = AuthenticatedMCPClient(client, request.server_name)
        
        # Use authenticated client for tool calls
        async with auth_client as session:
            result = await session.call_tool(request.tool_name, request.arguments)
            
            logger.info(f"✅ Tool call: {request.server_name}.{request.tool_name}")
            return ToolResult(success=True, result=str(result))
        
    except Exception as e:
        logger.error(f"❌ Tool call failed: {e}")
        return ToolResult(success=False, error=str(e))

# === CONFIGURATION ENDPOINTS ===

@app.get("/config")
async def get_config():
    """Get current MCP configuration."""
    try:
        mcp_servers = load_mcp_config()
        return {
            "config_file": CONFIG_FILE_PATH,
            "servers": [server.dict() for server in mcp_servers]
        }
    except Exception as e:
        raise HTTPException(500, f"Error loading config: {str(e)}")

@app.post("/config/reload")
async def reload_config():
    """Reload configuration from file and reconnect to servers."""
    global server_details, mcp_clients, chat_handler
    
    logger.info("🔄 Reloading configuration from file...")
    
    # Clear existing clients
    for client in mcp_clients.values():
        try:
            pass  # FastMCP 2.0 handles cleanup automatically
        except:
            pass
    
    # Clear storage
    server_details.clear()
    mcp_clients.clear()
    chat_handler = None
    
    # Reload from config file
    await load_all_servers()
    
    total_tools = sum(len(details.tools) for details in server_details.values())
    
    return {
        "message": "Configuration reloaded from file", 
        "config_file": CONFIG_FILE_PATH,
        "servers_loaded": len(server_details),
        "total_tools": total_tools,
        "chat_available": chat_handler is not None
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    healthy_servers = [name for name, details in server_details.items() if details.status == "connected"]
    
    # Check auth status
    auth_configured = bool(os.getenv("MCP_CLIENT_ID") and os.getenv("MCP_CLIENT_SECRET") and os.getenv("MCP_TENANT_ID"))
    auth_enabled_servers = [name for name, config in server_auth_config.items() if config.get('enabled')]
    
    return {
        "status": "healthy",
        "servers_loaded": len(server_details),
        "healthy_servers": len(healthy_servers),
        "server_status": {name: details.status for name, details in server_details.items()},
        "chat_available": chat_handler is not None,
        "auth_configured": auth_configured,
        "auth_enabled_servers": auth_enabled_servers
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )
