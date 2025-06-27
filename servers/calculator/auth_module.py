"""
Authentication Module for MCP Server
Handles Azure AD authentication completely decoupled from MCP business logic.
"""

import os
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from abc import ABC, abstractmethod

# Azure AD and JWT handling
import jwt
from jwt import PyJWKSClient
from datetime import datetime, timezone

# MCP SDK imports for token verification
from mcp.server.auth.provider import TokenVerifier, TokenInfo
from mcp.server.auth.settings import AuthSettings

# FastAPI for HTTP responses
from fastapi import HTTPException

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class AuthConfig:
    """Authentication configuration for the MCP server."""
    tenant_id: str
    client_id: str
    resource_server_url: str
    required_scopes: List[str]


class TokenValidator(ABC):
    """Abstract base class for token validation."""
    
    @abstractmethod
    async def validate_token(self, token: str) -> TokenInfo:
        """Validate a token and return token information."""
        pass


class AzureADTokenValidator(TokenValidator):
    """Azure AD specific token validator using JWKS."""
    
    def __init__(self, tenant_id: str, client_id: str):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.issuer = f"https://login.microsoftonline.com/{tenant_id}/v2.0"
        self.jwks_url = f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"
        self.jwks_client = PyJWKSClient(self.jwks_url)
        logger.info(f"Initialized Azure AD token validator for tenant: {tenant_id}")

    async def validate_token(self, token: str) -> TokenInfo:
        """Validate Azure AD JWT token against JWKS."""
        try:
            # Get signing key from JWKS endpoint
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            
            # Decode and validate token
            decoded_token = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer=self.issuer,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iat": True,
                    "verify_aud": True,
                    "verify_iss": True
                }
            )
            
            # Additional validation
            current_time = datetime.now(timezone.utc).timestamp()
            
            if decoded_token.get("exp", 0) < current_time:
                raise HTTPException(status_code=401, detail="Token expired")
            
            if decoded_token.get("nbf", 0) > current_time:
                raise HTTPException(status_code=401, detail="Token not yet valid")
            
            # Extract scopes/roles from token
            scopes = decoded_token.get("roles", [])
            if isinstance(scopes, str):
                scopes = [scopes]
                
            logger.info(f"Token validated for user: {decoded_token.get('preferred_username', 'unknown')}")
            
            return TokenInfo(
                scopes=scopes,
                claims=decoded_token
            )
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token validation failed: Token expired")
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError as e:
            logger.warning(f"Token validation failed: {str(e)}")
            raise HTTPException(status_code=401, detail="Invalid token")
        except Exception as e:
            logger.error(f"Token validation error: {str(e)}")
            raise HTTPException(status_code=401, detail="Token validation failed")


class MCPTokenVerifier(TokenVerifier):
    """MCP SDK compatible token verifier wrapper."""
    
    def __init__(self, validator: TokenValidator, required_scopes: List[str]):
        self.validator = validator
        self.required_scopes = required_scopes

    async def verify_token(self, token: str) -> TokenInfo:
        """Verify token using the wrapped validator and check scopes."""
        token_info = await self.validator.validate_token(token)
        
        # Check required scopes if any are specified
        if self.required_scopes:
            user_scopes = token_info.scopes or []
            if not any(scope in user_scopes for scope in self.required_scopes):
                raise HTTPException(
                    status_code=403, 
                    detail=f"Insufficient permissions. Required: {self.required_scopes}"
                )
        
        return token_info


class ProtectedResourceMetadata:
    """Handles RFC 9728 Protected Resource Metadata generation."""
    
    def __init__(self, config: AuthConfig):
        self.config = config

    def get_metadata(self) -> Dict[str, Any]:
        """Generate the protected resource metadata document per RFC 9728."""
        return {
            "resource": self.config.resource_server_url,
            "authorization_servers": [
                f"https://login.microsoftonline.com/{self.config.tenant_id}"
            ],
            "bearer_methods_supported": ["header"],
            "scopes_supported": self.config.required_scopes,
            "resource_documentation": f"{self.config.resource_server_url}/docs"
        }


class AuthenticationManager:
    """Central authentication manager that coordinates all auth components."""
    
    def __init__(self, config: AuthConfig):
        self.config = config
        self.validator = AzureADTokenValidator(config.tenant_id, config.client_id)
        self.mcp_verifier = MCPTokenVerifier(self.validator, config.required_scopes)
        self.prm = ProtectedResourceMetadata(config)
        
    def get_mcp_token_verifier(self) -> TokenVerifier:
        """Get the MCP SDK compatible token verifier."""
        return self.mcp_verifier
    
    def get_auth_settings(self) -> AuthSettings:
        """Get MCP SDK auth settings."""
        return AuthSettings(
            issuer_url=f"https://login.microsoftonline.com/{self.config.tenant_id}",
            resource_server_url=self.config.resource_server_url,
            required_scopes=self.config.required_scopes,
        )
    
    def get_protected_resource_metadata(self) -> Dict[str, Any]:
        """Get the protected resource metadata per RFC 9728."""
        return self.prm.get_metadata()


def create_auth_config_from_env() -> AuthConfig:
    """Create authentication configuration from environment variables."""
    tenant_id = os.getenv("AZURE_TENANT_ID")
    client_id = os.getenv("AZURE_CLIENT_ID")
    
    if not tenant_id or not client_id:
        raise ValueError("AZURE_TENANT_ID and AZURE_CLIENT_ID environment variables are required")
    
    resource_server_url = os.getenv("MCP_SERVER_URL", "https://localhost:8000")
    required_scopes_str = os.getenv("REQUIRED_SCOPES", "MCP.User,MCP.Admin")
    required_scopes = [scope.strip() for scope in required_scopes_str.split(",") if scope.strip()]
    
    return AuthConfig(
        tenant_id=tenant_id,
        client_id=client_id,
        resource_server_url=resource_server_url,
        required_scopes=required_scopes
    )
