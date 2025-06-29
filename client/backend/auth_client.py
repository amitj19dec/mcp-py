"""
Azure AD Authentication Module for MCP Client
Handles OAuth 2.1 authentication for MCP servers using official Microsoft libraries.
"""

import os
import asyncio
import logging
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from abc import ABC, abstractmethod

# Microsoft Authentication Library
from msal import ConfidentialClientApplication
from azure.identity import ClientSecretCredential
from azure.core.credentials import AccessToken

# HTTP client for discovery
import httpx

# JWT handling for token inspection (optional)
import jwt
from jwt import PyJWKSClient

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class AuthConfig:
    """Authentication configuration for MCP server."""
    auth_type: str  # "azure_ad", "bearer_token", "none"
    tenant_id: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    scope: Optional[str] = None
    authority: Optional[str] = None
    static_token: Optional[str] = None


@dataclass
class TokenInfo:
    """Token information with metadata."""
    access_token: str
    expires_at: datetime
    scope: str
    token_type: str = "Bearer"
    
    def is_expired(self, buffer_seconds: int = 300) -> bool:
        """Check if token is expired (with buffer for refresh)."""
        return datetime.now(timezone.utc) >= (self.expires_at - timedelta(seconds=buffer_seconds))


class TokenManager(ABC):
    """Abstract base class for token management."""
    
    @abstractmethod
    async def get_token(self, scope: str) -> str:
        """Get a valid access token for the given scope."""
        pass
    
    @abstractmethod
    async def refresh_token(self, scope: str) -> str:
        """Force refresh of the token for the given scope."""
        pass


class AzureADTokenManager(TokenManager):
    """
    Azure AD token manager using MSAL for OAuth 2.1 client credentials flow.
    Handles automatic token caching and refresh.
    """
    
    def __init__(self, tenant_id: str, client_id: str, client_secret: str, authority: Optional[str] = None):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.authority = authority or f"https://login.microsoftonline.com/{tenant_id}"
        
        # Initialize MSAL application
        self.msal_app = ConfidentialClientApplication(
            client_id=client_id,
            client_credential=client_secret,
            authority=self.authority
        )
        
        # Token cache (MSAL handles internal caching, this is for our metadata)
        self.token_cache: Dict[str, TokenInfo] = {}
        
        logger.info(f"Initialized Azure AD token manager for tenant: {tenant_id}")
    
    async def get_token(self, scope: str) -> str:
        """Get a valid access token for the scope, using cache when possible."""
        # Check if we have a valid cached token
        if scope in self.token_cache and not self.token_cache[scope].is_expired():
            logger.debug(f"Using cached token for scope: {scope}")
            return self.token_cache[scope].access_token
        
        # Acquire new token
        return await self.refresh_token(scope)
    
    async def refresh_token(self, scope: str) -> str:
        """Acquire a new token from Azure AD."""
        try:
            logger.info(f"Acquiring token for scope: {scope}")
            
            # Use MSAL to acquire token (this is synchronous but fast)
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.msal_app.acquire_token_for_client(scopes=[scope])
            )
            
            if "access_token" not in result:
                error_msg = result.get("error_description", result.get("error", "Unknown error"))
                raise Exception(f"Failed to acquire token: {error_msg}")
            
            # Extract token information
            access_token = result["access_token"]
            expires_in = result.get("expires_in", 3600)  # Default to 1 hour
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            
            # Cache token info
            token_info = TokenInfo(
                access_token=access_token,
                expires_at=expires_at,
                scope=scope,
                token_type="Bearer"
            )
            self.token_cache[scope] = token_info
            
            logger.info(f"Successfully acquired token for scope: {scope} (expires: {expires_at})")
            return access_token
            
        except Exception as e:
            logger.error(f"Failed to acquire token for scope {scope}: {e}")
            raise


class StaticTokenManager(TokenManager):
    """Simple token manager for static bearer tokens (for testing/development)."""
    
    def __init__(self, static_token: str):
        self.static_token = static_token
        logger.info("Initialized static token manager")
    
    async def get_token(self, scope: str) -> str:
        """Return the static token."""
        return self.static_token
    
    async def refresh_token(self, scope: str) -> str:
        """Return the static token (no refresh needed)."""
        return self.static_token


class MCPServerDiscovery:
    """
    Handles RFC 9728 Protected Resource Metadata discovery for MCP servers.
    Discovers authentication requirements from MCP servers.
    """
    
    def __init__(self):
        self.discovery_cache: Dict[str, Dict[str, Any]] = {}
    
    async def discover_auth_requirements(self, server_url: str) -> Dict[str, Any]:
        """
        Discover authentication requirements for an MCP server.
        Returns metadata from .well-known/oauth-protected-resource endpoint.
        """
        if server_url in self.discovery_cache:
            return self.discovery_cache[server_url]
        
        try:
            # Try to access the server without auth first
            async with httpx.AsyncClient() as client:
                # Check if server requires auth by making a test request
                try:
                    response = await client.get(f"{server_url}/health", timeout=5.0)
                    if response.status_code == 200:
                        # Server doesn't require auth
                        metadata = {"auth_required": False}
                        self.discovery_cache[server_url] = metadata
                        return metadata
                except:
                    pass
                
                # Try to get protected resource metadata
                metadata_url = f"{server_url}/.well-known/oauth-protected-resource"
                response = await client.get(metadata_url, timeout=5.0)
                
                if response.status_code == 200:
                    metadata = response.json()
                    metadata["auth_required"] = True
                    self.discovery_cache[server_url] = metadata
                    logger.info(f"Discovered auth metadata for {server_url}")
                    return metadata
                else:
                    # Try a regular request to see if we get WWW-Authenticate
                    response = await client.post(f"{server_url}", timeout=5.0)
                    if response.status_code == 401:
                        www_auth = response.headers.get("WWW-Authenticate", "")
                        if "resource_metadata" in www_auth:
                            # Extract metadata URL from WWW-Authenticate header
                            # This is a simplified extraction - real implementation would be more robust
                            logger.info(f"Server {server_url} requires authentication")
                            metadata = {"auth_required": True, "www_authenticate": www_auth}
                            self.discovery_cache[server_url] = metadata
                            return metadata
                
                # No auth requirements discovered
                metadata = {"auth_required": False}
                self.discovery_cache[server_url] = metadata
                return metadata
                
        except Exception as e:
            logger.warning(f"Failed to discover auth requirements for {server_url}: {e}")
            # Assume no auth required if discovery fails
            return {"auth_required": False}


class AuthenticatedMCPClient:
    """
    MCP client wrapper that handles authentication automatically.
    Integrates with FastMCP client and injects Bearer tokens.
    """
    
    def __init__(self, server_url: str, auth_config: AuthConfig, discovery: MCPServerDiscovery):
        self.server_url = server_url
        self.auth_config = auth_config
        self.discovery = discovery
        self.token_manager: Optional[TokenManager] = None
        self._auth_context: Optional[Dict[str, Any]] = None
        
        # Initialize token manager based on auth config
        self._initialize_token_manager()
    
    def _initialize_token_manager(self):
        """Initialize the appropriate token manager based on auth configuration."""
        if self.auth_config.auth_type == "azure_ad":
            if not all([self.auth_config.tenant_id, self.auth_config.client_id, self.auth_config.client_secret]):
                raise ValueError("Azure AD auth requires tenant_id, client_id, and client_secret")
            
            self.token_manager = AzureADTokenManager(
                tenant_id=self.auth_config.tenant_id,
                client_id=self.auth_config.client_id,
                client_secret=self.auth_config.client_secret,
                authority=self.auth_config.authority
            )
            
        elif self.auth_config.auth_type == "bearer_token":
            if not self.auth_config.static_token:
                raise ValueError("Bearer token auth requires static_token")
            
            self.token_manager = StaticTokenManager(self.auth_config.static_token)
            
        elif self.auth_config.auth_type == "none":
            self.token_manager = None
            
        else:
            raise ValueError(f"Unsupported auth type: {self.auth_config.auth_type}")
    
    async def discover_and_configure_auth(self) -> bool:
        """
        Discover server authentication requirements and configure accordingly.
        Returns True if auth is required and configured successfully.
        """
        try:
            metadata = await self.discovery.discover_auth_requirements(self.server_url)
            
            if not metadata.get("auth_required", False):
                logger.info(f"Server {self.server_url} does not require authentication")
                return False
            
            logger.info(f"Server {self.server_url} requires authentication")
            
            # If auth is required but not configured, this is an error
            if self.auth_config.auth_type == "none":
                logger.error(f"Server {self.server_url} requires auth but none configured")
                raise ValueError(f"Authentication required for {self.server_url} but not configured")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to configure auth for {self.server_url}: {e}")
            raise
    
    async def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for requests."""
        if not self.token_manager or self.auth_config.auth_type == "none":
            return {}
        
        try:
            scope = self.auth_config.scope or f"api://{self.auth_config.client_id}/.default"
            token = await self.token_manager.get_token(scope)
            return {"Authorization": f"Bearer {token}"}
            
        except Exception as e:
            logger.error(f"Failed to get auth headers: {e}")
            raise
    
    async def make_authenticated_request(self, method: str, endpoint: str, **kwargs) -> httpx.Response:
        """Make an authenticated HTTP request to the MCP server."""
        headers = await self.get_auth_headers()
        
        # Merge with any existing headers
        if "headers" in kwargs:
            headers.update(kwargs["headers"])
        kwargs["headers"] = headers
        
        url = f"{self.server_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        async with httpx.AsyncClient() as client:
            response = await client.request(method, url, **kwargs)
            
            # Handle auth errors
            if response.status_code == 401:
                logger.warning(f"Authentication failed for {url}")
                # Could implement token refresh and retry here
                
            elif response.status_code == 403:
                logger.warning(f"Authorization denied for {url}")
                
            return response
    
    async def get_authorization_context(self) -> Dict[str, Any]:
        """
        Get user's authorization context from the server.
        Returns information about accessible tools and permissions.
        """
        if self._auth_context:
            return self._auth_context
        
        try:
            response = await self.make_authenticated_request("GET", "/auth/info")
            if response.status_code == 200:
                self._auth_context = response.json()
                return self._auth_context
            else:
                logger.warning(f"Failed to get auth context: {response.status_code}")
                return {}
                
        except Exception as e:
            logger.warning(f"Failed to get authorization context: {e}")
            return {}
    
    async def filter_tools_by_permissions(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter tools based on user's permissions."""
        if self.auth_config.auth_type == "none":
            return tools  # No filtering needed
        
        try:
            auth_context = await self.get_authorization_context()
            accessible_tools = auth_context.get("accessible_tools", [])
            
            if not accessible_tools:
                # If no explicit accessible tools, assume all are accessible
                return tools
            
            # Filter tools
            filtered_tools = [tool for tool in tools if tool.get("name") in accessible_tools]
            
            logger.info(f"Filtered tools: {len(filtered_tools)}/{len(tools)} accessible")
            return filtered_tools
            
        except Exception as e:
            logger.warning(f"Failed to filter tools by permissions: {e}")
            return tools  # Return all tools if filtering fails


def create_token_manager_from_config(auth_config: AuthConfig) -> Optional[TokenManager]:
    """Factory function to create token manager from configuration."""
    if auth_config.auth_type == "azure_ad":
        return AzureADTokenManager(
            tenant_id=auth_config.tenant_id,
            client_id=auth_config.client_id,
            client_secret=auth_config.client_secret,
            authority=auth_config.authority
        )
    elif auth_config.auth_type == "bearer_token":
        return StaticTokenManager(auth_config.static_token)
    elif auth_config.auth_type == "none":
        return None
    else:
        raise ValueError(f"Unsupported auth type: {auth_config.auth_type}")


def parse_auth_config_from_dict(config_dict: Dict[str, Any]) -> AuthConfig:
    """Parse authentication configuration from dictionary."""
    auth_config = config_dict.get("auth", {})
    
    if not auth_config:
        return AuthConfig(auth_type="none")
    
    # Support environment variable substitution
    def resolve_env_vars(value: str) -> str:
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            env_var = value[2:-1]
            return os.getenv(env_var, value)
        return value
    
    return AuthConfig(
        auth_type=auth_config.get("type", "none"),
        tenant_id=resolve_env_vars(auth_config.get("tenant_id", "")),
        client_id=resolve_env_vars(auth_config.get("client_id", "")),
        client_secret=resolve_env_vars(auth_config.get("client_secret", "")),
        scope=resolve_env_vars(auth_config.get("scope", "")),
        authority=resolve_env_vars(auth_config.get("authority", "")),
        static_token=resolve_env_vars(auth_config.get("static_token", ""))
    )
