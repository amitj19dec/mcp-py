"""
Server Manager for handling multiple backend MCP server connections
Updated to support ONLY Streamable HTTP protocol (SSE deprecated as of June 2025)
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from concurrent.futures import ThreadPoolExecutor

from models import (
    BackendServer, MCPTool, MCPPrompt, MCPResource, ServerStatus,
    ToolCallRequest, ToolCallResponse, ActivityEvent
)
from mcp_client import MCPClient, MCPClientError
from config import config, ServerConfig

logger = logging.getLogger(__name__)


class ServerManager:
    """
    Manages multiple backend MCP server connections
    ONLY supports Streamable HTTP protocol (SSE deprecated as of June 2025)
    """
    
    def __init__(self):
        self.servers: Dict[str, BackendServer] = {}
        self.clients: Dict[str, MCPClient] = {}
        self.activity_log: List[ActivityEvent] = []
        self._health_check_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self.start_time = datetime.now()
        self.protocol_info = config.get_protocol_info()
        
    async def initialize(self):
        """Initialize server manager and connect to configured Streamable HTTP servers"""
        logger.info("Initializing Server Manager with Streamable HTTP Protocol")
        logger.info(f"Protocol: {self.protocol_info['protocol']}, Transport: {self.protocol_info['transport']}")
        logger.info("Note: SSE transport deprecated as of June 2025 - using Streamable HTTP")
        
        # Load servers from configuration
        for server_config in config.backend_servers:
            await self.add_server(
                server_config.name,
                server_config.endpoint,
                server_config.namespace
            )
        
        # Start health check task
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        
        logger.info(f"Server Manager initialized with {len(self.servers)} Streamable HTTP servers")
    
    async def shutdown(self):
        """Shutdown server manager and disconnect from all Streamable HTTP servers"""
        logger.info("Shutting down Server Manager")
        
        # Cancel health check task
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # Disconnect from all servers
        disconnect_tasks = []
        for client in self.clients.values():
            disconnect_tasks.append(client.disconnect())
        
        if disconnect_tasks:
            await asyncio.gather(*disconnect_tasks, return_exceptions=True)
        
        self.clients.clear()
        logger.info("Server Manager shutdown complete")
    
    async def add_server(
        self, 
        server_id: str, 
        endpoint: str, 
        namespace: str
    ) -> bool:
        """Add a new backend MCP server with Streamable HTTP support"""
        async with self._lock:
            if server_id in self.servers:
                logger.warning(f"Server {server_id} already exists")
                return False
            
            # Validate HTTP endpoint
            if not endpoint.startswith(('http://', 'https://')):
                logger.error(f"Invalid endpoint for server {server_id}: {endpoint}. Must be HTTP/HTTPS for Streamable HTTP protocol.")
                return False
            
            # Create server record
            server = BackendServer(
                id=server_id,
                name=server_id,
                endpoint=endpoint,
                namespace=namespace,
                status=ServerStatus.CONNECTING
            )
            self.servers[server_id] = server
            
            # Create MCP client with Streamable HTTP
            try:
                client = MCPClient(server_id, endpoint, namespace)
                self.clients[server_id] = client
            except MCPClientError as e:
                logger.error(f"Failed to create Streamable HTTP client for {server_id}: {e}")
                del self.servers[server_id]
                return False
            
            # Log activity
            await self._log_activity(
                event_type="server_added",
                details=f"Added Streamable HTTP server {server_id} at {endpoint}",
                server_id=server_id
            )
            
            # Attempt connection
            success = await self._connect_server(server_id)
            
            return success
    
    async def remove_server(self, server_id: str) -> bool:
        """Remove a backend MCP server"""
        async with self._lock:
            if server_id not in self.servers:
                logger.warning(f"Server {server_id} not found")
                return False
            
            # Disconnect client
            if server_id in self.clients:
                await self.clients[server_id].disconnect()
                del self.clients[server_id]
            
            # Remove server record
            del self.servers[server_id]
            
            # Log activity
            await self._log_activity(
                event_type="server_removed",
                details=f"Removed Streamable HTTP server {server_id}",
                server_id=server_id
            )
            
            logger.info(f"Removed Streamable HTTP server {server_id}")
            return True
    
    async def _connect_server(self, server_id: str) -> bool:
        """Connect to a specific backend server using Streamable HTTP"""
        server = self.servers[server_id]
        client = self.clients[server_id]
        
        try:
            logger.info(f"Connecting to server {server_id} using Streamable HTTP (/mcp endpoint)")
            server.status = ServerStatus.CONNECTING
            
            # Attempt connection with retries
            for attempt in range(config.max_retries):
                try:
                    # Use Streamable HTTP connection
                    await client.connect()
                    
                    # Update server status
                    server.status = ServerStatus.CONNECTED
                    server.last_connected = datetime.now()
                    server.last_error = None
                    
                    # Update capability counts
                    server.tool_count = len(client.tools)
                    server.prompt_count = len(client.prompts)
                    server.resource_count = len(client.resources)
                    server.capabilities = client.capabilities
                    server.capabilities.update(client.get_transport_info())
                    
                    # Log successful connection
                    await self._log_activity(
                        event_type="server_connected",
                        details=f"Connected to server {server_id} using Streamable HTTP (attempt {attempt + 1})",
                        server_id=server_id,
                        success=True
                    )
                    
                    logger.info(f"Successfully connected to {server_id} with Streamable HTTP")
                    return True
                    
                except Exception as e:
                    logger.warning(f"Streamable HTTP connection attempt {attempt + 1} failed for {server_id}: {e}")
                    if attempt < config.max_retries - 1:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
            
            # All attempts failed
            server.status = ServerStatus.ERROR
            server.last_error = f"Failed to connect via Streamable HTTP after {config.max_retries} attempts"
            
            await self._log_activity(
                event_type="server_connection_failed",
                details=f"Failed to connect to server {server_id} via Streamable HTTP after {config.max_retries} attempts",
                server_id=server_id,
                success=False
            )
            
            return False
            
        except Exception as e:
            server.status = ServerStatus.ERROR
            server.last_error = str(e)
            logger.error(f"Unexpected error connecting to {server_id} with Streamable HTTP: {e}")
            return False
    
    async def _health_check_loop(self):
        """Background task for periodic health checks"""
        while True:
            try:
                await asyncio.sleep(config.health_check_interval)
                await self._perform_health_checks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")
    
    async def _perform_health_checks(self):
        """Perform health checks on all Streamable HTTP servers"""
        health_tasks = []
        
        for server_id in list(self.servers.keys()):
            health_tasks.append(self._check_server_health(server_id))
        
        if health_tasks:
            await asyncio.gather(*health_tasks, return_exceptions=True)
    
    async def _check_server_health(self, server_id: str):
        """Check health of a specific server using Streamable HTTP"""
        if server_id not in self.servers or server_id not in self.clients:
            return
        
        server = self.servers[server_id]
        client = self.clients[server_id]
        
        try:
            # Ping the server using Streamable HTTP
            is_healthy = await client.ping()
            
            if is_healthy and server.status != ServerStatus.CONNECTED:
                # Server recovered
                server.status = ServerStatus.CONNECTED
                server.last_connected = datetime.now()
                server.last_error = None
                
                await self._log_activity(
                    event_type="server_recovered",
                    details=f"Server {server_id} recovered (Streamable HTTP)",
                    server_id=server_id,
                    success=True
                )
                
            elif not is_healthy and server.status == ServerStatus.CONNECTED:
                # Server became unhealthy
                server.status = ServerStatus.ERROR
                server.last_error = "Streamable HTTP health check failed"
                
                await self._log_activity(
                    event_type="server_health_check_failed",
                    details=f"Streamable HTTP health check failed for server {server_id}",
                    server_id=server_id,
                    success=False
                )
                
                # Attempt reconnection
                await self._connect_server(server_id)
                
        except Exception as e:
            logger.error(f"Streamable HTTP health check error for {server_id}: {e}")
    
    async def get_aggregated_tools(self) -> List[MCPTool]:
        """Get aggregated tools from all connected Streamable HTTP servers"""
        tools = []
        for client in self.clients.values():
            if client.is_initialized:
                tools.extend(client.tools)
        return tools
    
    async def get_aggregated_prompts(self) -> List[MCPPrompt]:
        """Get aggregated prompts from all connected Streamable HTTP servers"""
        prompts = []
        for client in self.clients.values():
            if client.is_initialized:
                prompts.extend(client.prompts)
        return prompts
    
    async def get_aggregated_resources(self) -> List[MCPResource]:
        """Get aggregated resources from all connected Streamable HTTP servers"""
        resources = []
        for client in self.clients.values():
            if client.is_initialized:
                resources.extend(client.resources)
        return resources
    
    async def route_tool_call(self, tool_name: str, arguments: Optional[Dict] = None) -> ToolCallResponse:
        """Route a tool call to the appropriate backend server using Streamable HTTP"""
        # Parse namespace from tool name
        if "." not in tool_name:
            raise ValueError(f"Tool name must include namespace: {tool_name}")
        
        namespace = tool_name.split(".", 1)[0]
        
        # Find server by namespace
        target_server_id = None
        for server_id, server in self.servers.items():
            if server.namespace == namespace:
                target_server_id = server_id
                break
        
        if not target_server_id:
            raise ValueError(f"No server found for namespace: {namespace}")
        
        if target_server_id not in self.clients:
            raise ValueError(f"Server {target_server_id} not available")
        
        server = self.servers[target_server_id]
        if server.status != ServerStatus.CONNECTED:
            raise ValueError(f"Server {target_server_id} is not connected via Streamable HTTP (status: {server.status})")
        
        client = self.clients[target_server_id]
        
        # Log the tool call
        await self._log_activity(
            event_type="tool_called",
            details=f"Calling tool {tool_name} via Streamable HTTP",
            server_id=target_server_id,
            tool_name=tool_name
        )
        
        try:
            # Execute the tool call using Streamable HTTP
            result = await client.call_tool(tool_name, arguments)
            
            # Log success
            await self._log_activity(
                event_type="tool_call_completed",
                details=f"Successfully called tool {tool_name} via Streamable HTTP",
                server_id=target_server_id,
                tool_name=tool_name,
                success=True
            )
            
            return result
            
        except Exception as e:
            # Log failure
            await self._log_activity(
                event_type="tool_call_failed",
                details=f"Failed to call tool {tool_name} via Streamable HTTP: {e}",
                server_id=target_server_id,
                tool_name=tool_name,
                success=False
            )
            
            # Return error response
            return ToolCallResponse(
                content=[{
                    "type": "text",
                    "text": f"Tool call failed via Streamable HTTP: {str(e)}"
                }],
                isError=True
            )
    
    async def get_server_list(self) -> List[BackendServer]:
        """Get list of all backend Streamable HTTP servers"""
        return list(self.servers.values())
    
    async def get_server_status(self, server_id: str) -> Optional[BackendServer]:
        """Get status of a specific Streamable HTTP server"""
        return self.servers.get(server_id)
    
    async def get_activity_log(self, limit: int = 100) -> List[ActivityEvent]:
        """Get recent activity events"""
        return self.activity_log[-limit:] if limit > 0 else self.activity_log
    
    async def _log_activity(
        self,
        event_type: str,
        details: str,
        server_id: Optional[str] = None,
        client_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        success: bool = True
    ):
        """Log an activity event"""
        event = ActivityEvent(
            timestamp=datetime.now(),
            event_type=event_type,
            details=details,
            server_id=server_id,
            client_id=client_id,
            tool_name=tool_name,
            success=success
        )
        
        self.activity_log.append(event)
        
        # Trim activity log to prevent memory issues
        if len(self.activity_log) > config.max_activity_events:
            self.activity_log = self.activity_log[-config.max_activity_events // 2:]
        
        logger.info(f"Activity: {event_type} - {details}")
    
    def get_gateway_status(self) -> Dict[str, any]:
        """Get overall gateway status for Streamable HTTP"""
        connected_servers = sum(1 for s in self.servers.values() if s.status == ServerStatus.CONNECTED)
        total_tools = sum(s.tool_count for s in self.servers.values())
        total_prompts = sum(s.prompt_count for s in self.servers.values())
        total_resources = sum(s.resource_count for s in self.servers.values())
        uptime = datetime.now() - self.start_time
        
        return {
            "status": "healthy" if connected_servers > 0 else "degraded",
            "protocol": self.protocol_info["protocol"],
            "transport": self.protocol_info["transport"],
            "endpoint_path": self.protocol_info["endpoint_path"],
            "servers_connected": connected_servers,
            "servers_total": len(self.servers),
            "total_tools": total_tools,
            "total_prompts": total_prompts,
            "total_resources": total_resources,
            "uptime_seconds": int(uptime.total_seconds())
        }


# Global server manager instance
server_manager = ServerManager()