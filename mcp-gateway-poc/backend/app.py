"""
Main FastAPI application for MCP Gateway
Serves dual role: MCP server for external clients + REST API for UI
ONLY supports Streamable HTTP protocol (SSE deprecated as of June 2025)
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from models import (
    MCPRequest, MCPResponse, MCPError, 
    ServerListResponse, ToolCatalogResponse, ActivityLogResponse,
    AddServerRequest, ToolExecuteRequest, GatewayStatus,
    BackendServer, MCPTool, MCPPrompt, MCPResource,
    ToolCallRequest, ToolCallResponse
)
from server_manager import server_manager
from auth import get_current_user, get_mcp_client, get_ui_user, extract_client_id
from config import config

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("Starting MCP Gateway - Streamable HTTP Protocol Only")
    logger.info(f"Protocol: {config.protocol}, Transport: {config.transport}")
    await server_manager.initialize()
    logger.info("MCP Gateway started successfully with Streamable HTTP")
    
    yield
    
    # Shutdown
    logger.info("Shutting down MCP Gateway")
    await server_manager.shutdown()
    logger.info("MCP Gateway shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="MCP Gateway - Streamable HTTP",
    description="Gateway for aggregating multiple MCP servers using Streamable HTTP protocol (/mcp endpoint)",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# MCP JSON-RPC Protocol Endpoints (for external MCP clients)
# Streamable HTTP Protocol Implementation
# ============================================================================

@app.post("/mcp")
async def mcp_endpoint(
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_mcp_client)
):
    """
    Main MCP JSON-RPC endpoint for external clients
    Handles standard MCP protocol communication via Streamable HTTP
    """
    try:
        # Parse JSON-RPC request
        body = await request.body()
        request_data = json.loads(body)
        
        # Extract client ID for logging
        client_id = extract_client_id(request, current_user)
        
        # Log the request
        method = request_data.get("method", "unknown")
        logger.info(f"MCP Streamable HTTP request from {client_id}: {method}")
        
        # Handle the request
        response = await handle_mcp_request(request_data, client_id)
        
        # Log activity in background
        background_tasks.add_task(
            server_manager._log_activity,
            event_type="mcp_streamable_http_request",
            details=f"MCP Streamable HTTP {method} request from {client_id}",
            client_id=client_id
        )
        
        return response
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in MCP Streamable HTTP request: {e}")
        return create_mcp_error_response(None, -32700, "Parse error")
    except Exception as e:
        logger.error(f"Unexpected error in MCP Streamable HTTP endpoint: {e}")
        return create_mcp_error_response(None, -32603, "Internal error")


async def handle_mcp_request(request_data: Dict[str, Any], client_id: str) -> Dict[str, Any]:
    """Handle individual MCP JSON-RPC request via Streamable HTTP"""
    request_id = request_data.get("id")
    method = request_data.get("method")
    params = request_data.get("params", {})
    
    try:
        if method == "initialize":
            return await handle_initialize(request_id, params, client_id)
        elif method == "notifications/initialized":
            return await handle_initialized(request_id, client_id)
        elif method == "tools/list":
            return await handle_tools_list(request_id)
        elif method == "tools/call":
            return await handle_tools_call(request_id, params, client_id)
        elif method == "prompts/list":
            return await handle_prompts_list(request_id)
        elif method == "prompts/get":
            return await handle_prompts_get(request_id, params, client_id)
        elif method == "resources/list":
            return await handle_resources_list(request_id)
        elif method == "resources/read":
            return await handle_resources_read(request_id, params, client_id)
        else:
            return create_mcp_error_response(request_id, -32601, f"Method not found: {method}")
            
    except Exception as e:
        logger.error(f"Error handling MCP Streamable HTTP method {method}: {e}")
        return create_mcp_error_response(request_id, -32603, f"Internal error: {str(e)}")


async def handle_initialize(request_id: Any, params: Dict[str, Any], client_id: str) -> Dict[str, Any]:
    """Handle MCP initialize request for Streamable HTTP"""
    logger.info(f"Initializing MCP Streamable HTTP client {client_id}")
    
    # Get gateway capabilities (aggregated from Streamable HTTP backend servers)
    tools = await server_manager.get_aggregated_tools()
    prompts = await server_manager.get_aggregated_prompts()
    resources = await server_manager.get_aggregated_resources()
    
    capabilities = {
        "tools": {
            "listChanged": False  # We don't support dynamic tool updates yet
        },
        "prompts": {
            "listChanged": False
        },
        "resources": {
            "listChanged": False
        }
    }
    
    result = {
        "protocolVersion": "2025-06-18",
        "capabilities": capabilities,
        "serverInfo": {
            "name": "mcp-gateway-streamable-http",
            "version": "1.0.0",
            "protocol": "streamable-http",
            "transport": "http"
        }
    }
    
    return create_mcp_response(request_id, result)


async def handle_initialized(request_id: Any, client_id: str) -> Dict[str, Any]:
    """Handle MCP initialized notification"""
    logger.info(f"MCP Streamable HTTP client {client_id} initialized")
    # This is a notification, no response needed
    return {}


async def handle_tools_list(request_id: Any) -> Dict[str, Any]:
    """Handle tools/list request from Streamable HTTP servers"""
    tools = await server_manager.get_aggregated_tools()
    
    tools_data = []
    for tool in tools:
        tool_data = {
            "name": tool.name,
            "description": tool.description or ""
        }
        if tool.input_schema:
            tool_data["inputSchema"] = tool.input_schema
        tools_data.append(tool_data)
    
    result = {"tools": tools_data}
    return create_mcp_response(request_id, result)


async def handle_tools_call(request_id: Any, params: Dict[str, Any], client_id: str) -> Dict[str, Any]:
    """Handle tools/call request - route to Streamable HTTP backend"""
    tool_name = params.get("name")
    arguments = params.get("arguments", {})
    
    if not tool_name:
        return create_mcp_error_response(request_id, -32602, "Missing tool name")
    
    try:
        result = await server_manager.route_tool_call(tool_name, arguments)
        
        return create_mcp_response(request_id, {
            "content": result.content,
            "isError": result.isError
        })
        
    except ValueError as e:
        return create_mcp_error_response(request_id, -32602, str(e))
    except Exception as e:
        return create_mcp_error_response(request_id, -32603, f"Tool execution failed via Streamable HTTP: {str(e)}")


async def handle_prompts_list(request_id: Any) -> Dict[str, Any]:
    """Handle prompts/list request from Streamable HTTP servers"""
    prompts = await server_manager.get_aggregated_prompts()
    
    prompts_data = []
    for prompt in prompts:
        prompt_data = {
            "name": prompt.name,
            "description": prompt.description or ""
        }
        if prompt.arguments:
            prompt_data["arguments"] = prompt.arguments
        prompts_data.append(prompt_data)
    
    result = {"prompts": prompts_data}
    return create_mcp_response(request_id, result)


async def handle_prompts_get(request_id: Any, params: Dict[str, Any], client_id: str) -> Dict[str, Any]:
    """Handle prompts/get request - route to Streamable HTTP backend"""
    # Implementation would route to appropriate Streamable HTTP backend server
    # For now, return method not implemented
    return create_mcp_error_response(request_id, -32601, "prompts/get not implemented yet for Streamable HTTP")


async def handle_resources_list(request_id: Any) -> Dict[str, Any]:
    """Handle resources/list request from Streamable HTTP servers"""
    resources = await server_manager.get_aggregated_resources()
    
    resources_data = []
    for resource in resources:
        resource_data = {
            "name": resource.name,
            "description": resource.description or ""
        }
        if resource.uri:
            resource_data["uri"] = resource.uri
        if resource.mime_type:
            resource_data["mimeType"] = resource.mime_type
        resources_data.append(resource_data)
    
    result = {"resources": resources_data}
    return create_mcp_response(request_id, result)


async def handle_resources_read(request_id: Any, params: Dict[str, Any], client_id: str) -> Dict[str, Any]:
    """Handle resources/read request - route to Streamable HTTP backend"""
    # Implementation would route to appropriate Streamable HTTP backend server
    # For now, return method not implemented
    return create_mcp_error_response(request_id, -32601, "resources/read not implemented yet for Streamable HTTP")


def create_mcp_response(request_id: Any, result: Dict[str, Any]) -> Dict[str, Any]:
    """Create MCP JSON-RPC response"""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": result
    }


def create_mcp_error_response(request_id: Any, code: int, message: str, data: Any = None) -> Dict[str, Any]:
    """Create MCP JSON-RPC error response"""
    error = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": error
    }


# ============================================================================
# REST API Endpoints (for React UI)
# Management interface for Streamable HTTP servers
# ============================================================================

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    status = server_manager.get_gateway_status()
    return {"status": "healthy", "details": status}


@app.get("/api/status", response_model=GatewayStatus)
async def get_gateway_status(current_user: str = Depends(get_ui_user)):
    """Get overall gateway status for Streamable HTTP"""
    status = server_manager.get_gateway_status()
    return GatewayStatus(**status)


@app.get("/api/protocol")
async def get_protocol_info():
    """Get information about the supported protocol"""
    return config.get_protocol_info()


@app.get("/api/servers", response_model=ServerListResponse)
async def get_servers(current_user: str = Depends(get_ui_user)):
    """Get list of backend Streamable HTTP servers"""
    servers = await server_manager.get_server_list()
    return ServerListResponse(servers=servers, total=len(servers))


@app.post("/api/servers")
async def add_server(
    server_request: AddServerRequest,
    current_user: str = Depends(get_ui_user)
):
    """Add a new backend Streamable HTTP server"""
    try:
        # Validate HTTP endpoint
        if not server_request.endpoint.startswith(('http://', 'https://')):
            raise HTTPException(
                status_code=400, 
                detail="Only HTTP/HTTPS endpoints are supported for Streamable HTTP protocol"
            )
        
        success = await server_manager.add_server(
            server_request.name,
            server_request.endpoint,
            server_request.namespace
        )
        
        if success:
            return {"success": True, "message": f"Streamable HTTP server {server_request.name} added successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to add Streamable HTTP server")
            
    except Exception as e:
        logger.error(f"Error adding Streamable HTTP server: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/servers/{server_id}")
async def remove_server(
    server_id: str,
    current_user: str = Depends(get_ui_user)
):
    """Remove a backend Streamable HTTP server"""
    try:
        success = await server_manager.remove_server(server_id)
        
        if success:
            return {"success": True, "message": f"Streamable HTTP server {server_id} removed successfully"}
        else:
            raise HTTPException(status_code=404, detail="Server not found")
            
    except Exception as e:
        logger.error(f"Error removing Streamable HTTP server: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tools", response_model=ToolCatalogResponse)
async def get_tool_catalog(current_user: str = Depends(get_ui_user)):
    """Get aggregated tool catalog from Streamable HTTP servers"""
    tools = await server_manager.get_aggregated_tools()
    prompts = await server_manager.get_aggregated_prompts()
    resources = await server_manager.get_aggregated_resources()
    
    return ToolCatalogResponse(
        tools=tools,
        prompts=prompts,
        resources=resources,
        total_tools=len(tools),
        total_prompts=len(prompts),
        total_resources=len(resources)
    )


@app.post("/api/tools/execute")
async def execute_tool(
    tool_request: ToolExecuteRequest,
    current_user: str = Depends(get_ui_user)
):
    """Execute a tool for testing via UI - route to Streamable HTTP backend"""
    try:
        result = await server_manager.route_tool_call(
            tool_request.tool_name,
            tool_request.arguments
        )
        
        return {
            "success": not result.isError,
            "result": result.content,
            "isError": result.isError,
            "transport": "streamable-http"
        }
        
    except Exception as e:
        logger.error(f"Error executing tool {tool_request.tool_name} via Streamable HTTP: {e}")
        return {
            "success": False,
            "result": [{"type": "text", "text": f"Error via Streamable HTTP: {str(e)}"}],
            "isError": True,
            "transport": "streamable-http"
        }


@app.get("/api/activity", response_model=ActivityLogResponse)
async def get_activity_log(
    limit: int = 100,
    current_user: str = Depends(get_ui_user)
):
    """Get recent activity log"""
    events = await server_manager.get_activity_log(limit)
    return ActivityLogResponse(events=events, total=len(events))


@app.get("/api/servers/{server_id}")
async def get_server_status(
    server_id: str,
    current_user: str = Depends(get_ui_user)
):
    """Get status of a specific Streamable HTTP server"""
    server = await server_manager.get_server_status(server_id)
    
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    
    return server


# ============================================================================
# Root endpoint for basic info
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint with basic gateway information"""
    status = server_manager.get_gateway_status()
    protocol_info = config.get_protocol_info()
    
    return {
        "name": "MCP Gateway - Streamable HTTP",
        "version": "1.0.0",
        "description": "Gateway for aggregating multiple MCP servers using Streamable HTTP protocol (/mcp endpoint)",
        "protocol": protocol_info,
        "status": status,
        "endpoints": {
            "mcp": "/mcp",
            "api": "/api",
            "health": "/api/health",
            "protocol": "/api/protocol"
        },
        "note": "SSE transport deprecated as of June 2025"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host=config.host,
        port=config.port,
        reload=config.debug,
        log_level=config.log_level.lower()
    )