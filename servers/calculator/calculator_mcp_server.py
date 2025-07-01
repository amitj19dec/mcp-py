"""
Basic Calculator MCP Server (Azure Container Instance Ready) with Tool-Level Authorization
A simple MCP server that provides basic arithmetic operations with JWT-based app role authorization.
Supports streamable-http transport with role-based access control using FastMCP Context.
"""

import os
import jwt
import logging
from typing import Any, Dict, List, Optional
from functools import wraps
from mcp.server.fastmcp import FastMCP, Context
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import requests
import base64

# Configure logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Role-based tool permissions
ROLE_PERMISSIONS = {
    "MCP.User": ["add", "subtract"],
    "MCP.Admin": ["add", "subtract", "multiply", "divide", "calculate_expression"]
}

# Initialize FastMCP server
mcp = FastMCP("Calculator")


class AuthorizationError(Exception):
    """Custom exception for authorization failures"""
    def __init__(self, message: str, required_roles: List[str] = None):
        self.message = message
        self.required_roles = required_roles
        super().__init__(message)


class AuthorizationMiddleware:
    """Handles JWT token validation and app role extraction"""
    
    def __init__(self, tenant_id: str = None, client_id: str = None):
        self.tenant_id = tenant_id or os.getenv("AZURE_TENANT_ID")
        self.client_id = client_id or os.getenv("AZURE_CLIENT_ID")
        self.enable_auth = os.getenv("ENABLE_AUTH", "false").lower() == "true"
        self._jwks_cache = {}
        
        if self.enable_auth and (not self.tenant_id or not self.client_id):
            logger.warning("Authentication enabled but missing Azure AD configuration")
    
    def extract_app_roles(self, token: str) -> List[str]:
        """Extract app roles from JWT token"""
        if not self.enable_auth:
            # If auth is disabled, return admin role for demo purposes
            return ["MCP.Admin"]
        
        try:
            # Decode without verification first to get header
            header = jwt.get_unverified_header(token)
            
            # Get signing key
            key = self._get_signing_key(header.get('kid'))
            
            # Decode and verify token
            payload = jwt.decode(
                token,
                key,
                algorithms=['RS256'],
                audience=self.client_id,
                issuer=f"https://login.microsoftonline.com/{self.tenant_id}/v2.0"
            )
            
            # Extract app roles from token
            roles = payload.get('roles', [])
            logger.info(f"Successfully extracted roles from token: {roles}")
            return roles
            
        except jwt.InvalidTokenError as e:
            logger.warning(f"Token validation failed: {e}")
            return []
        except Exception as e:
            logger.error(f"Error extracting app roles: {e}")
            return []
    
    def _get_signing_key(self, kid: str):
        """Get JWT signing key from Azure AD JWKS endpoint"""
        if not self.tenant_id:
            raise ValueError("Tenant ID not configured")
        
        # Cache JWKS for performance
        if kid in self._jwks_cache:
            return self._jwks_cache[kid]
        
        try:
            jwks_url = f"https://login.microsoftonline.com/{self.tenant_id}/discovery/v2.0/keys"
            response = requests.get(jwks_url, timeout=10)
            response.raise_for_status()
            
            jwks = response.json()
            
            # Find the key with matching kid
            for key in jwks.get('keys', []):
                if key.get('kid') == kid:
                    # Convert JWK to PEM format
                    public_key = self._jwk_to_pem(key)
                    self._jwks_cache[kid] = public_key
                    return public_key
            
            raise ValueError(f"Key with kid '{kid}' not found in JWKS")
            
        except Exception as e:
            logger.error(f"Failed to retrieve signing key: {e}")
            raise
    
    def _jwk_to_pem(self, jwk: Dict) -> str:
        """Convert JWK to PEM format"""
        try:
            # Extract n and e from JWK
            n = base64.urlsafe_b64decode(jwk['n'] + '==')
            e = base64.urlsafe_b64decode(jwk['e'] + '==')
            
            # Convert to integers
            n_int = int.from_bytes(n, 'big')
            e_int = int.from_bytes(e, 'big')
            
            # Create RSA public key
            public_key = rsa.RSAPublicNumbers(e_int, n_int).public_key()
            
            # Convert to PEM
            pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            return pem
            
        except Exception as e:
            logger.error(f"Failed to convert JWK to PEM: {e}")
            raise


# Initialize authorization middleware
auth_middleware = AuthorizationMiddleware()


def require_app_role(required_roles: List[str]):
    """Decorator to check if user has required app roles for tool access"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not auth_middleware.enable_auth:
                logger.debug(f"Authentication disabled, allowing access to {func.__name__}")
                return await func(*args, **kwargs)
            
            # Get FastMCP context from kwargs
            ctx = kwargs.get('ctx')
            if not ctx:
                logger.error(f"No FastMCP context found for {func.__name__}")
                raise AuthorizationError("Internal error: No request context available")
            
            # Extract authorization header from FastMCP context
            auth_header = None
            try:
                # Try to access request headers through FastMCP context
                if hasattr(ctx, 'request') and hasattr(ctx.request, 'headers'):
                    auth_header = ctx.request.headers.get('Authorization')
                elif hasattr(ctx, '_request') and hasattr(ctx._request, 'headers'):
                    auth_header = ctx._request.headers.get('Authorization')
                else:
                    logger.warning(f"Cannot access request headers for {func.__name__}")
            except Exception as e:
                logger.error(f"Error accessing request headers for {func.__name__}: {e}")
            
            if not auth_header or not auth_header.startswith('Bearer '):
                logger.warning(f"Missing or invalid authorization header for {func.__name__}")
                raise AuthorizationError("Missing or invalid authorization header")
            
            token = auth_header[7:]  # Remove 'Bearer ' prefix
            user_roles = auth_middleware.extract_app_roles(token)
            
            # Check if user has any of the required roles
            if not any(role in user_roles for role in required_roles):
                logger.warning(f"Access denied to {func.__name__}. User roles: {user_roles}, Required: {required_roles}")
                raise AuthorizationError(
                    f"Insufficient permissions. Required roles: {required_roles}",
                    required_roles
                )
            
            logger.info(f"Access granted to {func.__name__}. User roles: {user_roles}")
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def get_user_accessible_tools(ctx: Context = None) -> List[str]:
    """Get list of tools accessible to current user"""
    if not auth_middleware.enable_auth:
        return list(ROLE_PERMISSIONS["MCP.Admin"])
    
    if not ctx:
        return []
    
    # Extract authorization header from context
    auth_header = None
    try:
        if hasattr(ctx, 'request') and hasattr(ctx.request, 'headers'):
            auth_header = ctx.request.headers.get('Authorization')
        elif hasattr(ctx, '_request') and hasattr(ctx._request, 'headers'):
            auth_header = ctx._request.headers.get('Authorization')
    except Exception:
        pass
    
    if not auth_header or not auth_header.startswith('Bearer '):
        return []
    
    token = auth_header[7:]
    user_roles = auth_middleware.extract_app_roles(token)
    
    accessible_tools = set()
    for role in user_roles:
        if role in ROLE_PERMISSIONS:
            accessible_tools.update(ROLE_PERMISSIONS[role])
    
    return list(accessible_tools)


# Tool implementations with role-based authorization

@mcp.tool()
@require_app_role(["MCP.User", "MCP.Admin"])
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
    return {
        "operation": "addition",
        "operands": [a, b],
        "result": result,
        "expression": f"{a} + {b} = {result}"
    }


@mcp.tool()
@require_app_role(["MCP.User", "MCP.Admin"])
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
    return {
        "operation": "subtraction",
        "operands": [a, b],
        "result": result,
        "expression": f"{a} - {b} = {result}"
    }


@mcp.tool()
@require_app_role(["MCP.Admin"])
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
    return {
        "operation": "multiplication",
        "operands": [a, b],
        "result": result,
        "expression": f"{a} × {b} = {result}"
    }


@mcp.tool()
@require_app_role(["MCP.Admin"])
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
    return {
        "operation": "division",
        "operands": [a, b],
        "result": result,
        "expression": f"{a} ÷ {b} = {result}"
    }


@mcp.tool()
@require_app_role(["MCP.Admin"])
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
        
        return {
            "operation": "expression_evaluation",
            "expression": expression,
            "result": result,
            "formatted": f"{expression} = {result}"
        }
    except ZeroDivisionError:
        raise ValueError("Division by zero in expression")
    except Exception as e:
        raise ValueError(f"Invalid expression: {str(e)}")


@mcp.resource("calculator://info")
async def get_calculator_info(ctx: Context) -> str:
    """
    Get information about the calculator server capabilities.
    Shows only tools accessible to the current user.
    
    Returns:
        Information about available operations based on user permissions
    """
    accessible_tools = get_user_accessible_tools(ctx)
    
    base_info = """
Calculator MCP Server Information (Role-Based Access)
===================================================

Authentication: {}
Your accessible operations:
""".format("Enabled" if auth_middleware.enable_auth else "Disabled (Demo Mode)")
    
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

All operations return detailed results including the operation type,
operands, result, and a formatted expression.
"""
    
    return base_info + "\n".join(available_ops) + role_info


@mcp.prompt("math_helper")
async def math_helper_prompt(ctx: Context) -> str:
    """
    A prompt template for helping with math problems.
    Customized based on user's accessible tools.
    
    Returns:
        A prompt that guides users on how to use the calculator
    """
    accessible_tools = get_user_accessible_tools(ctx)
    
    base_prompt = """
I'm a calculator assistant with role-based access control.

Your available operations based on your permissions:
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
        return base_prompt + "\nNo operations available. Please contact your administrator for access."
    
    return base_prompt + "\n".join(available_ops) + "\n\nWhat mathematical operation would you like me to perform?"


# Custom error handler for authorization errors
@mcp.exception_handler(AuthorizationError)
async def handle_authorization_error(error: AuthorizationError) -> Dict[str, Any]:
    """Handle authorization errors with user-friendly messages"""
    return {
        "error": "Authorization Failed",
        "message": error.message,
        "required_roles": error.required_roles or [],
        "help": "Contact your administrator to request the required roles for this operation."
    }


if __name__ == "__main__":
    # Get configuration from environment variables
    transport = os.getenv("MCP_TRANSPORT", "streamable-http")
    
    print(f"Starting Calculator MCP Server with Authentication...")
    print(f"Transport: {transport}")
    print(f"Authentication: {'Enabled' if auth_middleware.enable_auth else 'Disabled (Demo Mode)'}")
    
    if auth_middleware.enable_auth:
        print(f"Azure Tenant ID: {auth_middleware.tenant_id}")
        print(f"Azure Client ID: {auth_middleware.client_id}")
        print("Role Permissions:")
        for role, tools in ROLE_PERMISSIONS.items():
            print(f"  {role}: {', '.join(tools)}")
    
    if transport == "streamable-http":
        host = os.getenv("MCP_HOST", "0.0.0.0")
        port = int(os.getenv("MCP_PORT", "8000"))
        
        print(f"Server will listen on {host}:{port}")
        print("Endpoints available:")
        print(f"  - Health check: http://{host}:{port}/health")
        print(f"  - MCP endpoint: http://{host}:{port}/mcp")
        print("\nNote: For full OAuth 2.1 compliance (RFC 9728), consider implementing")
        print("the /.well-known/oauth-protected-resource endpoint in production.")
        
        # Run with streamable HTTP transport
        mcp.run(transport="streamable-http")
    else:
        print("Only streamable-http transport is supported in this version")
        exit(1)
