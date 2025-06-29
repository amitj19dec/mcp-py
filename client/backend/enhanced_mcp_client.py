"""
Enhanced MCP Client with Authentication Support
Extends FastMCP client with Azure AD authentication and RBAC awareness.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, AsyncContextManager
from contextlib import asynccontextmanager

# FastMCP imports
from fastmcp import Client

# HTTP client
import httpx

# Authentication module
from auth_client import AuthenticatedMCPClient, AuthConfig, MCPServerDiscovery

# Configure logging
logger = logging.getLogger(__name__)


class AuthenticatedFastMCPSession:
    """
    Authenticated session wrapper for FastMCP that injects Bearer tokens.
    Provides the same interface as FastMCP session but with auth support.
    """
    
    def __init__(self, base_session, auth_client: AuthenticatedMCPClient):
        self.base_session = base_session
        self.auth_client = auth_client
        self._auth_headers = {}
    
    async def __aenter__(self):
        """Enter async context and set up authentication."""
        # Get auth headers
        self._auth_headers = await self.auth_client.get_auth_headers()
        
        # Inject auth headers into the base session
        # This assumes FastMCP allows header injection - adapt as needed
        if hasattr(self.base_session, '_client') and hasattr(self.base_session._client, 'headers'):
            self.base_session._client.headers.update(self._auth_headers)
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context."""
        # Clean up if needed
        pass
    
    async def list_tools(self):
        """List tools with authentication."""
        try:
            # Make the request with auth headers
            tools = await self.base_session.list_tools()
            
            # Filter tools based on user permissions
            if hasattr(tools, 'tools'):
                tools_list = tools.tools
            elif isinstance(tools, list):
                tools_list = tools
            else:
                tools_list = []
            
            # Convert to dict format for filtering
            tools_dicts = []
            for tool in tools_list:
                tool_dict = {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": getattr(tool, 'inputSchema', {}),
                }
                tools_dicts.append(tool_dict)
            
            # Filter by permissions
            filtered_tools = await self.auth_client.filter_tools_by_permissions(tools_dicts)
            
            # Convert back to original format
            # This is a simplified approach - you may need to preserve the original object structure
            return filtered_tools
            
        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
            raise
    
    async def list_resources(self):
        """List resources with authentication."""
        return await self.base_session.list_resources()
    
    async def list_prompts(self):
        """List prompts with authentication."""
        return await self.base_session.list_prompts()
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]):
        """Call tool with authentication and authorization checking."""
        try:
            # Check if user has permission for this tool
            auth_context = await self.auth_client.get_authorization_context()
            accessible_tools = auth_context.get("accessible_tools", [])
            
            if accessible_tools and name not in accessible_tools:
                raise PermissionError(f"Tool '{name}' not accessible. User has access to: {accessible_tools}")
            
            # Make the tool call
            result = await self.base_session.call_tool(name, arguments)
            logger.info(f"Successfully called tool: {name}")
            return result
            
        except PermissionError:
            raise
        except Exception as e:
            if "403" in str(e) or "Forbidden" in str(e):
                logger.warning(f"Tool call denied: {name} - insufficient permissions")
                raise PermissionError(f"Insufficient permissions to call tool '{name}'")
            else:
                logger.error(f"Tool call failed: {name} - {e}")
                raise


class EnhancedMCPClient:
    """
    Enhanced MCP client that combines FastMCP with authentication capabilities.
    Provides seamless integration with Azure AD and RBAC-aware operations.
    """
    
    def __init__(self, server_url: str, auth_config: AuthConfig, server_name: str = ""):
        self.server_url = server_url
        self.server_name = server_name or server_url
        self.auth_config = auth_config
        
        # Initialize discovery service
        self.discovery = MCPServerDiscovery()
        
        # Initialize authenticated client
        self.auth_client = AuthenticatedMCPClient(server_url, auth_config, self.discovery)
        
        # Initialize base FastMCP client
        self.base_client = Client(server_url)
        
        # Cache for server capabilities
        self._capabilities_cache = None
        self._auth_context_cache = None
    
    async def initialize(self) -> bool:
        """
        Initialize the client and configure authentication.
        Returns True if successfully connected (with or without auth).
        """
        try:
            # Discover and configure authentication
            auth_required = await self.auth_client.discover_and_configure_auth()
            
            if auth_required:
                logger.info(f"Authentication configured for {self.server_name}")
            else:
                logger.info(f"No authentication required for {self.server_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize client for {self.server_name}: {e}")
            raise
    
    @asynccontextmanager
    async def get_session(self) -> AsyncContextManager[AuthenticatedFastMCPSession]:
        """
        Get an authenticated session for MCP operations.
        This provides the same interface as FastMCP but with auth support.
        """
        # Get base FastMCP session
        async with self.base_client as base_session:
            # Wrap with authentication
            auth_session = AuthenticatedFastMCPSession(base_session, self.auth_client)
            async with auth_session as session:
                yield session
    
    async def get_server_capabilities(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Get server capabilities (tools, resources, prompts) with permission filtering.
        """
        if self._capabilities_cache and not force_refresh:
            return self._capabilities_cache
        
        try:
            async with self.get_session() as session:
                # Get all capabilities
                tools = await session.list_tools()
                resources = await session.list_resources()
                prompts = await session.list_prompts()
                
                # Convert resources and prompts to consistent format
                resources_list = []
                if hasattr(resources, 'resources'):
                    for resource in resources.resources:
                        resources_list.append({
                            "uri": str(resource.uri),
                            "name": getattr(resource, 'name', str(resource.uri)),
                            "description": getattr(resource, 'description', ''),
                            "mime_type": getattr(resource, 'mimeType', '')
                        })
                elif isinstance(resources, list):
                    resources_list = resources
                
                prompts_list = []
                if hasattr(prompts, 'prompts'):
                    for prompt in prompts.prompts:
                        prompts_list.append({
                            "name": prompt.name,
                            "description": getattr(prompt, 'description', ''),
                            "arguments": getattr(prompt, 'arguments', [])
                        })
                elif isinstance(prompts, list):
                    prompts_list = prompts
                
                capabilities = {
                    "tools": tools if isinstance(tools, list) else [],
                    "resources": resources_list,
                    "prompts": prompts_list,
                    "server_name": self.server_name,
                    "auth_required": self.auth_config.auth_type != "none"
                }
                
                self._capabilities_cache = capabilities
                return capabilities
                
        except Exception as e:
            logger.error(f"Failed to get server capabilities for {self.server_name}: {e}")
            raise
    
    async def get_authorization_context(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Get user's authorization context and accessible tools."""
        if self._auth_context_cache and not force_refresh:
            return self._auth_context_cache
        
        try:
            context = await self.auth_client.get_authorization_context()
            self._auth_context_cache = context
            return context
            
        except Exception as e:
            logger.warning(f"Failed to get authorization context for {self.server_name}: {e}")
            return {}
    
    async def call_tool_with_auth(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool with full authentication and authorization checking."""
        try:
            async with self.get_session() as session:
                result = await session.call_tool(tool_name, arguments)
                logger.info(f"Successfully executed {self.server_name}.{tool_name}")
                return result
                
        except PermissionError as e:
            logger.warning(f"Permission denied for {self.server_name}.{tool_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Tool execution failed for {self.server_name}.{tool_name}: {e}")
            raise
    
    async def check_tool_permission(self, tool_name: str) -> bool:
        """Check if user has permission to execute a specific tool."""
        try:
            auth_context = await self.get_authorization_context()
            accessible_tools = auth_context.get("accessible_tools", [])
            
            # If no explicit accessible tools list, assume all are accessible
            if not accessible_tools:
                return True
            
            return tool_name in accessible_tools
            
        except Exception as e:
            logger.warning(f"Failed to check tool permission for {tool_name}: {e}")
            return True  # Assume accessible if check fails
    
    async def get_accessible_tools(self) -> List[str]:
        """Get list of tools that the current user can access."""
        try:
            auth_context = await self.get_authorization_context()
            return auth_context.get("accessible_tools", [])
            
        except Exception as e:
            logger.warning(f"Failed to get accessible tools: {e}")
            return []
    
    async def refresh_auth(self):
        """Refresh authentication tokens and clear caches."""
        try:
            if self.auth_client.token_manager:
                scope = self.auth_config.scope or f"api://{self.auth_config.client_id}/.default"
                await self.auth_client.token_manager.refresh_token(scope)
                
            # Clear caches
            self._capabilities_cache = None
            self._auth_context_cache = None
            
            logger.info(f"Authentication refreshed for {self.server_name}")
            
        except Exception as e:
            logger.error(f"Failed to refresh authentication for {self.server_name}: {e}")
            raise
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to the server and return status information."""
        try:
            # Try to get capabilities
            capabilities = await self.get_server_capabilities()
            auth_context = await self.get_authorization_context()
            
            return {
                "status": "connected",
                "server_name": self.server_name,
                "auth_required": self.auth_config.auth_type != "none",
                "tools_count": len(capabilities.get("tools", [])),
                "accessible_tools": auth_context.get("accessible_tools", []),
                "user_roles": auth_context.get("user_roles", []),
                "effective_roles": auth_context.get("effective_roles", [])
            }
            
        except Exception as e:
            return {
                "status": "error",
                "server_name": self.server_name,
                "error": str(e),
                "auth_required": self.auth_config.auth_type != "none"
            }


def create_enhanced_mcp_client(server_config: Dict[str, Any]) -> EnhancedMCPClient:
    """
    Factory function to create an enhanced MCP client from configuration.
    
    Args:
        server_config: Dictionary containing server configuration including auth settings
        
    Returns:
        EnhancedMCPClient instance
    """
    from auth_client import parse_auth_config_from_dict
    
    server_name = server_config.get("name", "")
    server_url = server_config.get("url", "")
    auth_config = parse_auth_config_from_dict(server_config)
    
    return EnhancedMCPClient(server_url, auth_config, server_name)
