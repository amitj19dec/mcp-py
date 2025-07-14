"""
Simple authentication for MCP Gateway
Handles API key validation for external MCP clients and UI access
"""
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import logging

from config import config

logger = logging.getLogger(__name__)

# Security scheme for FastAPI
security = HTTPBearer(auto_error=False)


class AuthenticationError(HTTPException):
    """Custom authentication error"""
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(status_code=401, detail=detail)


class AuthManager:
    """Manages authentication for the gateway"""
    
    def __init__(self):
        self.api_key = config.api_key
        self.ui_token = config.ui_token
    
    def validate_api_key(self, api_key: str) -> bool:
        """Validate API key for external MCP clients"""
        return api_key == self.api_key
    
    def validate_ui_token(self, token: str) -> bool:
        """Validate token for UI access"""
        return token == self.ui_token
    
    def validate_token(self, token: str) -> bool:
        """Validate any token (API key or UI token)"""
        return self.validate_api_key(token) or self.validate_ui_token(token)


# Global auth manager instance
auth_manager = AuthManager()


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> str:
    """
    FastAPI dependency to get current authenticated user
    Returns user type: 'mcp_client' or 'ui_user'
    """
    if not credentials:
        # Check for API key in headers (alternative auth method)
        api_key = request.headers.get("X-API-Key")
        if api_key and auth_manager.validate_api_key(api_key):
            return "mcp_client"
        
        raise AuthenticationError("No authentication credentials provided")
    
    token = credentials.credentials
    
    # Check if it's an API key (for MCP clients)
    if auth_manager.validate_api_key(token):
        return "mcp_client"
    
    # Check if it's a UI token
    if auth_manager.validate_ui_token(token):
        return "ui_user"
    
    raise AuthenticationError("Invalid authentication credentials")


async def get_mcp_client(
    current_user: str = Depends(get_current_user)
) -> str:
    """
    FastAPI dependency that ensures the user is an MCP client
    """
    if current_user != "mcp_client":
        raise AuthenticationError("MCP client authentication required")
    return current_user


async def get_ui_user(
    current_user: str = Depends(get_current_user)
) -> str:
    """
    FastAPI dependency that ensures the user is a UI user
    """
    if current_user != "ui_user":
        raise AuthenticationError("UI authentication required")
    return current_user


async def optional_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[str]:
    """
    Optional authentication dependency
    Returns user type if authenticated, None if not
    """
    if not credentials:
        return None
    
    token = credentials.credentials
    
    if auth_manager.validate_api_key(token):
        return "mcp_client"
    
    if auth_manager.validate_ui_token(token):
        return "ui_user"
    
    return None


def create_auth_header(token: str) -> dict:
    """Create authorization header for HTTP requests"""
    return {"Authorization": f"Bearer {token}"}


def extract_client_id(request: Request, user_type: str) -> str:
    """Extract client ID from request for logging"""
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    return f"{user_type}_{client_ip}_{hash(user_agent) % 10000}"
