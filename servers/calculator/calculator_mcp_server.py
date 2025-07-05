"""
Calculator MCP Server with Official SDK Authentication
Refactored to use the official MCP SDK authentication framework properly
"""

import os
import logging
from typing import Any, Dict, List
from mcp.server.fastmcp import FastMCP, Context
from mcp.server.auth.settings import AuthSettings
from azure_token_verifier import AzureTokenVerifier

# Configure logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Get configuration from environment
tenant_id = os.getenv("AZURE_TENANT_ID")
client_id = os.getenv("AZURE_CLIENT_ID")
enable_auth = os.getenv("ENABLE_AUTH", "true").lower() == "true"
server_url = os.getenv("MCP_SERVER_URL", "https://your-server.azurecontainerapps.io")

# Role-based tool permissions
ROLE_PERMISSIONS = {
    "MCP.User": ["add", "subtract"],
    "MCP.Admin": ["add", "subtract", "multiply", "divide", "calculate_expression"]
}

# Initialize the Azure token verifier
token_verifier = AzureTokenVerifier(
    tenant_id=tenant_id,
    client_id=client_id,
    enable_auth=enable_auth
) if enable_auth else None

# Create AuthSettings for the official SDK
auth_settings = None
if enable_auth and tenant_id:
    auth_settings = AuthSettings(
        issuer_url=f"https://login.microsoftonline.com/{tenant_id}/v2.0",
        resource_server_url=server_url,
        required_scopes=["MCP.User"],  # Default minimum scope
    )

# Create FastMCP server with official auth support
# The SDK will automatically handle /.well-known/oauth-protected-resource endpoint
mcp = FastMCP(
    "Calculator",
    token_verifier=token_verifier,
    auth=auth_settings
)


class AuthorizationError(Exception):
    """Custom exception for authorization failures"""
    def __init__(self, message: str, required_roles: List[str] = None):
        self.message = message
        self.required_roles = required_roles
        super().__init__(message)


def check_tool_permission(token_info, required_roles: List[str]) -> bool:
    """
    Check if the user has permission to access a tool based on their roles.
    
    Args:
        token_info: Token information from the verifier
        required_roles: List of roles that can access the tool
        
    Returns:
        True if user has permission, False otherwise
    """
    if not token_info:
        return not enable_auth  # Allow if auth is disabled
    
    user_roles = token_info.scopes or []
    return any(role in user_roles for role in required_roles)


def get_accessible_tools(token_info) -> List[str]:
    """
    Get list of tools accessible to the user based on their roles.
    
    Args:
        token_info: Token information from the verifier
        
    Returns:
        List of tool names the user can access
    """
    if not token_info:
        return list(ROLE_PERMISSIONS["MCP.Admin"]) if not enable_auth else []
    
    user_roles = token_info.scopes or []
    accessible_tools = set()
    
    for role in user_roles:
        if role in ROLE_PERMISSIONS:
            accessible_tools.update(ROLE_PERMISSIONS[role])
    
    return list(accessible_tools)


def require_roles(required_roles: List[str]):
    """
    Decorator to check if user has required roles for tool access.
    Works with the official MCP SDK auth framework.
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Get context from kwargs
            ctx = kwargs.get('ctx')
            if not ctx:
                raise AuthorizationError("No request context available")
            
            # If auth is disabled, allow access
            if not enable_auth:
                logger.debug(f"Authentication disabled, allowing access to {func.__name__}")
                return await func(*args, **kwargs)
            
            # The official SDK populates ctx.session with authentication info
            # Access token info through the session
            token_info = getattr(ctx.session, 'token_info', None) if hasattr(ctx, 'session') else None
            
            # Check permissions using the token info
            if not check_tool_permission(token_info, required_roles):
                user_roles = token_info.scopes if token_info else []
                logger.warning(f"Access denied to {func.__name__}. User roles: {user_roles}, Required: {required_roles}")
                raise AuthorizationError(
                    f"Insufficient permissions. Required roles: {required_roles}",
                    required_roles
                )
            
            subject = token_info.subject if token_info else "unknown"
            logger.info(f"Access granted to {func.__name__}. User: {subject}")
            return await func(*args, **kwargs)
        return wrapper
    return decorator


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
    token_info = getattr(ctx.session, 'token_info', None) if hasattr(ctx, 'session') else None
    user = token_info.subject if token_info else 'unknown'
    
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
    token_info = getattr(ctx.session, 'token_info', None) if hasattr(ctx, 'session') else None
    user = token_info.subject if token_info else 'unknown'
    
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
    token_info = getattr(ctx.session, 'token_info', None) if hasattr(ctx, 'session') else None
    user = token_info.subject if token_info else 'unknown'
    
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
    token_info = getattr(ctx.session, 'token_info', None) if hasattr(ctx, 'session') else None
    user = token_info.subject if token_info else 'unknown'
    
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
        
        token_info = getattr(ctx.session, 'token_info', None) if hasattr(ctx, 'session') else None
        user = token_info.subject if token_info else 'unknown'
        
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
async def get_calculator_info(ctx: Context) -> str:
    """
    Get information about the calculator server capabilities.
    Shows only tools accessible to the current user.
    
    Returns:
        Information about available operations based on user permissions
    """
    # Get token info from session
    token_info = getattr(ctx.session, 'token_info', None) if hasattr(ctx, 'session') else None
    
    # Get accessible tools based on user's token
    accessible_tools = get_accessible_tools(token_info)
    
    if token_info:
        user_info = f"User: {token_info.subject}\nRoles: {', '.join(token_info.scopes or [])}"
    else:
        user_info = "User: Not authenticated" if enable_auth else "User: Mock user (auth disabled)"
    
    base_info = f"""
Calculator MCP Server Information (OAuth 2.1 Compliant with Official SDK)
========================================================================

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

OAuth 2.1 Features (Official SDK Implementation):
- Automatic Protected Resource Metadata (RFC 9728)
- Automatic /.well-known/oauth-protected-resource endpoint
- Automatic WWW-Authenticate headers on 401 responses
- Azure AD integration with JWKS validation
- Token audience and issuer validation
- App roles as scopes mapping

All operations return detailed results including the operation type,
operands, result, and the authenticated user.
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
    # Get token info from session
    token_info = getattr(ctx.session, 'token_info', None) if hasattr(ctx, 'session') else None
    
    # Get accessible tools for the current user
    accessible_tools = get_accessible_tools(token_info)
    
    base_prompt = """
I'm a calculator assistant with OAuth 2.1 role-based access control using the official MCP SDK.

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
        "current_roles": "Check your token claims for current role assignments"
    }


if __name__ == "__main__":
    print(f"Starting Calculator MCP Server with Official OAuth 2.1 SDK Support...")
    print(f"Authentication: {'Enabled' if enable_auth else 'Disabled (Demo Mode)'}")
    
    if enable_auth and tenant_id:
        print(f"Azure Tenant ID: {tenant_id}")
        print(f"Azure Client ID: {client_id}")
        print(f"Issuer URL: https://login.microsoftonline.com/{tenant_id}/v2.0")
        print(f"Resource Server URL: {server_url}")
        print("Role Permissions:")
        for role, tools in ROLE_PERMISSIONS.items():
            print(f"  {role}: {', '.join(tools)}")
        print("\nOAuth 2.1 Endpoints (Automatically handled by SDK):")
        print(f"  - Protected Resource Metadata: {server_url}/.well-known/oauth-protected-resource")
        print(f"  - MCP endpoint: {server_url}/mcp")
        print(f"  - Health check: {server_url}/health")
        print("\nThe official MCP SDK automatically implements:")
        print("  - RFC 9728 (Protected Resource Metadata)")
        print("  - WWW-Authenticate headers on 401 responses")
        print("  - OAuth 2.1 Resource Server functionality")
    
    # Run with the official SDK's transport handling
    # The SDK automatically manages endpoints and OAuth compliance
    mcp.run()
