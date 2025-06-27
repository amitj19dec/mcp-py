"""
Enhanced Calculator MCP Server with Decoupled Azure AD Authentication
Maintains the original calculator functionality while adding secure authentication.
"""

import os
import logging
from typing import Any, Dict
from datetime import datetime, timezone

# MCP SDK imports
from mcp.server.fastmcp import FastMCP

# FastAPI for hosting and middleware
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Authentication module (decoupled)
from auth_module import AuthenticationManager, create_auth_config_from_env

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
            Authenticated Calculator MCP Server Information
            =============================================
            
            Authentication: Azure AD Bearer Token Required
            
            Available Operations:
            - add(a, b): Add two numbers
            - subtract(a, b): Subtract b from a  
            - multiply(a, b): Multiply two numbers
            - divide(a, b): Divide a by b (b cannot be zero)
            - calculate_expression(expression): Evaluate a mathematical expression
            
            All operations return detailed results including the operation type,
            operands, result, and a formatted expression.
            
            Authentication Requirements:
            - Valid Azure AD bearer token in Authorization header
            - Token must have MCP.User or MCP.Admin role
            - Token audience must match the configured client ID
            
            Example usage:
            - add(5, 3) returns 8
            - subtract(10, 4) returns 6
            - multiply(7, 6) returns 42
            - divide(15, 3) returns 5
            - calculate_expression("2 + 3 * 4") returns 14
            """

    def _setup_prompts(self):
        """Setup calculator prompts."""
        
        @self.mcp.prompt("math_helper")
        async def math_helper_prompt() -> str:
            """A prompt template for helping with math problems."""
            return """
            I'm an authenticated calculator assistant that can help you with basic arithmetic operations.
            
            Authentication: This server requires a valid Azure AD bearer token.
            
            I can perform the following operations:
            1. Addition: add(a, b)
            2. Subtraction: subtract(a, b)
            3. Multiplication: multiply(a, b)  
            4. Division: divide(a, b)
            5. Expression evaluation: calculate_expression("expression")
            
            What mathematical operation would you like me to perform?
            Please provide the numbers or expression you'd like me to calculate.
            """
    
    def get_fastmcp_instance(self) -> FastMCP:
        """Get the FastMCP instance."""
        return self.mcp


class AuthenticatedCalculatorApp:
    """Main application that composes authentication and MCP server."""
    
    def __init__(self):
        # Load authentication configuration
        self.auth_config = create_auth_config_from_env()
        self.auth_manager = AuthenticationManager(self.auth_config)
        
        # Initialize calculator server
        self.calculator_server = CalculatorMCPServer("Authenticated Calculator")
        self._configure_mcp_auth()
        
        # Initialize FastAPI app
        self.app = FastAPI(
            title="Authenticated Calculator MCP Server",
            description="A secure calculator MCP server with Azure AD authentication"
        )
        self._setup_fastapi()

    def _configure_mcp_auth(self):
        """Configure the MCP server with authentication using official SDK."""
        mcp_instance = self.calculator_server.get_fastmcp_instance()
        
        # Configure authentication using the MCP SDK approach
        mcp_instance._token_verifier = self.auth_manager.get_mcp_token_verifier()
        mcp_instance._auth_settings = self.auth_manager.get_auth_settings()

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
        
        # RFC 9728 Protected Resource Metadata endpoint
        @self.app.get("/.well-known/oauth-protected-resource")
        async def protected_resource_metadata():
            """RFC 9728 Protected Resource Metadata endpoint."""
            return self.auth_manager.get_protected_resource_metadata()
        
        # Health check endpoint (no auth required)
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint for monitoring."""
            return {
                "status": "healthy",
                "service": "Authenticated Calculator MCP Server",
                "authentication": "Azure AD",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        
        # Authentication middleware for MCP endpoints
        @self.app.middleware("http")
        async def auth_middleware(request: Request, call_next):
            """Authentication middleware for MCP requests."""
            # Skip auth for public endpoints
            public_paths = [
                "/health", 
                "/.well-known/oauth-protected-resource", 
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
            
            # The MCP SDK TokenVerifier will handle token validation automatically
            return await call_next(request)
        
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


if __name__ == "__main__":
    # Check if authentication is enabled
    auth_enabled = os.getenv("ENABLE_AUTH", "true").lower() == "true"
    
    if auth_enabled and os.getenv("AZURE_TENANT_ID") and os.getenv("AZURE_CLIENT_ID"):
        # Run with authentication
        import uvicorn
        
        host = os.getenv("MCP_HOST", "0.0.0.0")
        port = int(os.getenv("MCP_PORT", "8000"))
        
        logger.info("Starting Authenticated Calculator MCP Server...")
        logger.info(f"Host: {host}")
        logger.info(f"Port: {port}")
        logger.info("Authentication: Azure AD Bearer Token Required")
        logger.info("Endpoints available:")
        logger.info(f"  - Health check: http://{host}:{port}/health")
        logger.info(f"  - Protected Resource Metadata: http://{host}:{port}/.well-known/oauth-protected-resource")
        logger.info(f"  - MCP endpoint: http://{host}:{port}/mcp")
        
        app = create_app()
        uvicorn.run(app, host=host, port=port, log_level="info")
    else:
        # Fall back to original mode
        logger.info("Authentication not configured, running in original mode")
        run_original_mode()
