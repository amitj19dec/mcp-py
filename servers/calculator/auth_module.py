"""
Authentication Module for MCP Server with Tool-Level RBAC
Handles Azure AD authentication completely decoupled from MCP business logic.
"""

import os
import logging
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass
from abc import ABC, abstractmethod
from enum import Enum

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


class PermissionLevel(Enum):
    """Permission levels for RBAC operations."""
    BASIC = "basic"
    POWER = "power"
    ADMIN = "admin"


@dataclass
class AuthConfig:
    """Authentication configuration for the MCP server."""
    tenant_id: str
    client_id: str
    resource_server_url: str
    required_scopes: List[str]


@dataclass
class ToolPermission:
    """Represents a permission requirement for a specific tool."""
    tool_name: str
    required_roles: List[str]
    permission_level: PermissionLevel
    description: str


class RBACPolicyEngine:
    """
    Role-Based Access Control policy engine for tool-level authorization.
    Completely decoupled from MCP business logic.
    """
    
    def __init__(self):
        self.tool_permissions: Dict[str, ToolPermission] = {}
        self.role_hierarchy: Dict[str, Set[str]] = {}
        self._initialize_default_policies()
    
    def _initialize_default_policies(self):
        """Initialize default RBAC policies for calculator tools."""
        # Define role hierarchy (higher roles inherit lower role permissions)
        self.role_hierarchy = {
            "MCP.Admin": {"MCP.PowerUser", "MCP.BasicUser"},
            "MCP.PowerUser": {"MCP.BasicUser"},
            "MCP.BasicUser": set()
        }
        
        # Define tool permissions
        self.tool_permissions = {
            "add": ToolPermission(
                tool_name="add",
                required_roles=["MCP.BasicUser"],
                permission_level=PermissionLevel.BASIC,
                description="Basic arithmetic operation"
            ),
            "subtract": ToolPermission(
                tool_name="subtract", 
                required_roles=["MCP.BasicUser"],
                permission_level=PermissionLevel.BASIC,
                description="Basic arithmetic operation"
            ),
            "multiply": ToolPermission(
                tool_name="multiply",
                required_roles=["MCP.PowerUser"],
                permission_level=PermissionLevel.POWER,
                description="Advanced arithmetic operation"
            ),
            "divide": ToolPermission(
                tool_name="divide",
                required_roles=["MCP.PowerUser"],
                permission_level=PermissionLevel.POWER,
                description="Advanced arithmetic operation with division by zero handling"
            ),
            "calculate_expression": ToolPermission(
                tool_name="calculate_expression",
                required_roles=["MCP.Admin"],
                permission_level=PermissionLevel.ADMIN,
                description="Expression evaluation with potential security implications"
            )
        }
        
        logger.info(f"Initialized RBAC policies for {len(self.tool_permissions)} tools")
    
    def get_effective_roles(self, user_roles: List[str]) -> Set[str]:
        """Get all effective roles including inherited roles."""
        effective_roles = set(user_roles)
        
        for role in user_roles:
            if role in self.role_hierarchy:
                effective_roles.update(self.role_hierarchy[role])
        
        return effective_roles
    
    def check_tool_permission(self, tool_name: str, user_roles: List[str]) -> bool:
        """
        Check if user has permission to execute a specific tool.
        
        Args:
            tool_name: Name of the MCP tool being accessed
            user_roles: List of roles assigned to the user
            
        Returns:
            bool: True if user has permission, False otherwise
        """
        if tool_name not in self.tool_permissions:
            logger.warning(f"Tool '{tool_name}' not found in RBAC policies")
            return False
        
        tool_permission = self.tool_permissions[tool_name]
        effective_roles = self.get_effective_roles(user_roles)
        
        # Check if user has any of the required roles
        has_permission = any(role in effective_roles for role in tool_permission.required_roles)
        
        logger.info(f"Permission check for tool '{tool_name}': user_roles={user_roles}, "
                   f"effective_roles={effective_roles}, required_roles={tool_permission.required_roles}, "
                   f"granted={has_permission}")
        
        return has_permission
    
    def get_accessible_tools(self, user_roles: List[str]) -> List[str]:
        """Get list of tools that user can access based on their roles."""
        effective_roles = self.get_effective_roles(user_roles)
        accessible_tools = []
        
        for tool_name, permission in self.tool_permissions.items():
            if any(role in effective_roles for role in permission.required_roles):
                accessible_tools.append(tool_name)
        
        return accessible_tools
    
    def get_permission_info(self, tool_name: str) -> Optional[ToolPermission]:
        """Get permission information for a specific tool."""
        return self.tool_permissions.get(tool_name)
    
    def add_tool_permission(self, permission: ToolPermission):
        """Add or update a tool permission (for dynamic configuration)."""
        self.tool_permissions[permission.tool_name] = permission
        logger.info(f"Added/updated permission for tool '{permission.tool_name}'")
    
    def get_authorization_summary(self, user_roles: List[str]) -> Dict[str, Any]:
        """Get comprehensive authorization summary for a user."""
        effective_roles = self.get_effective_roles(user_roles)
        accessible_tools = self.get_accessible_tools(user_roles)
        
        return {
            "user_roles": user_roles,
            "effective_roles": list(effective_roles),
            "accessible_tools": accessible_tools,
            "tool_permissions": {
                tool: {
                    "allowed": tool in accessible_tools,
                    "required_roles": perm.required_roles,
                    "permission_level": perm.permission_level.value,
                    "description": perm.description
                }
                for tool, perm in self.tool_permissions.items()
            }
        }


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
            
            # Extract app roles from token (Azure AD client credentials flow)
            roles = decoded_token.get("roles", [])
            if isinstance(roles, str):
                roles = [roles]
            
            # For user tokens, might also check 'scp' claim for scopes
            scopes = decoded_token.get("scp", "").split() if decoded_token.get("scp") else []
            
            # Combine roles and scopes for comprehensive authorization
            all_permissions = list(set(roles + scopes))
                
            logger.info(f"Token validated - App ID: {decoded_token.get('appid', 'unknown')}, "
                       f"Roles: {roles}, Scopes: {scopes}")
            
            return TokenInfo(
                scopes=all_permissions,
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


class RBACTokenVerifier(TokenVerifier):
    """
    MCP SDK compatible token verifier with RBAC capabilities.
    Handles both request-level and tool-level authorization.
    """
    
    def __init__(self, validator: TokenValidator, required_scopes: List[str], rbac_engine: RBACPolicyEngine):
        self.validator = validator
        self.required_scopes = required_scopes
        self.rbac_engine = rbac_engine

    async def verify_token(self, token: str) -> TokenInfo:
        """Verify token and perform basic scope checking."""
        token_info = await self.validator.validate_token(token)
        
        # Check required scopes for request-level authorization
        if self.required_scopes:
            user_permissions = token_info.scopes or []
            if not any(scope in user_permissions for scope in self.required_scopes):
                raise HTTPException(
                    status_code=403, 
                    detail=f"Insufficient permissions. Required: {self.required_scopes}"
                )
        
        return token_info
    
    def check_tool_authorization(self, tool_name: str, token_info: TokenInfo) -> bool:
        """
        Check if the token holder has permission to execute a specific tool.
        
        Args:
            tool_name: Name of the MCP tool being accessed
            token_info: Validated token information
            
        Returns:
            bool: True if authorized, False otherwise
        """
        user_roles = token_info.scopes or []
        return self.rbac_engine.check_tool_permission(tool_name, user_roles)
    
    def get_authorization_context(self, token_info: TokenInfo) -> Dict[str, Any]:
        """Get comprehensive authorization context for the user."""
        user_roles = token_info.scopes or []
        return self.rbac_engine.get_authorization_summary(user_roles)


class ProtectedResourceMetadata:
    """Handles RFC 9728 Protected Resource Metadata generation."""
    
    def __init__(self, config: AuthConfig, rbac_engine: RBACPolicyEngine):
        self.config = config
        self.rbac_engine = rbac_engine

    def get_metadata(self) -> Dict[str, Any]:
        """Generate the protected resource metadata document per RFC 9728."""
        # Include RBAC information in metadata
        tool_permissions = {
            tool: {
                "required_roles": perm.required_roles,
                "permission_level": perm.permission_level.value,
                "description": perm.description
            }
            for tool, perm in self.rbac_engine.tool_permissions.items()
        }
        
        return {
            "resource": self.config.resource_server_url,
            "authorization_servers": [
                f"https://login.microsoftonline.com/{self.config.tenant_id}"
            ],
            "bearer_methods_supported": ["header"],
            "scopes_supported": self.config.required_scopes,
            "resource_documentation": f"{self.config.resource_server_url}/docs",
            "rbac_info": {
                "supported_roles": list(self.rbac_engine.role_hierarchy.keys()),
                "tool_permissions": tool_permissions,
                "role_hierarchy": {
                    role: list(inherited) for role, inherited in self.rbac_engine.role_hierarchy.items()
                }
            }
        }


class AuthenticationManager:
    """
    Central authentication manager that coordinates all auth components.
    Enhanced with RBAC capabilities for tool-level authorization.
    """
    
    def __init__(self, config: AuthConfig, rbac_engine: Optional[RBACPolicyEngine] = None):
        self.config = config
        self.rbac_engine = rbac_engine or RBACPolicyEngine()
        self.validator = AzureADTokenValidator(config.tenant_id, config.client_id)
        self.mcp_verifier = RBACTokenVerifier(self.validator, config.required_scopes, self.rbac_engine)
        self.prm = ProtectedResourceMetadata(config, self.rbac_engine)
        
    def get_mcp_token_verifier(self) -> TokenVerifier:
        """Get the MCP SDK compatible token verifier."""
        return self.mcp_verifier
    
    def get_rbac_verifier(self) -> RBACTokenVerifier:
        """Get the RBAC-enabled token verifier."""
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
    
    def get_rbac_engine(self) -> RBACPolicyEngine:
        """Get the RBAC policy engine for direct access."""
        return self.rbac_engine


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


def create_rbac_policy_from_env() -> RBACPolicyEngine:
    """Create RBAC policy engine with optional environment-based configuration."""
    rbac_engine = RBACPolicyEngine()
    
    # Allow environment-based customization of tool permissions
    # Format: TOOL_PERMISSIONS=tool1:role1,role2;tool2:role3
    custom_permissions = os.getenv("TOOL_PERMISSIONS")
    if custom_permissions:
        try:
            for tool_config in custom_permissions.split(";"):
                tool_name, roles_str = tool_config.split(":")
                roles = [role.strip() for role in roles_str.split(",")]
                
                permission = ToolPermission(
                    tool_name=tool_name.strip(),
                    required_roles=roles,
                    permission_level=PermissionLevel.BASIC,  # Default level
                    description=f"Custom permission for {tool_name}"
                )
                rbac_engine.add_tool_permission(permission)
                
        except Exception as e:
            logger.warning(f"Failed to parse custom tool permissions: {e}")
    
    return rbac_engine
