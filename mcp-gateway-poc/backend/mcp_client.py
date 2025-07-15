"""
MCP Client implementation using Official MCP Python SDK
Uses proper streamablehttp_client for Streamable HTTP protocol
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from contextlib import AsyncExitStack

# Import Official MCP SDK - Streamable HTTP
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from models import (
    MCPTool, MCPPrompt, MCPResource, ServerStatus, ToolCallResponse
)
from config import config

logger = logging.getLogger(__name__)


class MCPClientError(Exception):
    """Custom exception for MCP client errors"""
    pass


class MCPClient:
    """
    MCP Client using Official MCP Python SDK
    Uses streamablehttp_client for proper Streamable HTTP protocol support
    """
    
    def __init__(self, server_name: str, endpoint: str, namespace: str):
        self.server_name = server_name
        self.endpoint = endpoint.rstrip('/')
        self.namespace = namespace
        self.client_info = {
            "name": "mcp-gateway",
            "version": "1.0.0"
        }
        
        # Validate HTTP endpoint
        if not self.endpoint.startswith(('http://', 'https://')):
            raise MCPClientError(f"Invalid HTTP endpoint: {self.endpoint}. Must start with http:// or https://")
        
        # Official SDK components
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.mcp_endpoint = f"{self.endpoint}/mcp"
        
        # Connection state
        self.is_initialized = False
        self.capabilities: Dict[str, Any] = {}
        
        # Discovered capabilities
        self.tools: List[MCPTool] = []
        self.prompts: List[MCPPrompt] = []
        self.resources: List[MCPResource] = []
        
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()
    
    async def connect(self) -> bool:
        """Connect and initialize session with backend MCP server using Official SDK"""
        try:
            logger.info(f"Connecting to MCP server via Streamable HTTP: {self.server_name} at {self.mcp_endpoint}")
            
            # Use official SDK streamablehttp_client
            read_stream, write_stream, _ = await self.exit_stack.enter_async_context(
                streamablehttp_client(self.mcp_endpoint)
            )
            
            # Create session using official SDK
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            
            # Initialize the connection
            await self.session.initialize()
            
            logger.info(f"Successfully connected to {self.server_name} via Streamable HTTP")
            self.is_initialized = True
            
            # Discover available tools, prompts, and resources
            await self.discover_capabilities()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to {self.server_name} via Streamable HTTP: {e}")
            raise MCPClientError(f"Streamable HTTP connection failed: {e}")
    
    async def disconnect(self):
        """Disconnect from backend MCP server"""
        if self.exit_stack:
            await self.exit_stack.aclose()
        
        self.is_initialized = False
        self.session = None
        logger.info(f"Disconnected from {self.server_name}")
    
    async def discover_capabilities(self):
        """Discover tools, prompts, and resources from backend server using Official SDK"""
        try:
            if not self.session:
                raise MCPClientError("No active session")
            
            # Discover tools using official SDK
            await self._discover_tools()
            
            # Discover prompts using official SDK
            await self._discover_prompts()
            
            # Discover resources using official SDK
            await self._discover_resources()
                
            logger.info(f"Discovered {len(self.tools)} tools, {len(self.prompts)} prompts, {len(self.resources)} resources from {self.server_name} via Streamable HTTP")
            
        except Exception as e:
            logger.error(f"Failed to discover capabilities from {self.server_name} via Streamable HTTP: {e}")
            # Don't raise - partial discovery is better than total failure
    
    async def _discover_tools(self):
        """Discover available tools using Official SDK"""
        try:
            # Use official SDK method
            result = await self.session.list_tools()
            
            self.tools = []
            for tool in result.tools:
                mcp_tool = MCPTool(
                    name=f"{self.namespace}.{tool.name}",
                    description=tool.description,
                    input_schema=tool.inputSchema if hasattr(tool, 'inputSchema') else None,
                    source_server=self.server_name,
                    namespace=self.namespace
                )
                self.tools.append(mcp_tool)
                
        except Exception as e:
            logger.error(f"Failed to discover tools from {self.server_name} via Streamable HTTP: {e}")
    
    async def _discover_prompts(self):
        """Discover available prompts using Official SDK"""
        try:
            # Use official SDK method
            result = await self.session.list_prompts()
            
            self.prompts = []
            for prompt in result.prompts:
                mcp_prompt = MCPPrompt(
                    name=f"{self.namespace}.{prompt.name}",
                    description=prompt.description,
                    arguments=prompt.arguments if hasattr(prompt, 'arguments') else None,
                    source_server=self.server_name,
                    namespace=self.namespace
                )
                self.prompts.append(mcp_prompt)
                
        except Exception as e:
            logger.error(f"Failed to discover prompts from {self.server_name} via Streamable HTTP: {e}")
    
    async def _discover_resources(self):
        """Discover available resources using Official SDK"""
        try:
            # Use official SDK method
            result = await self.session.list_resources()
            
            self.resources = []
            for resource in result.resources:
                # Handle AnyUrl from MCP SDK
                uri_str = None
                if hasattr(resource, 'uri') and resource.uri:
                    uri_str = str(resource.uri)  # Convert AnyUrl to string
                
                mcp_resource = MCPResource(
                    name=f"{self.namespace}.{resource.name}",
                    description=resource.description if hasattr(resource, 'description') else None,
                    uri=uri_str,
                    mime_type=resource.mimeType if hasattr(resource, 'mimeType') else None,
                    source_server=self.server_name,
                    namespace=self.namespace
                )
                self.resources.append(mcp_resource)
                
        except Exception as e:
            logger.error(f"Failed to discover resources from {self.server_name} via Streamable HTTP: {e}")
    
    async def call_tool(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> ToolCallResponse:
        """
        Call a tool on the backend server using Official SDK
        tool_name should NOT include namespace prefix when calling backend
        """
        if not self.is_initialized or not self.session:
            raise MCPClientError("Streamable HTTP client not initialized")
        
        # Remove namespace prefix for backend call
        backend_tool_name = tool_name
        if tool_name.startswith(f"{self.namespace}."):
            backend_tool_name = tool_name[len(f"{self.namespace}."):]
        
        try:
            logger.info(f"Calling tool {backend_tool_name} on {self.server_name} via Streamable HTTP")
            
            # Use official SDK method
            result = await self.session.call_tool(backend_tool_name, arguments or {})
            
            # Convert SDK result to our response format
            content = []
            if hasattr(result, 'content'):
                if isinstance(result.content, list):
                    content = [self._convert_content_item(item) for item in result.content]
                else:
                    content = [self._convert_content_item(result.content)]
            
            return ToolCallResponse(
                content=content,
                isError=getattr(result, 'isError', False)
            )
            
        except Exception as e:
            logger.error(f"Failed to call tool {backend_tool_name} on {self.server_name} via Streamable HTTP: {e}")
            return ToolCallResponse(
                content=[{
                    "type": "text",
                    "text": f"Error calling tool via Streamable HTTP: {str(e)}"
                }],
                isError=True
            )
    
    def _convert_content_item(self, item) -> Dict[str, Any]:
        """Convert SDK content item to our format"""
        if hasattr(item, 'type') and hasattr(item, 'text'):
            return {
                "type": item.type,
                "text": item.text
            }
        elif isinstance(item, dict):
            return item
        else:
            return {
                "type": "text", 
                "text": str(item)
            }
    
    async def get_prompt(self, prompt_name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get a prompt from the backend server using Official SDK"""
        if not self.is_initialized or not self.session:
            raise MCPClientError("Streamable HTTP client not initialized")
        
        # Remove namespace prefix for backend call
        backend_prompt_name = prompt_name
        if prompt_name.startswith(f"{self.namespace}."):
            backend_prompt_name = prompt_name[len(f"{self.namespace}."):]
        
        try:
            # Use official SDK method
            result = await self.session.get_prompt(backend_prompt_name, arguments or {})
            
            # Convert result to dict format
            return {
                "description": getattr(result, 'description', ''),
                "messages": [
                    {
                        "role": msg.role,
                        "content": self._convert_content_item(msg.content)
                    } 
                    for msg in result.messages
                ] if hasattr(result, 'messages') else []
            }
            
        except Exception as e:
            logger.error(f"Failed to get prompt {backend_prompt_name} from {self.server_name} via Streamable HTTP: {e}")
            raise MCPClientError(f"Failed to get prompt via Streamable HTTP: {e}")
    
    async def get_resource(self, resource_uri: str) -> Dict[str, Any]:
        """Get a resource from the backend server using Official SDK"""
        if not self.is_initialized or not self.session:
            raise MCPClientError("Streamable HTTP client not initialized")
        
        try:
            # Use official SDK method
            result = await self.session.read_resource(resource_uri)
            
            # Convert result to dict format
            return {
                "contents": [
                    self._convert_content_item(content) 
                    for content in result.contents
                ] if hasattr(result, 'contents') else []
            }
            
        except Exception as e:
            logger.error(f"Failed to get resource {resource_uri} from {self.server_name} via Streamable HTTP: {e}")
            raise MCPClientError(f"Failed to get resource via Streamable HTTP: {e}")
    
    async def ping(self) -> bool:
        """Ping the backend server to check Streamable HTTP connectivity"""
        try:
            if not self.session:
                return False
            
            # Try a simple tools/list call as a health check
            await self.session.list_tools()
            return True
        except Exception:
            return False
    
    def get_status(self) -> ServerStatus:
        """Get current Streamable HTTP connection status"""
        if not self.is_initialized:
            return ServerStatus.DISCONNECTED
        
        return ServerStatus.CONNECTED
    
    def get_transport_info(self) -> Dict[str, str]:
        """Get transport information"""
        return {
            "transport": "streamable-http",
            "protocol": "http",
            "endpoint": self.endpoint,
            "mcp_endpoint": self.mcp_endpoint
        }