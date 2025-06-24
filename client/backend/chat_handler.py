#!/usr/bin/env python3
"""
Chat handler for MCP Client Backend
Integrates Azure OpenAI with MCP tools for dynamic tool calling.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from openai import AsyncAzureOpenAI
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class ChatMessage(BaseModel):
    message: str
    user_id: Optional[str] = "demo-user"

class ChatResponse(BaseModel):
    response: str
    tool_calls_made: List[Dict[str, Any]] = []
    reasoning: Optional[str] = None

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
            openai_tool = {
                "type": "function",
                "function": {
                    "name": f"{tool['server']}__{tool['name']}",  # Prefix with server name
                    "description": tool['description'],
                    "parameters": tool['input_schema']
                }
            }
            openai_tools.append(openai_tool)
        
        logger.info(f"🔧 Converted {len(mcp_tools)} MCP tools to OpenAI format")
        return openai_tools
    
    def create_system_prompt(self, available_tools: List[Dict[str, Any]]) -> str:
        """Create system prompt that describes available MCP tools."""
        if not available_tools:
            return "You are a helpful assistant. You don't have access to any special tools."
        
        tools_description = "You are a helpful assistant with access to the following tools:\\n\\n"
        
        for tool in available_tools:
            tools_description += f"**{tool['server']}.{tool['name']}**: {tool['description']}\\n"
            
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
When a user asks something that requires using these tools:
1. Use the appropriate tool(s) to get the information
2. Always provide a clear, helpful response based on the tool results
3. If multiple calculations are needed, break them down step by step
4. Be conversational and friendly in your responses

Remember: The tool names in function calls should be prefixed with the server name (e.g., "calculator__add").
"""
        
        return tools_description
    
    async def chat_with_tools(
        self, 
        message: str, 
        available_tools: List[Dict[str, Any]], 
        mcp_clients: Dict[str, Any]
    ) -> ChatResponse:
        """Handle chat message with dynamic MCP tool calling."""
        try:
            # Prepare OpenAI tools format
            openai_tools = self.convert_mcp_tools_to_openai_format(available_tools)
            system_prompt = self.create_system_prompt(available_tools)
            
            # Prepare messages
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ]
            
            logger.info(f"💭 Processing chat message: {message[:50]}...")
            
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
            
            # Execute tool calls if any
            if assistant_message.tool_calls:
                logger.info(f"🔧 Executing {len(assistant_message.tool_calls)} tool calls")
                
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
                
                # Execute each tool call
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
                        
                        # Execute tool via MCP client
                        if server_name in mcp_clients:
                            client = mcp_clients[server_name]
                            async with client as session:
                                result = await session.call_tool(tool_name, arguments)
                                
                                tool_calls_made.append({
                                    "server": server_name,
                                    "tool": tool_name,
                                    "arguments": arguments,
                                    "result": str(result)
                                })
                                
                                # Add tool result to conversation
                                messages.append({
                                    "role": "tool",
                                    "tool_call_id": tool_call.id,
                                    "content": str(result)
                                })
                                
                                logger.info(f"✅ Tool executed: {server_name}.{tool_name}")
                        else:
                            logger.error(f"❌ Server not found: {server_name}")
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": f"Error: Server {server_name} not available"
                            })
                    
                    except Exception as e:
                        logger.error(f"❌ Tool execution failed: {e}")
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": f"Error executing tool: {str(e)}"
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
            
            logger.info(f"💬 Chat response generated successfully")
            
            return ChatResponse(
                response=final_content,
                tool_calls_made=tool_calls_made,
                reasoning=f"Used {len(tool_calls_made)} tool(s)" if tool_calls_made else "No tools needed"
            )
            
        except Exception as e:
            logger.error(f"❌ Chat processing failed: {e}")
            return ChatResponse(
                response=f"I apologize, but I encountered an error: {str(e)}",
                tool_calls_made=[],
                reasoning="Error occurred"
            )
