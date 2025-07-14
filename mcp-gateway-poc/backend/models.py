"""
Data models for MCP Gateway
Pydantic models for request/response structures and internal data
"""
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
from enum import Enum


class ServerStatus(str, Enum):
    """Backend MCP server connection status"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    CONNECTING = "connecting"


class MCPCapability(BaseModel):
    """Base model for MCP capabilities (tools, prompts, resources)"""
    name: str
    description: Optional[str] = None
    source_server: str
    namespace: str


class MCPTool(MCPCapability):
    """MCP Tool definition with parameters schema"""
    input_schema: Optional[Dict[str, Any]] = None


class MCPPrompt(MCPCapability):
    """MCP Prompt definition with arguments"""
    arguments: Optional[List[Dict[str, Any]]] = None


class MCPResource(MCPCapability):
    """MCP Resource definition"""
    uri: Optional[str] = None
    mime_type: Optional[str] = None


class BackendServer(BaseModel):
    """Backend MCP server configuration and status"""
    id: str
    name: str
    endpoint: str
    namespace: str
    status: ServerStatus = ServerStatus.DISCONNECTED
    last_connected: Optional[datetime] = None
    last_error: Optional[str] = None
    tool_count: int = 0
    prompt_count: int = 0
    resource_count: int = 0
    capabilities: Dict[str, Any] = Field(default_factory=dict)


class ToolCallRequest(BaseModel):
    """Request to execute a tool"""
    name: str
    arguments: Optional[Dict[str, Any]] = None


class ToolCallResponse(BaseModel):
    """Response from tool execution"""
    content: List[Dict[str, Any]]
    isError: bool = False


class ActivityEvent(BaseModel):
    """Activity log event"""
    timestamp: datetime
    event_type: str
    details: str
    server_id: Optional[str] = None
    client_id: Optional[str] = None
    tool_name: Optional[str] = None
    success: bool = True


class MCPRequest(BaseModel):
    """Generic MCP JSON-RPC request"""
    jsonrpc: str = "2.0"
    id: Union[str, int, None] = None
    method: str
    params: Optional[Dict[str, Any]] = None


class MCPResponse(BaseModel):
    """Generic MCP JSON-RPC response"""
    jsonrpc: str = "2.0"
    id: Union[str, int, None] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None


class MCPError(BaseModel):
    """MCP JSON-RPC error"""
    code: int
    message: str
    data: Optional[Any] = None


class GatewayStatus(BaseModel):
    """Overall gateway status"""
    status: str
    servers_connected: int
    servers_total: int
    total_tools: int
    total_prompts: int
    total_resources: int
    uptime_seconds: int


class ServerListResponse(BaseModel):
    """Response for server list API"""
    servers: List[BackendServer]
    total: int


class ToolCatalogResponse(BaseModel):
    """Response for tool catalog API"""
    tools: List[MCPTool]
    prompts: List[MCPPrompt]
    resources: List[MCPResource]
    total_tools: int
    total_prompts: int
    total_resources: int


class ActivityLogResponse(BaseModel):
    """Response for activity log API"""
    events: List[ActivityEvent]
    total: int


class AddServerRequest(BaseModel):
    """Request to add a new backend server"""
    name: str
    endpoint: str
    namespace: str


class ToolExecuteRequest(BaseModel):
    """Request to execute a tool via UI"""
    tool_name: str
    arguments: Optional[Dict[str, Any]] = None


class AuthToken(BaseModel):
    """Authentication token info"""
    token: str
    token_type: str = "bearer"
    expires_in: Optional[int] = None


class ClientSession(BaseModel):
    """MCP client session info"""
    client_id: str
    connected_at: datetime
    last_activity: datetime
    capabilities: Dict[str, Any] = Field(default_factory=dict)
