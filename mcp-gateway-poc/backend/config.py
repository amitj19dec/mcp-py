"""
Configuration management for MCP Gateway
Updated to support ONLY Streamable HTTP protocol (SSE deprecated as of June 2025)
"""
import os
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class ServerConfig:
    """Configuration for a backend MCP server using Streamable HTTP only"""
    name: str
    endpoint: str
    namespace: str
    
    def __post_init__(self):
        """Validate that endpoint is HTTP/HTTPS"""
        if not self.endpoint.startswith(('http://', 'https://')):
            raise ValueError(f"Invalid endpoint: {self.endpoint}. Must be HTTP/HTTPS URL for streamable HTTP protocol")
    
    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'ServerConfig':
        return cls(
            name=data['name'],
            endpoint=data['endpoint'],
            namespace=data['namespace']
        )


class Config:
    """Main configuration class - Streamable HTTP Protocol Only (SSE deprecated)"""
    
    def __init__(self):
        # Server configuration
        self.host = os.getenv("GATEWAY_HOST", "0.0.0.0")
        self.port = int(os.getenv("GATEWAY_PORT", "8000"))
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        
        # Protocol specification (SSE deprecated as of June 2025)
        self.protocol = "streamable-http"
        self.transport = "http"
        
        # Authentication
        self.api_key = os.getenv("GATEWAY_API_KEY", "gateway-dev-key-123")
        self.ui_token = os.getenv("UI_TOKEN", "ui-dev-token-456")
        
        # CORS settings
        self.cors_origins = self._parse_list(os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001"))
        
        # Backend MCP servers (Streamable HTTP only)
        self.backend_servers = self._parse_backend_servers()
        
        # HTTP specific timeouts (SSE deprecated)
        self.http_connect_timeout = int(os.getenv("HTTP_CONNECT_TIMEOUT", "30"))
        self.http_request_timeout = int(os.getenv("HTTP_REQUEST_TIMEOUT", "60"))
        self.http_stream_timeout = int(os.getenv("HTTP_STREAM_TIMEOUT", "300"))  # For long-running streams
        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))
        
        # Activity log settings
        self.max_activity_events = int(os.getenv("MAX_ACTIVITY_EVENTS", "1000"))
        
        # Health check settings
        self.health_check_interval = int(os.getenv("HEALTH_CHECK_INTERVAL", "30"))
        
        # Logging
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.log_format = os.getenv("LOG_FORMAT", "json")
    
    def _parse_list(self, value: str) -> List[str]:
        """Parse comma-separated string into list"""
        if not value:
            return []
        return [item.strip() for item in value.split(",") if item.strip()]
    
    def _parse_backend_servers(self) -> List[ServerConfig]:
        """
        Parse backend MCP servers from environment variables
        ONLY supports HTTP/HTTPS endpoints for streamable HTTP protocol
        """
        servers = []
        
        # Parse from MCP_SERVERS environment variable
        # Format: "name1:endpoint1:namespace1,name2:endpoint2:namespace2"
        # All endpoints MUST be HTTP/HTTPS URLs
        # Examples:
        # - "api:http://localhost:8000:api"  (connects to http://localhost:8000/mcp)

        servers_env = os.getenv("MCP_SERVERS", "")
        if servers_env:
            for server_str in servers_env.split(","):
                parts = [p.strip() for p in server_str.strip().split(":")]
                if len(parts) >= 3:
                    name = parts[0]
                    # Handle URLs with ports by joining middle parts
                    endpoint = ":".join(parts[1:-1])
                    namespace = parts[-1]
                    
                    try:
                        servers.append(ServerConfig(
                            name=name,
                            endpoint=endpoint,
                            namespace=namespace
                        ))
                    except ValueError as e:
                        print(f"Warning: Skipping invalid server config '{server_str}': {e}")
                        continue
        
        # If no servers configured, use default for development
        if not servers:
            print("No MCP servers found from the config")
        
        return servers

    def add_server(self, server: ServerConfig):
        """Add a new backend server configuration"""
        if not server.endpoint.startswith(('http://', 'https://')):
            raise ValueError(f"Only HTTP/HTTPS endpoints are supported. Got: {server.endpoint}")
        
        self.backend_servers.append(server)
    
    def remove_server(self, server_id: str):
        """Remove a backend server by ID (name)"""
        self.backend_servers = [s for s in self.backend_servers if s.name != server_id]
    
    def get_server_config(self, server_id: str) -> ServerConfig:
        """Get server configuration by ID"""
        for server in self.backend_servers:
            if server.name == server_id:
                return server
        raise ValueError(f"Server {server_id} not found in configuration")
    
    def validate_configuration(self) -> bool:
        """Validate that all configured servers support Streamable HTTP"""
        for server in self.backend_servers:
            if not server.endpoint.startswith(('http://', 'https://')):
                raise ValueError(f"Server {server.name} has invalid endpoint: {server.endpoint}. Only HTTP/HTTPS supported.")
        return True
    
    def get_protocol_info(self) -> Dict[str, str]:
        """Get information about the supported protocol"""
        return {
            "protocol": self.protocol,
            "transport": self.transport,
            "description": "Streamable HTTP protocol (SSE deprecated as of June 2025)",
            "supported_schemes": ["http", "https"],
            "mcp_version": "2025-06-18",
            "endpoint_path": "/mcp"
        }


# Global configuration instance
config = Config()

# Validate configuration on import
try:
    config.validate_configuration()
except ValueError as e:
    print(f"Configuration Error: {e}")
    print("Gateway will not start with invalid configuration.")