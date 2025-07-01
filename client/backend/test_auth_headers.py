#!/usr/bin/env python3
"""
Test script to demonstrate correct FastMCP 2.0 authentication
Shows the exact header that gets sent to the MCP server.
"""

import asyncio
import os
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

async def test_header_injection():
    """Test that demonstrates the correct way to add Authorization headers in FastMCP 2.0"""
    
    # Example token (this would come from your token manager)
    test_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsIng1dCI6Ik1uQ19WWmNBVGZNNXBP..."
    
    print("🧪 Testing FastMCP 2.0 Authentication Header Injection")
    print("=" * 60)
    
    # Method 1: Using StreamableHttpTransport directly
    print("\n1. Using StreamableHttpTransport with headers:")
    transport = StreamableHttpTransport(
        url="http://localhost:8000/mcp",
        headers={"Authorization": f"Bearer {test_token}"}
    )
    client = Client(transport)
    print(f"   Transport headers: {transport.headers}")
    print(f"   Header that will be sent: Authorization: Bearer {test_token[:50]}...")
    
    # Method 2: Using MCP configuration format
    print("\n2. Using MCP configuration format:")
    config = {
        "mcpServers": {
            "calculator": {
                "transport": "http",
                "url": "http://localhost:8000/mcp",
                "headers": {"Authorization": f"Bearer {test_token}"}
            }
        }
    }
    print(f"   Config headers: {config['mcpServers']['calculator']['headers']}")
    
    print("\n✅ Headers are configured at transport creation time")
    print("✅ No need to modify session internals")
    print("✅ Follows FastMCP 2.0 best practices")
    
    # Uncomment to test actual connection (requires running MCP server)
    # try:
    #     async with client as session:
    #         tools = await session.list_tools()
    #         print(f"\n🔧 Available tools: {[tool.name for tool in tools]}")
    # except Exception as e:
    #     print(f"\n⚠️  Connection test skipped (server not running): {e}")

if __name__ == "__main__":
    asyncio.run(test_header_injection())
