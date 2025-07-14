#!/usr/bin/env python3
"""
Startup script for MCP Gateway - Streamable HTTP Protocol Only
SSE deprecated as of June 2025 - using /mcp endpoint
"""
import os
import sys
import logging
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

def setup_environment():
    """Setup default environment variables if not set"""
    defaults = {
        "GATEWAY_HOST": "0.0.0.0",
        "GATEWAY_PORT": "8001",  # Default to 8001 to avoid conflicts
        "DEBUG": "true",
        "LOG_LEVEL": "INFO",
        "GATEWAY_API_KEY": "gateway-dev-key-123",
        "UI_TOKEN": "ui-dev-token-456",
        "CORS_ORIGINS": "http://localhost:3000,http://localhost:3001",
        "HTTP_CONNECT_TIMEOUT": "30",
        "HTTP_REQUEST_TIMEOUT": "60",
        "HTTP_STREAM_TIMEOUT": "300",
        "MAX_RETRIES": "3",
        "HEALTH_CHECK_INTERVAL": "30",
        "MAX_ACTIVITY_EVENTS": "1000"
    }
    
    for key, value in defaults.items():
        if key not in os.environ:
            os.environ[key] = value
    
    # Print configuration
    print("🌊 MCP Gateway - Streamable HTTP Protocol Configuration:")
    print(f"  Protocol: Streamable HTTP (/mcp endpoint)")
    print(f"  Note: SSE deprecated as of June 2025")
    print(f"  Host: {os.getenv('GATEWAY_HOST')}")
    print(f"  Port: {os.getenv('GATEWAY_PORT')}")
    print(f"  Debug: {os.getenv('DEBUG')}")
    print(f"  Log Level: {os.getenv('LOG_LEVEL')}")
    servers = os.getenv('MCP_SERVERS', 'None configured - will use defaults')
    print(f"  Backend Servers: {servers}")
    if servers != 'None configured - will use defaults':
        print(f"  → Gateway connects to /mcp endpoint on each server")
    print(f"  HTTP Connect Timeout: {os.getenv('HTTP_CONNECT_TIMEOUT')}s")
    print(f"  HTTP Stream Timeout: {os.getenv('HTTP_STREAM_TIMEOUT')}s")
    print()

def validate_servers():
    """Validate that configured servers are HTTP/HTTPS and show /mcp endpoint info"""
    servers = os.getenv('MCP_SERVERS', '')
    if servers:
        print("📡 Server Connection Details:")
        for server_str in servers.split(','):
            parts = [p.strip() for p in server_str.strip().split(':')]
            if len(parts) >= 3:
                name = parts[0]
                endpoint = ':'.join(parts[1:-1])
                namespace = parts[-1]
                
                if endpoint.startswith(('http://', 'https://')):
                    mcp_endpoint = f"{endpoint}/mcp"
                    print(f"  ✅ {name}: {endpoint} → connects to {mcp_endpoint}")
                else:
                    print(f"  ❌ {name}: Invalid endpoint '{endpoint}' - must be HTTP/HTTPS")
                    print(f"     Example: 'demo:http://localhost:8000:demo'")
        print()

def main():
    """Main startup function"""
    print("🚀 Starting MCP Gateway - Streamable HTTP Protocol Only...")
    print("📝 Note: SSE transport deprecated as of June 2025")
    print()
    
    # Setup environment
    setup_environment()
    
    # Validate server configuration
    validate_servers()
    
    try:
        # Import and run the FastAPI app
        import uvicorn
        from config import config
        
        print(f"🌐 Starting gateway server at http://{config.host}:{config.port}")
        print(f"📡 Protocol: {config.protocol}, Transport: {config.transport}")
        print(f"🔍 API Documentation: http://{config.host}:{config.port}/docs")
        print(f"🔧 Protocol Info: http://{config.host}:{config.port}/api/protocol")
        print(f"🎯 Gateway /mcp endpoint: http://{config.host}:{config.port}/mcp")
        print()
        print("🔄 Gateway connects to backend servers at their /mcp endpoints")
        print("📊 External clients connect to gateway /mcp endpoint")
        print()
        
        uvicorn.run(
            "app:app",
            host=config.host,
            port=config.port,
            reload=config.debug,
            log_level=config.log_level.lower()
        )
        
    except ImportError as e:
        print(f"❌ Error importing dependencies: {e}")
        print("Please install requirements: pip install -r backend/requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error starting gateway: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
