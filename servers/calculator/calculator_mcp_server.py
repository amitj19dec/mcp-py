"""
Basic Calculator MCP Server (Azure Container Instance Ready)
A simple MCP server that provides basic arithmetic operations.
Supports both stdio and streamable-http transports.
"""

import asyncio
import os
from typing import Any, Dict
from mcp.server.fastmcp import FastMCP


# Initialize FastMCP server
mcp = FastMCP("Calculator")


@mcp.tool()
async def add(a: float, b: float) -> Dict[str, Any]:
    """
    Add two numbers together.
    
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
async def subtract(a: float, b: float) -> Dict[str, Any]:
    """
    Subtract the second number from the first number.
    
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
async def multiply(a: float, b: float) -> Dict[str, Any]:
    """
    Multiply two numbers together.
    
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
async def divide(a: float, b: float) -> Dict[str, Any]:
    """
    Divide the first number by the second number.
    
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
async def calculate_expression(expression: str) -> Dict[str, Any]:
    """
    Evaluate a basic mathematical expression.
    
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
async def get_calculator_info() -> str:
    """
    Get information about the calculator server capabilities.
    
    Returns:
        Information about available operations
    """
    info = """
    Calculator MCP Server Information
    ================================
    
    Available Operations:
    - add(a, b): Add two numbers
    - subtract(a, b): Subtract b from a
    - multiply(a, b): Multiply two numbers
    - divide(a, b): Divide a by b (b cannot be zero)
    - calculate_expression(expression): Evaluate a mathematical expression
    
    All operations return detailed results including the operation type,
    operands, result, and a formatted expression.
    
    Example usage:
    - add(5, 3) returns 8
    - subtract(10, 4) returns 6
    - multiply(7, 6) returns 42
    - divide(15, 3) returns 5
    - calculate_expression("2 + 3 * 4") returns 14
    """
    return info


@mcp.prompt("math_helper")
async def math_helper_prompt() -> str:
    """
    A prompt template for helping with math problems.
    
    Returns:
        A prompt that guides users on how to use the calculator
    """
    return """
    I'm a calculator assistant that can help you with basic arithmetic operations.
    
    I can perform the following operations:
    1. Addition: add(a, b)
    2. Subtraction: subtract(a, b)
    3. Multiplication: multiply(a, b)
    4. Division: divide(a, b)
    5. Expression evaluation: calculate_expression("expression")
    
    What mathematical operation would you like me to perform?
    Please provide the numbers or expression you'd like me to calculate.
    """


if __name__ == "__main__":
    # Get configuration from environment variables
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    
    print(f"Starting Calculator MCP Server...")
    print(f"Transport: {transport}")
    
    if transport == "streamable-http":
        print("Server will listen on default host and port (0.0.0.0:8000)")
        print("Endpoints available:")
        print("  - Health check: http://0.0.0.0:8000/health")
        print("  - MCP endpoint: http://0.0.0.0:8000/mcp")
        
        # The official MCP SDK FastMCP.run() only accepts transport parameter
        # Host and port are configured through other means or use defaults
        mcp.run(transport="streamable-http" )
    else:
        print("Running with stdio transport for local development")
        # Run with stdio transport for local development
        mcp.run()