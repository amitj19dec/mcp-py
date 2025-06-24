# Calculator MCP Server

A basic calculator MCP (Model Context Protocol) server that provides arithmetic operations following the latest MCP specification (June 2025).

## Features

- **Basic Operations**: Add, subtract, multiply, divide
- **Expression Evaluation**: Calculate mathematical expressions
- **MCP Compliant**: Implements latest MCP specification with Streamable HTTP transport
- **Containerized**: Ready for deployment in Docker containers
- **Cloud Ready**: Suitable for Azure Container Instances and other cloud platforms

## Tools Available

1. **add(a, b)** - Add two numbers
2. **subtract(a, b)** - Subtract b from a  
3. **multiply(a, b)** - Multiply two numbers
4. **divide(a, b)** - Divide a by b (handles division by zero)
5. **calculate_expression(expression)** - Evaluate mathematical expressions

## Resources

- **calculator://info** - Get server capabilities information

## Prompts

- **math_helper** - A helpful prompt for math assistance

## Quick Start

### Local Development (stdio transport)

```bash
python calculator_mcp_server.py
```

### Docker Development

```bash
# Build the image
docker build -t calculator-mcp .

# Run the container
docker run -p 8000:8000 calculator-mcp
```

### Using Docker Compose

```bash
# Start the service
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the service
docker-compose down
```

## Azure Container Instance Deployment

```bash
# Build and push to Azure Container Registry
az acr build --registry myregistry --image calculator-mcp:latest .

# Deploy to Azure Container Instance
az container create \
  --resource-group myResourceGroup \
  --name calculator-mcp \
  --image myregistry.azurecr.io/calculator-mcp:latest \
  --ports 8000 \
  --environment-variables MCP_TRANSPORT=streamable-http MCP_PORT=8000 \
  --cpu 1 --memory 1
```

## MCP Client Configuration

For VS Code or other MCP clients, configure the server as:

```json
{
  "servers": {
    "calculator": {
      "type": "streamable-http",
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

For cloud deployment:
```json
{
  "servers": {
    "calculator": {
      "type": "streamable-http", 
      "url": "https://your-aci-instance.azurecontainer.io/mcp"
    }
  }
}
```

## API Examples

When connected via MCP client, you can use:

```
add(5, 3)
# Returns: {"operation": "addition", "operands": [5, 3], "result": 8, "expression": "5 + 3 = 8"}

calculate_expression("2 + 3 * 4")  
# Returns: {"operation": "expression_evaluation", "expression": "2 + 3 * 4", "result": 14}
```

## File Structure

```
.
├── calculator_mcp_server.py    # Main MCP server implementation
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Container definition
├── docker-compose.yml          # Local deployment
└── README.md                   # This file
```

## Security Notes

- The `calculate_expression` function uses `eval()` for demonstration purposes only
- In production, use a proper expression parser like `sympy` or `ast.literal_eval`
- The server runs as non-root user in the container
- Health checks are included for container orchestration

## Environment Variables

- `MCP_TRANSPORT`: Transport type (`stdio` or `streamable-http`)
- `MCP_PORT`: Port number for HTTP transport (default: 8000)

## Health Check

The container includes a health check endpoint accessible at `/health` when running in HTTP mode.

## License

This is a demo implementation for educational purposes.
