#!/usr/bin/env python3
"""
Enhanced Chat handler for MCP Client Backend with Authentication Support
Integrates Azure OpenAI with authenticated MCP tools for dynamic tool calling with RBAC awareness.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from openai import AsyncAzureOpenAI
from pydantic import BaseModel

# Enhanced MCP client
from enhanced_mcp_client import EnhancedMCPClient

logger = logging.getLogger(__name__)

class ChatMessage(BaseModel):
    message: str
    user_id: Optional[str] = "demo-user"

class ChatResponse(BaseModel):
    response: str
    tool_calls_made: List[Dict[str, Any]] = []
    reasoning: Optional[str] = None
    permission_errors: List[str] = []

class ChatHandler:
    def __init__(self, azure_endpoint: str, api_key: str, api_version: str, deployment_name: str):
        """Initialize Azure OpenAI client."""
        self.client = AsyncAzureOpenAI(
            azure_endpoint=azure_endpoint,
            api_key=api_key,
            api_version=api_version
        )
        self.deployment_name = deployment_name
        logger.info(f"🤖 Azure OpenAI chat handler initialized with deployment: {deployment_name}")
    
    def convert_mcp_tools_to_openai_format(self, mcp_tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert MCP tool definitions to OpenAI function calling format."""
        openai_tools = []
        
        for tool in mcp_tools:
            if not tool.get("accessible", True):
                continue  # Skip inaccessible tools
                
            openai_tool = {
                "type": "function",
                "function": {
                    "name": f"{tool['server']}__{tool['name']}",  # Prefix with server name
                    "description": tool['description'],
                    "parameters": tool['input_schema']
                }
            }
            openai_tools.append(openai_tool)
        
        logger.info(f"🔧 Converted {len(openai_tools)} accessible MCP tools to OpenAI format")
        return openai_tools
    
    def create_system_prompt(self, available_tools: List[Dict[str, Any]]) -> str:
        """Create system prompt that describes available MCP tools with auth context."""
        if not available_tools:
            return "You are a helpful assistant. You don't have access to any special tools."
        
        tools_description = "You are a helpful assistant with access to the following authenticated tools:\\n\\n"
        
        # Group tools by server for better organization
        tools_by_server = {}
        for tool in available_tools:
            if not tool.get("accessible", True):
                continue
                
            server = tool.get('server', 'unknown')
            if server not in tools_by_server:
                tools_by_server[server] = []
            tools_by_server[server].append(tool)
        
        for server_name, server_tools in tools_by_server.items():
            tools_description += f"**{server_name} Server:**\\n"
            
            for tool in server_tools:
                tools_description += f"- **{tool['name']}**: {tool['description']}\\n"
                
                # Add parameter info
                if tool.get('input_schema', {}).get('properties'):
                    params = tool['input_schema']['properties']
                    param_list = []
                    for param_name, param_info in params.items():
                        param_type = param_info.get('type', 'unknown')
                        param_desc = param_info.get('title', param_name)
                        param_list.append(f"{param_name} ({param_type}): {param_desc}")
                    
                    tools_description += f"  Parameters: {', '.join(param_list)}\\n"
            
            tools_description += "\\n"
        
        tools_description += """
**Important Authentication Notes:**
- All tools require proper authentication and authorization
- You only have access to tools listed above based on your current permissions
- If a tool call fails due to permissions, explain this to the user clearly
- Some operations may be restricted based on user roles

When a user asks something that requires using these tools:
1. Use the appropriate tool(s) to get the information
2. Always provide a clear, helpful response based on the tool results
3. If multiple calculations are needed, break them down step by step
4. Be conversational and friendly in your responses
5. If permission is denied, explain what happened and suggest alternatives if available

Remember: The tool names in function calls should be prefixed with the server name (e.g., "calculator__add").
"""
        
        return tools_description
    
    async def chat_with_tools_auth(
        self, 
        message: str, 
        available_tools: List[Dict[str, Any]], 
        enhanced_clients: Dict[str, EnhancedMCPClient]
    ) -> ChatResponse:
        """Handle chat message with authenticated MCP tool calling and RBAC awareness."""
        try:
            # Filter tools to only accessible ones
            accessible_tools = [tool for tool in available_tools if tool.get("accessible", True)]
            
            # Prepare OpenAI tools format
            openai_tools = self.convert_mcp_tools_to_openai_format(accessible_tools)
            system_prompt = self.create_system_prompt(accessible_tools)
            
            # Prepare messages
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ]
            
            logger.info(f"💭 Processing chat message with {len(accessible_tools)} accessible tools: {message[:50]}...")
            
            # First LLM call - get tool calls
            response = await self.client.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
                tools=openai_tools if openai_tools else None,
                tool_choice="auto" if openai_tools else None,
                temperature=0.1
            )
            
            assistant_message = response.choices[0].message
            tool_calls_made = []
            permission_errors = []
            
            # Execute tool calls if any
            if assistant_message.tool_calls:
                logger.info(f"🔧 Executing {len(assistant_message.tool_calls)} tool calls with authentication")
                
                # Add assistant message to conversation
                messages.append({
                    "role": "assistant", 
                    "content": assistant_message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in assistant_message.tool_calls
                    ]
                })
                
                # Execute each tool call with authentication
                for tool_call in assistant_message.tool_calls:
                    try:
                        # Parse server and tool name
                        full_tool_name = tool_call.function.name
                        if "__" in full_tool_name:
                            server_name, tool_name = full_tool_name.split("__", 1)
                        else:
                            logger.warning(f"Invalid tool name format: {full_tool_name}")
                            continue
                        
                        # Parse arguments
                        arguments = json.loads(tool_call.function.arguments)
                        
                        # Execute tool via enhanced MCP client with auth
                        if server_name in enhanced_clients:
                            client = enhanced_clients[server_name]
                            
                            # Check permission first
                            has_permission = await client.check_tool_permission(tool_name)
                            if not has_permission:
                                error_msg = f"Permission denied for {server_name}.{tool_name}"
                                permission_errors.append(error_msg)
                                
                                messages.append({
                                    "role": "tool",
                                    "tool_call_id": tool_call.id,
                                    "content": f"Error: {error_msg}. You don't have permission to use this tool."
                                })
                                continue
                            
                            # Execute the tool with authentication
                            result = await client.call_tool_with_auth(tool_name, arguments)
                            
                            tool_calls_made.append({
                                "server": server_name,
                                "tool": tool_name,
                                "arguments": arguments,
                                "result": str(result),
                                "authenticated": True
                            })
                            
                            # Add tool result to conversation
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": str(result)
                            })
                            
                            logger.info(f"✅ Authenticated tool executed: {server_name}.{tool_name}")
                            
                        else:
                            error_msg = f"Server {server_name} not available"
                            logger.error(f"❌ {error_msg}")
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": f"Error: {error_msg}"
                            })
                    
                    except PermissionError as e:
                        error_msg = f"Permission denied: {str(e)}"
                        permission_errors.append(error_msg)
                        logger.warning(f"🚫 {error_msg}")
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": f"Permission denied: {str(e)}"
                        })
                    
                    except Exception as e:
                        error_msg = f"Tool execution failed: {str(e)}"
                        logger.error(f"❌ {error_msg}")
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": f"Error: {error_msg}"
                        })
                
                # Get final response with tool results
                final_response = await self.client.chat.completions.create(
                    model=self.deployment_name,
                    messages=messages,
                    temperature=0.1
                )
                
                final_content = final_response.choices[0].message.content
                
            else:
                # No tool calls needed
                final_content = assistant_message.content
            
            # Create reasoning text
            reasoning_parts = []
            if tool_calls_made:
                reasoning_parts.append(f"Used {len(tool_calls_made)} authenticated tool(s)")
            if permission_errors:
                reasoning_parts.append(f"{len(permission_errors)} permission error(s)")
            if not tool_calls_made and not permission_errors:
                reasoning_parts.append("No tools needed")
            
            reasoning = "; ".join(reasoning_parts)
            
            logger.info(f"💬 Chat response generated successfully with authentication")
            
            return ChatResponse(
                response=final_content,
                tool_calls_made=tool_calls_made,
                reasoning=reasoning,
                permission_errors=permission_errors
            )
            
        except Exception as e:
            logger.error(f"❌ Chat processing failed: {e}")
            return ChatResponse(
                response=f"I apologize, but I encountered an error: {str(e)}",
                tool_calls_made=[],
                reasoning="Error occurred",
                permission_errors=[]
            )

    # Keep backward compatibility with original method
    async def chat_with_tools(
        self, 
        message: str, 
        available_tools: List[Dict[str, Any]], 
        mcp_clients: Dict[str, Any]
    ) -> ChatResponse:
        """
        Backward compatibility method that delegates to the enhanced version.
        This assumes mcp_clients are actually enhanced clients.
        """
        # If mcp_clients are not enhanced clients, this will need adaptation
        return await self.chat_with_tools_auth(message, available_tools, mcp_clients)
