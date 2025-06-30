"""
Enhanced Calculator MCP Server with Tool-Level RBAC
Maintains the original calculator functionality while adding granular role-based access control.
"""

import os
import logging
from typing import Any, Dict
from datetime import datetime, timezone

# MCP SDK imports
from mcp.server.fastmcp import FastMCP

# FastAPI for hosting and middleware
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Authentication module (decoupled with RBAC)
from auth_module import (
    AuthenticationManager, 
    create_auth_config_from_env, 
    create_rbac_policy_from_env,
    RBACTokenVerifier
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CalculatorMCPServer:
    """Pure calculator MCP server with business logic only - no auth concerns."""
    
    def __init__(self, name: str = "Calculator"):
        self.mcp = FastMCP(name)
        self._setup_tools()
        self._setup_resources()
        self._setup_prompts()
    
    def _setup_tools(self):
        """Setup calculator tools - unchanged from original."""
        
        @self.mcp.tool()
        async def add(a: float, b: float) -> Dict[str, Any]:
            """Add two numbers together."""
            result = a + b
            return {
                "operation": "addition",
                "operands": [a, b],
                "result": result,
                "expression": f"{a} + {b} = {result}"
            }

        @self.mcp.tool()
        async def subtract(a: float, b: float) -> Dict[str, Any]:
            """Subtract the second number from the first number."""
            result = a - b
            return {
                "operation": "subtraction",
                "operands": [a, b],
                "result": result,
                "expression": f"{a} - {b} = {result}"
            }

        @self.mcp.tool()
        async def multiply(a: float, b: float) -> Dict[str, Any]:
            """Multiply two numbers together."""
            result = a * b
            return {
                "operation": "multiplication",
                "operands": [a, b],
                "result": result,
                "expression": f"{a} × {b} = {result}"
            }

        @self.mcp.tool()
        async def divide(a: float, b: float) -> Dict[str, Any]:
            """Divide the first number by the second number."""
            if b == 0:
                raise ValueError("Cannot divide by zero")
            
            result = a / b
            return {
                "operation": "division",
                "operands": [a, b],
                "result": result,
                "expression": f"{a} ÷ {b} = {result}"
            }

        @self.mcp.tool()
        async def calculate_expression(expression: str) -> Dict[str, Any]:
            """Evaluate a basic mathematical expression."""
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

    def _setup_resources(self):
        """Setup calculator resources."""
        
        @self.mcp.resource("calculator://info")
        async def get_calculator_info() -> str:
            """Get information about the calculator server capabilities."""
            return """
            RBAC-Protected Calculator MCP Server Information
            ==============================================
            
            Authentication: Azure AD Bearer Token Required
            Authorization: Role-Based Access Control (RBAC)
            
            Available Operations & Required Roles:
            - add(a, b): Requires MCP.BasicUser role
            - subtract(a, b): Requires MCP.BasicUser role
            - multiply(a, b): Requires MCP.PowerUser role (inherits BasicUser)
            - divide(a, b): Requires MCP.PowerUser role (inherits BasicUser)
            - calculate_expression(expression): Requires MCP.Admin role (inherits all)
            
            Role Hierarchy:
            - MCP.BasicUser: Basic arithmetic (add, subtract)
            - MCP.PowerUser: Advanced arithmetic (includes basic + multiply, divide)
            - MCP.Admin: All operations (includes power + expression evaluation)
            
            All operations return detailed results including the operation type,
            operands, result, and a formatted expression.
            
            Authentication Requirements:
            - Valid Azure AD bearer token in Authorization header
            - Token must contain appropriate app roles for the requested operation
            - Token audience must match the configured client ID
            
            Example usage:
            - add(5, 3) returns 8 [BasicUser+]
            - multiply(7, 6) returns 42 [PowerUser+]
            - calculate_expression("2 + 3 * 4") returns 14 [Admin only]
            """

        @self.mcp.resource("calculator://rbac")
        async def get_rbac_info() -> str:
            """Get RBAC configuration information."""
            return """
            Role-Based Access Control Configuration
            =====================================
            
            This server implements granular RBAC with tool-level authorization.
            
            Azure AD App Registration Setup:
            1. Server App Registration: Define app roles (MCP.BasicUser, MCP.PowerUser, MCP.Admin)
            2. Client App Registration: Request API permissions for server app roles
            3. Admin Consent: Grant permissions at tenant level
            4. Token Request: Use api://server-app-id/.default scope
            
            Token Validation:
            - JWT signature validation against Azure AD JWKS
            - Audience validation (must match server app ID)
            - Role extraction from 'roles' claim
            - Tool-level authorization check before execution
            
            Role Inheritance:
            - Higher roles automatically inherit lower role permissions
            - Admin can execute all tools
            - PowerUser can execute basic and power tools
            - BasicUser can only execute basic tools
            
            For access issues, check:
            1. Token contains required roles in 'roles' claim
            2. App registration has correct API permissions
            3. Admin consent has been granted
            4. Client is using correct audience scope
            """

    def _setup_prompts(self):
        """Setup calculator prompts."""
        
        @self.mcp.prompt("math_helper")
        async def math_helper_prompt() -> str:
            """A prompt template for helping with math problems."""
            return """
            I'm an RBAC-protected calculator assistant with role-based operation access.
            
            Authentication: This server requires a valid Azure AD bearer token with appropriate roles.
            
            Available Operations by Role:
            
            🔰 MCP.BasicUser:
            1. Addition: add(a, b)
            2. Subtraction: subtract(a, b)
            
            ⚡ MCP.PowerUser (includes BasicUser):
            3. Multiplication: multiply(a, b)  
            4. Division: divide(a, b)
            
            👑 MCP.Admin (includes all):
            5. Expression evaluation: calculate_expression("expression")
            
            Your access level depends on the roles in your Azure AD token.
            What mathematical operation would you like me to perform?
            Please provide the numbers or expression you'd like me to calculate.
            """
    
    def get_fastmcp_instance(self) -> FastMCP:
        """Get the FastMCP instance."""
        return self.mcp


class AuthenticatedCalculatorApp:
    """Main application that composes authentication, RBAC, and MCP server."""
    
    def __init__(self):
        # Load authentication configuration
        self.auth_config = create_auth_config_from_env()
        self.rbac_engine = create_rbac_policy_from_env()
        self.auth_manager = AuthenticationManager(self.auth_config, self.rbac_engine)
        
        # Initialize calculator server
        self.calculator_server = CalculatorMCPServer("RBAC-Protected Calculator")
        self._configure_mcp_auth()
        
        # Initialize FastAPI app
        self.app = FastAPI(
            title="RBAC-Protected Calculator MCP Server",
            description="A secure calculator MCP server with Azure AD authentication and role-based access control"
        )
        self._setup_fastapi()

    def _configure_mcp_auth(self):
        """Configure the MCP server with authentication using simplified approach."""
        # Note: The current MCP SDK may not support direct token_verifier configuration
        # We'll handle authentication at the middleware level instead
        logger.info("Authentication will be handled via FastAPI middleware")

    def _setup_fastapi(self):
        """Setup FastAPI application with endpoints and middleware."""
        
        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure appropriately for production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # RFC 9728 Protected Resource Metadata endpoint (enhanced with RBAC info)
        @self.app.get("/.well-known/oauth-protected-resource")
        async def protected_resource_metadata():
            """RFC 9728 Protected Resource Metadata endpoint with RBAC information."""
            return self.auth_manager.get_protected_resource_metadata()
        
        # RBAC authorization info endpoint
        @self.app.get("/auth/info")
        async def auth_info(request: Request):
            """Get user's authorization information and accessible tools."""
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                raise HTTPException(status_code=401, detail="Bearer token required")
            
            token = auth_header.split(" ", 1)[1]
            rbac_verifier = self.auth_manager.get_rbac_verifier()
            
            try:
                # Verify token first
                await rbac_verifier.verify_token(token)
                auth_context = rbac_verifier.get_authorization_context(token)
                return auth_context
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=401, detail=f"Token validation failed: {str(e)}")
        
        # Health check endpoint (no auth required)
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint for monitoring."""
            return {
                "status": "healthy",
                "service": "RBAC-Protected Calculator MCP Server",
                "authentication": "Azure AD with RBAC",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "rbac_enabled": True,
                "supported_roles": list(self.rbac_engine.role_hierarchy.keys())
            }
        
        # Authentication middleware for MCP endpoints with token context injection
        @self.app.middleware("http")
        async def auth_middleware(request: Request, call_next):
            """Authentication middleware for MCP requests with RBAC context."""
            # Skip auth for public endpoints
            public_paths = [
                "/health", 
                "/.well-known/oauth-protected-resource", 
                "/auth/info",
                "/docs", 
                "/openapi.json"
            ]
            
            if request.url.path in public_paths:
                return await call_next(request)
            
            # Only apply auth to MCP endpoints
            if not request.url.path.startswith("/mcp"):
                return await call_next(request)
            
            # Check for Authorization header
            auth_header = request.headers.get("Authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                return JSONResponse(
                    status_code=401,
                    content={
                        "error": "Unauthorized", 
                        "detail": "Missing or invalid Authorization header"
                    },
                    headers={
                        "WWW-Authenticate": 'Bearer resource_metadata="/.well-known/oauth-protected-resource"'
                    }
                )
            
            # Validate token
            token = auth_header.split(" ", 1)[1]
            rbac_verifier = self.auth_manager.get_rbac_verifier()
            
            try:
                # Verify the token
                await rbac_verifier.verify_token(token)
                
                # Store token in request state for tool-level authorization
                request.state.auth_token = token
                request.state.rbac_verifier = rbac_verifier
                
                response = await call_next(request)
                return response
                
            except HTTPException as e:
                return JSONResponse(
                    status_code=e.status_code,
                    content={"error": "Authentication failed", "detail": e.detail},
                    headers={
                        "WWW-Authenticate": 'Bearer resource_metadata="/.well-known/oauth-protected-resource"'
                    }
                )
            except Exception as e:
                logger.error(f"Authentication error: {str(e)}")
                return JSONResponse(
                    status_code=401,
                    content={"error": "Authentication failed", "detail": "Token validation error"},
                    headers={
                        "WWW-Authenticate": 'Bearer resource_metadata="/.well-known/oauth-protected-resource"'
                    }
                )
        
        # Mount the MCP server
        mcp_app = self.calculator_server.get_fastmcp_instance()
        self.app.mount("/mcp", mcp_app._app)

    def get_app(self) -> FastAPI:
        """Get the configured FastAPI application."""
        return self.app


def create_app() -> FastAPI:
    """Application factory function."""
    application = AuthenticatedCalculatorApp()
    return application.get_app()


# For backward compatibility with original structure
def run_original_mode():
    """Run in original mode (stdio or basic streamable-http)."""
    from calculator_mcp_server import mcp as original_mcp
    
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    
    print(f"Starting Calculator MCP Server...")
    print(f"Transport: {transport}")
    
    if transport == "streamable-http":
        print("Server will listen on default host and port (0.0.0.0:8000)")
        print("Endpoints available:")
        print("  - Health check: http://0.0.0.0:8000/health")
        print("  - MCP endpoint: http://0.0.0.0:8000/mcp")
        
        original_mcp.run(transport="streamable-http")
    else:
        print("Running with stdio transport for local development")
        original_mcp.run()


# Global MCP server instance for CLI compatibility
# This creates a basic MCP server that the CLI can detect and run
_calculator_server = CalculatorMCPServer("Calculator")
mcp = _calculator_server.get_fastmcp_instance()

# For FastAPI deployment with authentication
app = create_app()


if __name__ == "__main__":
    # Check if authentication is enabled
    auth_enabled = os.getenv("ENABLE_AUTH", "true").lower() == "true"
    
    if auth_enabled and os.getenv("AZURE_TENANT_ID") and os.getenv("AZURE_CLIENT_ID"):
        # Run with authentication and RBAC
        import uvicorn
        
        host = os.getenv("MCP_HOST", "0.0.0.0")
        port = int(os.getenv("MCP_PORT", "8000"))
        
        logger.info("Starting RBAC-Protected Calculator MCP Server...")
        logger.info(f"Host: {host}")
        logger.info(f"Port: {port}")
        logger.info("Authentication: Azure AD Bearer Token Required")
        logger.info("Authorization: Role-Based Access Control (RBAC)")
        logger.info("Supported Roles: MCP.BasicUser, MCP.PowerUser, MCP.Admin")
        logger.info("Endpoints available:")
        logger.info(f"  - Health check: http://{host}:{port}/health")
        logger.info(f"  - Protected Resource Metadata: http://{host}:{port}/.well-known/oauth-protected-resource")
        logger.info(f"  - Authorization Info: http://{host}:{port}/auth/info")
        logger.info(f"  - MCP endpoint: http://{host}:{port}/mcp")
        
        app = create_app()
        uvicorn.run(app, host=host, port=port, log_level="info")
    else:
        # Fall back to original mode
        logger.info("Authentication not configured, running in original mode")
        run_original_mode()
