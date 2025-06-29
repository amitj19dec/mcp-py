#!/usr/bin/env python3
"""
Enhanced MCP Client Backend with Authentication Support
Loads all MCP server details with Azure AD authentication and provides chat interface with RBAC-aware tool calling.
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

# Enhanced MCP client with authentication
from enhanced_mcp_client import EnhancedMCPClient, create_enhanced_mcp_client
from auth_client import AuthConfig, parse_auth_config_from_dict

# Chat functionality (enhanced to work with authenticated clients)
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
    annotations: Optional[Dict[str, Any]] = None
    server: str = ""
    accessible: bool = True

class ResourceInfo(BaseModel):
    uri: str
    name: str
    description: str = ""
    mime_type: str = ""
    server: str = ""

class PromptInfo(BaseModel):
    name: str
    description: str = ""
    arguments: List[Dict[str, Any]] = []
    server: str = ""

class ServerDetails(BaseModel):
    name: str
    description: str
    status: str
    auth_required: bool = False
    tools: List[ToolInfo] = []
    resources: List[ResourceInfo] = []
    prompts: List[PromptInfo] = []
    auth_context: Dict[str, Any] = {}

class ToolCallRequest(BaseModel):
    server_name: str
    tool_name: str
    arguments: Dict[str, Any] = {}

class ToolResult(BaseModel):
    success: bool
    result: Any = None
    error: Optional[str] = None
    permission_denied: bool = False

class AuthStatusResponse(BaseModel):
    server_name: str
    auth_required: bool
    status: str
    accessible_tools: List[str] = []
    user_roles: List[str] = []
    error: Optional[str] = None

# Global storage for enhanced MCP clients and server details
enhanced_clients: Dict[str, EnhancedMCPClient] = {}
server_details: Dict[str, ServerDetails] = {}
chat_handler: Optional[ChatHandler] = None

# Configuration file path
CONFIG_FILE_PATH = "/Users/amitj/Documents/code2.0/mcp-py/client/mcp_config.json"

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
    """Load MCP server configuration from JSON file with auth support."""
    try:
        if not os.path.exists(CONFIG_FILE_PATH):
            logger.error(f"Config file not found: {CONFIG_FILE_PATH}")
            return []
        
        with open(CONFIG_FILE_PATH, 'r') as f:
            config_data = json.load(f)
        
        servers = []
        for server_config in config_data.get('servers', []):
            servers.append(MCPServerConfig(
                name=server_config['name'],
                url=server_config['url'],
                description=server_config.get('description', ''),
                auth=server_config.get('auth', None)
            ))
        
        logger.info(f"📄 Loaded {len(servers)} server configs from {CONFIG_FILE_PATH}")
        return servers
        
    except Exception as e:
        logger.error(f"Failed to load config from {CONFIG_FILE_PATH}: {e}")
        return []

async def load_server_details(config: MCPServerConfig) -> ServerDetails:
    """Load complete server details with authentication support."""
    try:
        logger.info(f"Loading details for {config.name} with auth support...")
        
        # Create enhanced MCP client
        client = create_enhanced_mcp_client(config.dict())
        enhanced_clients[config.name] = client
        
        # Initialize client and test connection
        await client.initialize()
        connection_status = await client.test_connection()
        
        if connection_status["status"] != "connected":
            logger.warning(f"Failed to connect to {config.name}: {connection_status.get('error', 'Unknown error')}")
            return ServerDetails(
                name=config.name,
                description=config.description,
                status="error",
                auth_required=connection_status.get("auth_required", False),
                tools=[],
                resources=[],
                prompts=[],
                auth_context={}
            )
        
        # Get server capabilities with permission filtering
        capabilities = await client.get_server_capabilities()
        auth_context = await client.get_authorization_context()
        
        # Convert tools with accessibility info
        tools = []
        accessible_tools = auth_context.get("accessible_tools", [])
        for tool in capabilities.get("tools", []):
            tool_name = tool.get("name", "")
            is_accessible = not accessible_tools or tool_name in accessible_tools
            
            tools.append(ToolInfo(
                name=tool_name,
                description=tool.get("description", ""),
                title=tool.get("title", tool_name),
                input_schema=tool.get("input_schema", {}),
                annotations=tool.get("annotations", {}),
                server=config.name,
                accessible=is_accessible
            ))
        
        # Convert resources
        resources = []
        for resource in capabilities.get("resources", []):
            resources.append(ResourceInfo(
                uri=resource.get("uri", ""),
                name=resource.get("name", ""),
                description=resource.get("description", ""),
                mime_type=resource.get("mime_type", ""),
                server=config.name
            ))
        
        # Convert prompts
        prompts = []
        for prompt in capabilities.get("prompts", []):
            prompts.append(PromptInfo(
                name=prompt.get("name", ""),
                description=prompt.get("description", ""),
                arguments=prompt.get("arguments", []),
                server=config.name
            ))
        
        details = ServerDetails(
            name=config.name,
            description=config.description,
            status="connected",
            auth_required=capabilities.get("auth_required", False),
            tools=tools,
            resources=resources,
            prompts=prompts,
            auth_context=auth_context
        )
        
        accessible_count = len([t for t in tools if t.accessible])
        logger.info(f"✅ Loaded {config.name}: {accessible_count}/{len(tools)} accessible tools, "
                   f"{len(resources)} resources, {len(prompts)} prompts")
        
        if auth_context:
            user_roles = auth_context.get("user_roles", [])
            if user_roles:
                logger.info(f"🔐 User roles for {config.name}: {user_roles}")
        
        return details
        
    except Exception as e:
        logger.error(f"❌ Failed to load {config.name}: {e}")
        return ServerDetails(
            name=config.name,
            description=config.description,
            status="error",
            auth_required=True,  # Assume auth required if loading failed
            tools=[],
            resources=[],
            prompts=[],
            auth_context={}
        )

async def load_all_servers():
    """Load details from all configured MCP servers with authentication."""
    logger.info("🚀 Loading all MCP server details with authentication support...")
    
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
    accessible_tools = sum(len([t for t in details.tools if t.accessible]) for details in server_details.values())
    total_resources = sum(len(details.resources) for details in server_details.values())
    total_prompts = sum(len(details.prompts) for details in server_details.values())
    auth_servers = len([d for d in server_details.values() if d.auth_required])
    
    logger.info(f"📊 Summary: {len(server_details)} servers ({auth_servers} with auth), "
               f"{accessible_tools}/{total_tools} accessible tools, "
               f"{total_resources} resources, {total_prompts} prompts")
    
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
    enhanced_clients.clear()

# Create FastAPI app
app = FastAPI(
    title="Enhanced MCP Client Backend with Authentication",
    description="MCP backend with Azure AD authentication support and RBAC-aware chat integration",
    version="2.0.0",
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
    """Root endpoint with summary including auth information."""
    total_tools = sum(len(details.tools) for details in server_details.values())
    accessible_tools = sum(len([t for t in details.tools if t.accessible]) for details in server_details.values())
    total_resources = sum(len(details.resources) for details in server_details.values())
    total_prompts = sum(len(details.prompts) for details in server_details.values())
    auth_enabled_servers = [name for name, details in server_details.items() if details.auth_required]
    
    return {
        "message": "Enhanced MCP Client Backend with Authentication",
        "servers_loaded": len(server_details),
        "auth_enabled_servers": len(auth_enabled_servers),
        "auth_server_names": auth_enabled_servers,
        "total_tools": total_tools,
        "accessible_tools": accessible_tools,
        "total_resources": total_resources,
        "total_prompts": total_prompts,
        "server_names": list(server_details.keys()),
        "chat_available": chat_handler is not None
    }

# === CHAT ENDPOINTS ===

@app.post("/chat", response_model=ChatResponse)
async def chat_with_llm(request: ChatMessage):
    """Chat with LLM that can dynamically call accessible MCP tools with auth support."""
    if not chat_handler:
        raise HTTPException(
            status_code=503, 
            detail="Chat functionality not available. Please check Azure OpenAI configuration."
        )
    
    try:
        # Get all accessible tools in the format needed for LLM
        all_tools = []
        for server_name, details in server_details.items():
            for tool in details.tools:
                if tool.accessible:  # Only include accessible tools
                    tool_data = tool.dict()
                    all_tools.append(tool_data)
        
        logger.info(f"🤖 Processing chat with {len(all_tools)} accessible tools")
        
        # Process chat with available tools (enhanced chat handler will handle auth)
        response = await chat_handler.chat_with_tools_auth(
            message=request.message,
            available_tools=all_tools,
            enhanced_clients=enhanced_clients
        )
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Chat processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")

@app.get("/chat/status")
async def chat_status():
    """Check if chat functionality is available with auth information."""
    accessible_tools = sum(len([t for t in details.tools if t.accessible]) for details in server_details.values())
    auth_servers = [name for name, details in server_details.items() if details.auth_required]
    
    return {
        "chat_available": chat_handler is not None,
        "azure_openai_configured": bool(os.getenv("AZURE_OPENAI_ENDPOINT") and os.getenv("AZURE_OPENAI_API_KEY")),
        "deployment_name": os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4"),
        "tools_available": accessible_tools,
        "auth_enabled_servers": len(auth_servers),
        "auth_server_names": auth_servers
    }

# === AUTHENTICATION ENDPOINTS ===

@app.get("/auth/status", response_model=List[AuthStatusResponse])
async def get_auth_status():
    """Get authentication status for all servers."""
    status_list = []
    
    for server_name, client in enhanced_clients.items():
        try:
            connection_status = await client.test_connection()
            auth_context = await client.get_authorization_context()
            
            status_list.append(AuthStatusResponse(
                server_name=server_name,
                auth_required=client.auth_config.auth_type != "none",
                status=connection_status["status"],
                accessible_tools=auth_context.get("accessible_tools", []),
                user_roles=auth_context.get("user_roles", []),
                error=connection_status.get("error")
            ))
            
        except Exception as e:
            status_list.append(AuthStatusResponse(
                server_name=server_name,
                auth_required=True,
                status="error",
                error=str(e)
            ))
    
    return status_list

@app.post("/auth/refresh/{server_name}")
async def refresh_server_auth(server_name: str):
    """Refresh authentication for a specific server."""
    if server_name not in enhanced_clients:
        raise HTTPException(404, f"Server {server_name} not found")
    
    try:
        client = enhanced_clients[server_name]
        await client.refresh_auth()
        
        # Reload server details
        config_data = load_mcp_config()
        server_config = next((s for s in config_data if s.name == server_name), None)
        if server_config:
            new_details = await load_server_details(server_config)
            server_details[server_name] = new_details
        
        return {"message": f"Authentication refreshed for {server_name}", "status": "success"}
        
    except Exception as e:
        logger.error(f"Failed to refresh auth for {server_name}: {e}")
        raise HTTPException(500, f"Failed to refresh authentication: {str(e)}")

@app.get("/auth/context/{server_name}")
async def get_server_auth_context(server_name: str):
    """Get detailed authentication context for a server."""
    if server_name not in enhanced_clients:
        raise HTTPException(404, f"Server {server_name} not found")
    
    try:
        client = enhanced_clients[server_name]
        auth_context = await client.get_authorization_context(force_refresh=True)
        
        return {
            "server_name": server_name,
            "auth_context": auth_context,
            "auth_type": client.auth_config.auth_type,
            "scope": client.auth_config.scope
        }
        
    except Exception as e:
        logger.error(f"Failed to get auth context for {server_name}: {e}")
        raise HTTPException(500, f"Failed to get authentication context: {str(e)}")

# === SERVER MANAGEMENT ENDPOINTS ===

@app.get("/servers", response_model=List[ServerDetails])
async def get_all_servers():
    """Get all loaded server details with authentication information."""
    return list(server_details.values())

@app.get("/servers/{server_name}", response_model=ServerDetails)
async def get_server_details(server_name: str):
    """Get specific server details with auth context."""
    if server_name not in server_details:
        raise HTTPException(404, f"Server {server_name} not found")
    
    return server_details[server_name]

@app.get("/tools")
async def get_all_tools():
    """Get all accessible tools from all servers."""
    all_tools = []
    for server_name, details in server_details.items():
        for tool in details.tools:
            if tool.accessible:  # Only include accessible tools
                all_tools.append(tool.dict())
    
    return {"tools": all_tools, "total": len(all_tools)}

@app.get("/tools/accessible/{server_name}")
async def get_accessible_tools(server_name: str):
    """Get tools accessible to the current user for a specific server."""
    if server_name not in enhanced_clients:
        raise HTTPException(404, f"Server {server_name} not found")
    
    try:
        client = enhanced_clients[server_name]
        accessible_tools = await client.get_accessible_tools()
        
        return {
            "server_name": server_name,
            "accessible_tools": accessible_tools,
            "total": len(accessible_tools)
        }
        
    except Exception as e:
        logger.error(f"Failed to get accessible tools for {server_name}: {e}")
        raise HTTPException(500, f"Failed to get accessible tools: {str(e)}")

@app.post("/tools/call", response_model=ToolResult)
async def call_tool(request: ToolCallRequest):
    """Execute a tool on the specified server with authentication and authorization."""
    if request.server_name not in enhanced_clients:
        raise HTTPException(404, f"Server {request.server_name} not connected")
    
    try:
        client = enhanced_clients[request.server_name]
        
        # Check permission first
        has_permission = await client.check_tool_permission(request.tool_name)
        if not has_permission:
            return ToolResult(
                success=False,
                error=f"Permission denied for tool '{request.tool_name}'",
                permission_denied=True
            )
        
        # Execute tool with auth
        result = await client.call_tool_with_auth(request.tool_name, request.arguments)
        
        logger.info(f"✅ Tool call: {request.server_name}.{request.tool_name}")
        return ToolResult(success=True, result=result)
        
    except PermissionError as e:
        logger.warning(f"🚫 Permission denied: {request.server_name}.{request.tool_name}")
        return ToolResult(
            success=False,
            error=str(e),
            permission_denied=True
        )
    except Exception as e:
        logger.error(f"❌ Tool call failed: {e}")
        return ToolResult(success=False, error=str(e))

# === CONFIGURATION ENDPOINTS ===

@app.get("/config")
async def get_config():
    """Get current MCP configuration with auth information."""
    try:
        mcp_servers = load_mcp_config()
        config_with_auth = []
        
        for server in mcp_servers:
            server_dict = server.dict()
            # Mask sensitive information
            if server_dict.get("auth") and server_dict["auth"].get("client_secret"):
                server_dict["auth"]["client_secret"] = "***masked***"
            config_with_auth.append(server_dict)
        
        return {
            "config_file": CONFIG_FILE_PATH,
            "servers": config_with_auth
        }
    except Exception as e:
        raise HTTPException(500, f"Error loading config: {str(e)}")

@app.post("/config/reload")
async def reload_config():
    """Reload configuration from file and reconnect to servers with auth."""
    global server_details, enhanced_clients, chat_handler
    
    logger.info("🔄 Reloading configuration from file with auth support...")
    
    # Clear existing clients and storage
    enhanced_clients.clear()
    server_details.clear()
    chat_handler = None
    
    # Reload from config file
    await load_all_servers()
    
    accessible_tools = sum(len([t for t in details.tools if t.accessible]) for details in server_details.values())
    auth_servers = len([d for d in server_details.values() if d.auth_required])
    
    return {
        "message": "Configuration reloaded from file with authentication support", 
        "config_file": CONFIG_FILE_PATH,
        "servers_loaded": len(server_details),
        "auth_enabled_servers": auth_servers,
        "accessible_tools": accessible_tools,
        "chat_available": chat_handler is not None
    }

@app.get("/health")
async def health_check():
    """Health check endpoint with authentication status."""
    healthy_servers = [name for name, details in server_details.items() if details.status == "connected"]
    auth_servers = [name for name, details in server_details.items() if details.auth_required]
    
    return {
        "status": "healthy",
        "servers_loaded": len(server_details),
        "healthy_servers": len(healthy_servers),
        "auth_enabled_servers": len(auth_servers),
        "server_status": {name: details.status for name, details in server_details.items()},
        "auth_status": {name: details.auth_required for name, details in server_details.items()},
        "chat_available": chat_handler is not None
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
