"""
Calculator MCP Server with Official SDK OAuth 2.1 Implementation
Uses the official MCP SDK auth framework for automatic OAuth 2.1 compliance including:
- /.well-known/oauth-protected-resource endpoint (RFC 9728)
- Proper WWW-Authenticate headers on 401 responses
- Azure AD JWT token validation with app roles
"""

import os
import jwt
import logging
from typing import Any, Dict, List, Optional
from functools import wraps
import requests
import base64
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from mcp.server.fastmcp import FastMCP, Context
from mcp.server.auth.settings import AuthSettings
from mcp.server.auth.provider import TokenVerifier

# Configure logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Role-based tool permissions
ROLE_PERMISSIONS = {
    "MCP.User": ["add", "subtract"],
    "MCP.Admin": ["add", "subtract", "multiply", "divide", "calculate_expression"]
}


class AuthorizationError(Exception):
    """Custom exception for authorization failures"""
    def __init__(self, message: str, required_roles: List[str] = None):
        self.message = message
        self.required_roles = required_roles
        super().__init__(message)


class AzureTokenVerifier(TokenVerifier):
    """
    Azure AD token verifier that validates JWT tokens and extracts app roles.
    Implements the official MCP TokenVerifier interface for seamless integration.
    """
    
    def __init__(self, tenant_id: str = None, client_id: str = None, enable_auth: bool = True):
        """
        Initialize Azure AD token verifier.
        
        Args:
            tenant_id: Azure AD tenant ID
            client_id: Azure AD application client ID  
            enable_auth: Whether to enable authentication
        """
        self.tenant_id = tenant_id or os.getenv("AZURE_TENANT_ID")
        self.client_id = client_id or os.getenv("AZURE_CLIENT_ID")
        self.enable_auth = enable_auth and os.getenv("ENABLE_AUTH", "true").lower() == "true"
        self._jwks_cache = {}
        
        # Validate required configuration
        if self.enable_auth and (not self.tenant_id or not self.client_id):
            raise ValueError(
                "Azure AD configuration missing. Set AZURE_TENANT_ID and AZURE_CLIENT_ID "
                "environment variables or pass them to constructor."
            )
        
        if not self.enable_auth:
            logger.warning("Authentication is disabled - using mock admin role for all requests")
    
    async def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify JWT token and extract user information.
        
        Args:
            token: JWT access token from Authorization header
            
        Returns:
            Dictionary containing subject, scopes (app roles), and claims
            
        Raises:
            jwt.InvalidTokenError: If token validation fails
            ValueError: If token format is invalid or required claims are missing
        """
        if not self.enable_auth:
            # Return mock admin role for development/testing
            return {
                "subject": "mock_user",
                "scopes": ["MCP.Admin"],
                "claims": {"roles": ["MCP.Admin"], "preferred_username": "mock_user"}
            }
        
        try:
            # Decode header to get key ID
            header = jwt.get_unverified_header(token)
            kid = header.get('kid')
            
            if not kid:
                raise ValueError("Token header missing 'kid' (key ID)")
            
            # Get signing key from Azure AD JWKS endpoint
            signing_key = await self._get_signing_key(kid)
            
            # Decode and verify the token
            payload = jwt.decode(
                token,
                signing_key,
                algorithms=['RS256'],
                audience=self.client_id,
                issuer=f"https://login.microsoftonline.com/{self.tenant_id}/v2.0",
                options={
                    "verify_signature": True,
                    "verify_aud": True,
                    "verify_iat": True,
                    "verify_exp": True,
                    "verify_nbf": True,
                    "verify_iss": True,
                }
            )
            
            # Extract user information
            subject = payload.get('sub') or payload.get('oid') or payload.get('preferred_username')
            if not subject:
                raise ValueError("Token missing required subject identifier")
            
            # Extract app roles (these become scopes in MCP context)
            app_roles = payload.get('roles', [])
            if not isinstance(app_roles, list):
                app_roles = []
            
            # Additional claims for context
            claims = {
                "roles": app_roles,
                "preferred_username": payload.get('preferred_username'),
                "name": payload.get('name'),
                "email": payload.get('email'),
                "tenant_id": payload.get('tid'),
                "app_id": payload.get('appid'),
                "auth_time": payload.get('auth_time'),
                "iat": payload.get('iat'),
                "exp": payload.get('exp'),
            }
            
            # Remove None values from claims
            claims = {k: v for k, v in claims.items() if v is not None}
            
            logger.info(f"Successfully validated token for user: {subject}, roles: {app_roles}")
            
            return {
                "subject": subject,
                "scopes": app_roles,  # App roles become scopes in MCP
                "claims": claims
            }
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            raise jwt.InvalidTokenError("Token has expired")
        except jwt.InvalidAudienceError:
            logger.warning(f"Token audience mismatch. Expected: {self.client_id}")
            raise jwt.InvalidTokenError("Token audience mismatch")
        except jwt.InvalidIssuerError:
            logger.warning(f"Token issuer mismatch")
            raise jwt.InvalidTokenError("Token issuer mismatch")
        except jwt.InvalidSignatureError:
            logger.warning("Token signature verification failed")
            raise jwt.InvalidTokenError("Token signature verification failed")
        except jwt.InvalidTokenError as e:
            logger.warning(f"Token validation failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during token validation: {e}")
            raise jwt.InvalidTokenError(f"Token validation error: {str(e)}")
    
    async def _get_signing_key(self, kid: str) -> bytes:
        """Get JWT signing key from Azure AD JWKS endpoint with caching."""
        # Check cache first
        if kid in self._jwks_cache:
            return self._jwks_cache[kid]
        
        try:
            # Fetch JWKS from Azure AD
            jwks_url = f"https://login.microsoftonline.com/{self.tenant_id}/discovery/v2.0/keys"
            
            response = requests.get(jwks_url, timeout=10)
            response.raise_for_status()
            
            jwks = response.json()
            
            # Find the key with matching kid
            for key in jwks.get('keys', []):
                if key.get('kid') == kid and key.get('kty') == 'RSA':
                    # Convert JWK to PEM format
                    public_key_pem = self._jwk_to_pem(key)
                    
                    # Cache the key for future use
                    self._jwks_cache[kid] = public_key_pem
                    
                    logger.debug(f"Cached new signing key with kid: {kid}")
                    return public_key_pem
            
            raise ValueError(f"Signing key with kid '{kid}' not found in Azure AD JWKS")
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch JWKS from Azure AD: {e}")
            raise ValueError(f"JWKS request failed: {str(e)}")
        except Exception as e:
            logger.error(f"Error processing JWKS response: {e}")
            raise ValueError(f"JWKS processing error: {str(e)}")
    
    def _jwk_to_pem(self, jwk: Dict) -> bytes:
        """Convert JWK (JSON Web Key) to PEM format."""
        try:
            # Validate required JWK fields
            if jwk.get('kty') != 'RSA':
                raise ValueError(f"Unsupported key type: {jwk.get('kty')}")
            
            if 'n' not in jwk or 'e' not in jwk:
                raise ValueError("JWK missing required RSA components (n, e)")
            
            # Extract and decode modulus (n) and exponent (e)
            n_b64 = jwk['n']
            e_b64 = jwk['e']
            
            # Add padding if needed for base64 decoding
            n_b64 += '=' * (4 - len(n_b64) % 4) % 4
            e_b64 += '=' * (4 - len(e_b64) % 4) % 4
            
            n_bytes = base64.urlsafe_b64decode(n_b64)
            e_bytes = base64.urlsafe_b64decode(e_b64)
            
            # Convert to integers
            n_int = int.from_bytes(n_bytes, 'big')
            e_int = int.from_bytes(e_bytes, 'big')
            
            # Create RSA public key
            public_numbers = rsa.RSAPublicNumbers(e_int, n_int)
            public_key = public_numbers.public_key()
            
            # Convert to PEM format
            pem_bytes = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            return pem_bytes
            
        except Exception as e:
            logger.error(f"Failed to convert JWK to PEM: {e}")
            raise ValueError(f"JWK conversion error: {str(e)}")


# Get configuration from environment
tenant_id = os.getenv("AZURE_TENANT_ID")
client_id = os.getenv("AZURE_CLIENT_ID")
enable_auth = os.getenv("ENABLE_AUTH", "true").lower() == "true"
server_url = os.getenv("MCP_SERVER_URL", "https://your-server.azurecontainerapps.io")

# Validate required configuration for OAuth endpoints
if not tenant_id:
    logger.warning("AZURE_TENANT_ID not set - OAuth endpoints will be disabled")
if not server_url:
    raise ValueError("MCP_SERVER_URL is required")

# Initialize the Azure token verifier
token_verifier = AzureTokenVerifier(
    tenant_id=tenant_id,
    client_id=client_id,
    enable_auth=enable_auth
) if enable_auth and tenant_id and client_id else None

# Create auth settings to enable OAuth 2.1 endpoints (/.well-known/oauth-protected-resource)
auth_settings = AuthSettings(
    issuer_url=f"https://login.microsoftonline.com/{tenant_id}/v2.0",
    resource_server_url=server_url,
    required_scopes=["MCP.User"],  # Default minimum scope - enables OAuth endpoints
) if tenant_id else None

# Create FastMCP server with official OAuth 2.1 support
mcp = FastMCP(
    "Calculator",
    token_verifier=token_verifier,  # Handles token validation
    auth=auth_settings              # Enables OAuth 2.1 endpoints automatically
)


def require_roles(required_roles: List[str]):
    """
    Decorator to check if user has required roles for tool access.
    Works with the official MCP SDK auth framework.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get context from kwargs
            ctx = kwargs.get('ctx')
            if not ctx:
                raise AuthorizationError("No request context available")
            
            # If auth is disabled, allow access
            if not enable_auth or not token_verifier:
                logger.debug(f"Authentication disabled, allowing access to {func.__name__}")
                return await func(*args, **kwargs)
            
            # Check if token info is available (provided by SDK)
            if not hasattr(ctx, 'token_info') or not ctx.token_info:
                raise AuthorizationError("No authentication information available")
            
            # Check permissions using the token info
            user_roles = ctx.token_info.get("scopes", []) if isinstance(ctx.token_info, dict) else []
            if not any(role in user_roles for role in required_roles):
                logger.warning(f"Access denied to {func.__name__}. User roles: {user_roles}, Required: {required_roles}")
                raise AuthorizationError(
                    f"Insufficient permissions. Required roles: {required_roles}",
                    required_roles
                )
            
            subject = ctx.token_info.get("subject", "unknown") if isinstance(ctx.token_info, dict) else "unknown"
            logger.info(f"Access granted to {func.__name__}. User: {subject}")
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def get_accessible_tools(ctx: Context) -> List[str]:
    """Get list of tools accessible to the user based on their roles."""
    if not enable_auth or not token_verifier:
        return list(ROLE_PERMISSIONS["MCP.Admin"])
    
    if not hasattr(ctx, 'token_info') or not ctx.token_info:
        return []
    
    user_roles = ctx.token_info.get("scopes", []) if isinstance(ctx.token_info, dict) else []
    accessible_tools = set()
    
    for role in user_roles:
        if role in ROLE_PERMISSIONS:
            accessible_tools.update(ROLE_PERMISSIONS[role])
    
    return list(accessible_tools)


# Tool implementations with role-based authorization

@mcp.tool()
@require_roles(["MCP.User", "MCP.Admin"])
async def add(a: float, b: float, ctx: Context) -> Dict[str, Any]:
    """
    Add two numbers together.
    Requires: MCP.User or MCP.Admin role
    
    Args:
        a: First number
        b: Second number
    
    Returns:
        Dictionary containing the operation, operands, and result
    """
    result = a + b
    user = ctx.token_info.get("subject", "unknown") if hasattr(ctx, 'token_info') and ctx.token_info else "unknown"
    return {
        "operation": "addition",
        "operands": [a, b],
        "result": result,
        "expression": f"{a} + {b} = {result}",
        "user": user
    }


@mcp.tool()
@require_roles(["MCP.User", "MCP.Admin"])
async def subtract(a: float, b: float, ctx: Context) -> Dict[str, Any]:
    """
    Subtract the second number from the first number.
    Requires: MCP.User or MCP.Admin role
    
    Args:
        a: First number (minuend)
        b: Second number (subtrahend)
    
    Returns:
        Dictionary containing the operation, operands, and result
    """
    result = a - b
    user = ctx.token_info.get("subject", "unknown") if hasattr(ctx, 'token_info') and ctx.token_info else "unknown"
    return {
        "operation": "subtraction",
        "operands": [a, b],
        "result": result,
        "expression": f"{a} - {b} = {result}",
        "user": user
    }


@mcp.tool()
@require_roles(["MCP.Admin"])
async def multiply(a: float, b: float, ctx: Context) -> Dict[str, Any]:
    """
    Multiply two numbers together.
    Requires: MCP.Admin role
    
    Args:
        a: First number
        b: Second number
    
    Returns:
        Dictionary containing the operation, operands, and result
    """
    result = a * b
    user = ctx.token_info.get("subject", "unknown") if hasattr(ctx, 'token_info') and ctx.token_info else "unknown"
    return {
        "operation": "multiplication",
        "operands": [a, b],
        "result": result,
        "expression": f"{a} × {b} = {result}",
        "user": user
    }


@mcp.tool()
@require_roles(["MCP.Admin"])
async def divide(a: float, b: float, ctx: Context) -> Dict[str, Any]:
    """
    Divide the first number by the second number.
    Requires: MCP.Admin role
    
    Args:
        a: Dividend (number to be divided)
        b: Divisor (number to divide by)
    
    Returns:
        Dictionary containing the operation, operands, and result
    
    Raises:
        ValueError: If attempting to divide by zero
    """
    if b == 0:
        raise ValueError("Cannot divide by zero")
    
    result = a / b
    user = getattr(ctx.token_info, 'subject', 'unknown') if hasattr(ctx, 'token_info') and ctx.token_info else 'unknown'
    return {
        "operation": "division",
        "operands": [a, b],
        "result": result,
        "expression": f"{a} ÷ {b} = {result}",
        "user": user
    }


@mcp.tool()
@require_roles(["MCP.Admin"])
async def calculate_expression(expression: str, ctx: Context) -> Dict[str, Any]:
    """
    Evaluate a basic mathematical expression.
    Requires: MCP.Admin role
    
    Args:
        expression: Mathematical expression as a string (e.g., "2 + 3 * 4")
    
    Returns:
        Dictionary containing the expression and result
    
    Note:
        Only supports basic arithmetic operations (+, -, *, /) and parentheses.
        Uses eval() for simplicity - NOT recommended for production use.
    """
    try:
        # Sanitize the expression to only allow basic arithmetic
        allowed_chars = set('0123456789+-*/.() ')
        if not all(c in allowed_chars for c in expression):
            raise ValueError("Expression contains invalid characters")
        
        # Evaluate the expression
        result = eval(expression)
        
        user = ctx.token_info.get("subject", "unknown") if hasattr(ctx, 'token_info') and ctx.token_info else "unknown"
        return {
            "operation": "expression_evaluation",
            "expression": expression,
            "result": result,
            "formatted": f"{expression} = {result}",
            "user": user
        }
    except ZeroDivisionError:
        raise ValueError("Division by zero in expression")
    except Exception as e:
        raise ValueError(f"Invalid expression: {str(e)}")


@mcp.resource("calculator://info")
async def get_calculator_info() -> str:
    """
    Get information about the calculator server capabilities.
    Shows only tools accessible to the current user.
    
    Returns:
        Information about available operations based on user permissions
    """
    # Get accessible tools based on user's token
    # Note: For resources, we can't directly access the context
    # This would need to be handled differently in a production scenario
    accessible_tools = list(ROLE_PERMISSIONS["MCP.Admin"])  # Default to admin for demo
    
    user_info = "User: Resource context not available in FastMCP"
    
    base_info = f"""
Calculator MCP Server Information (Official OAuth 2.1 SDK)
=========================================================

Authentication: {"Enabled" if enable_auth else "Disabled (Demo Mode)"}
{user_info}

Your accessible operations:
"""
    
    tool_descriptions = {
        "add": "- add(a, b): Add two numbers",
        "subtract": "- subtract(a, b): Subtract b from a", 
        "multiply": "- multiply(a, b): Multiply two numbers",
        "divide": "- divide(a, b): Divide a by b (b cannot be zero)",
        "calculate_expression": "- calculate_expression(expression): Evaluate a mathematical expression"
    }
    
    available_ops = []
    for tool in accessible_tools:
        if tool in tool_descriptions:
            available_ops.append(tool_descriptions[tool])
    
    if not available_ops:
        available_ops.append("- No operations available (insufficient permissions)")
    
    role_info = """

Role-Based Access Control:
- MCP.User: Basic operations (add, subtract)
- MCP.Admin: All operations (add, subtract, multiply, divide, calculate_expression)

OAuth 2.1 Features (Official SDK):
- Automatic /.well-known/oauth-protected-resource endpoint (RFC 9728)
- Proper WWW-Authenticate headers on 401 responses
- Azure AD integration with JWKS validation
- Token audience and issuer validation
- App roles as scopes mapping

All operations return detailed results including the operation type,
operands, result, and the authenticated user.
"""
    
    return base_info + "\n".join(available_ops) + role_info


@mcp.prompt("math_helper")
async def math_helper_prompt() -> str:
    """
    A prompt template for helping with math problems.
    Customized based on user's accessible tools.
    
    Returns:
        A prompt that guides users on how to use the calculator
    """
    # Get accessible tools for the current user
    # Note: For prompts, we can't directly access the context
    # This would need to be handled differently in a production scenario
    accessible_tools = list(ROLE_PERMISSIONS["MCP.Admin"])  # Default to admin for demo
    
    base_prompt = """
I'm a calculator assistant with OAuth 2.1 role-based access control.

Your available operations based on your authenticated roles:
"""
    
    tool_descriptions = {
        "add": "1. Addition: add(a, b)",
        "subtract": "2. Subtraction: subtract(a, b)",
        "multiply": "3. Multiplication: multiply(a, b)", 
        "divide": "4. Division: divide(a, b)",
        "calculate_expression": "5. Expression evaluation: calculate_expression(\"expression\")"
    }
    
    available_ops = []
    for tool in accessible_tools:
        if tool in tool_descriptions:
            available_ops.append(tool_descriptions[tool])
    
    if not available_ops:
        return base_prompt + "\nNo operations available. Please ensure you have the required Azure AD app roles assigned."
    
    return base_prompt + "\n".join(available_ops) + "\n\nWhat mathematical operation would you like me to perform?"


# Error handler for authorization errors
@mcp.exception_handler(AuthorizationError)
async def handle_authorization_error(error: AuthorizationError) -> Dict[str, Any]:
    """Handle authorization errors with user-friendly messages"""
    return {
        "error": "Authorization Failed",
        "message": error.message,
        "required_roles": error.required_roles or [],
        "help": "Contact your administrator to assign the required Azure AD app roles for this operation.",
        "oauth_endpoints": {
            "protected_resource_metadata": f"{server_url}/.well-known/oauth-protected-resource",
            "authorization_server": f"https://login.microsoftonline.com/{tenant_id}/v2.0" if tenant_id else None
        }
    }


if __name__ == "__main__":
    # Get configuration from environment variables
    transport = os.getenv("MCP_TRANSPORT", "streamable-http")
    
    print(f"Starting Calculator MCP Server with Official OAuth 2.1 SDK...")
    print(f"Transport: {transport}")
    print(f"Authentication: {'Enabled' if enable_auth else 'Disabled (Demo Mode)'}")
    
    if enable_auth and tenant_id:
        print(f"Azure Tenant ID: {tenant_id}")
        print(f"Azure Client ID: {client_id}")
        print(f"Issuer URL: https://login.microsoftonline.com/{tenant_id}/v2.0")
        print(f"Resource Server URL: {server_url}")
        print("Role Permissions:")
        for role, tools in ROLE_PERMISSIONS.items():
            print(f"  {role}: {', '.join(tools)}")
    
    if transport == "streamable-http":
        host = os.getenv("MCP_HOST", "0.0.0.0")
        port = int(os.getenv("MCP_PORT", "8000"))
        
        print(f"Server will listen on {host}:{port}")
        print("OAuth 2.1 Compliant Endpoints (Automatic via Official SDK):")
        print(f"  - MCP endpoint: http://{host}:{port}/mcp")
        if auth_settings:
            print(f"  - Protected Resource Metadata: http://{host}:{port}/.well-known/oauth-protected-resource")
            print(f"  - Authorization Server: https://login.microsoftonline.com/{tenant_id}/v2.0")
        print(f"  - Health check: http://{host}:{port}/health")
        print("\nThe server automatically implements RFC 9728 (Protected Resource Metadata)")
        print("and provides proper WWW-Authenticate headers via the official MCP SDK.")
        
        # Run with streamable HTTP transport
        mcp.run(transport="streamable-http")
    else:
        print("Only streamable-http transport is supported in this version")
        exit(1)
