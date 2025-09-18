"""
Echo Test Provider
A testing provider that echoes messages and can simulate tool calling based on commands
"""

import asyncio
import random
import re
from typing import List, Optional, Dict, Any
from core.base_provider import BaseModelProvider
from core.base_types import ChatMessage, ChatResponse, ToolDefinition, ToolCall


class EchoTestProvider(BaseModelProvider):
    """
    Test provider that echoes messages and simulates tool calling
    
    Commands:
    - "call X tools Y times" - calls X tools simultaneously, Y times
    - "echo [text]" - just echoes the text
    - Regular text - echoes with "Echo: " prefix
    """
    
    def __init__(self, api_key: str = "test-key", model: str = "echo-test", **config):
        """Initialize the echo test provider"""
        super().__init__(api_key, model, **config)
        self.available_tools = []
    
    @property
    def provider_name(self) -> str:
        """Provider name"""
        return "echo_test"
    
    def set_tools(self, tools: List[ToolDefinition]):
        """Set available tools for simulation"""
        self.available_tools = tools
    
    def format_messages(self, messages: List[ChatMessage]) -> List[Dict[str, Any]]:
        """Convert messages to our internal format (no conversion needed for test)"""
        return [{"role": msg.role, "content": msg.content} for msg in messages]
    
    def format_tools(self, tools: List[ToolDefinition]) -> Any:
        """Convert tools to our internal format (no conversion needed for test)"""
        return tools
    
    async def call_api(self, messages: List[Dict[str, Any]], tools: Optional[Any] = None, **kwargs) -> Dict[str, Any]:
        """Simulate API call"""
        # Get the last user message
        last_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_message = msg.get("content", "")
                break
        
        # Parse command for tool calling
        tool_calls = self._parse_tool_command_raw(last_message, tools or self.available_tools)
        
        # Generate response
        if tool_calls:
            response_content = f"Echo: {last_message}\n\n🔧 Calling {len(tool_calls)} tools as requested..."
        else:
            response_content = f"Echo: {last_message}"
        
        return {
            "content": response_content,
            "tool_calls": tool_calls,
            "usage": {
                "prompt_tokens": len(last_message.split()),
                "completion_tokens": len(response_content.split()),
                "total_tokens": len(last_message.split()) + len(response_content.split())
            },
            "finish_reason": "stop" if not tool_calls else "tool_calls"
        }
    
    async def call_api_stream(self, messages: List[Dict[str, Any]], tools: Optional[Any] = None, **kwargs) -> Dict[str, Any]:
        """Simulate streaming API call (same as regular call for test)"""
        return await self.call_api(messages, tools, **kwargs)
    
    def parse_response(self, raw_response: Dict[str, Any]) -> ChatResponse:
        """Parse response to standard format"""
        tool_calls = []
        if raw_response.get("tool_calls"):
            for tc in raw_response["tool_calls"]:
                tool_calls.append(ToolCall(
                    id=tc["id"],
                    name=tc["name"], 
                    arguments=tc["arguments"]
                ))
        
        return ChatResponse(
            content=raw_response.get("content", ""),
            model=self.model,
            usage=raw_response.get("usage", {}),
            finish_reason=raw_response.get("finish_reason", "stop"),
            provider="echo_test",
            tool_calls=tool_calls if tool_calls else None,
            requires_tool_execution=bool(tool_calls)
        )
    
    def parse_stream_chunk(self, chunk: Dict[str, Any]) -> Optional[ChatResponse]:
        """Parse streaming chunk (same as parse_response for test)"""
        return self.parse_response(chunk)
    
    def _parse_tool_command_raw(self, message: str, tools: List[ToolDefinition]) -> List[Dict[str, Any]]:
        """Parse message for tool calling commands and return raw format"""
        
        # Pattern: "call X tools Y times"
        pattern = r"call\s+(\d+)\s+tools?\s+(\d+)\s+times?"
        match = re.search(pattern, message.lower())
        
        if not match:
            return []
        
        num_tools = int(match.group(1))
        num_iterations = int(match.group(2))
        
        # Limit to reasonable numbers
        num_tools = min(num_tools, len(tools), 5)
        num_iterations = min(num_iterations, 3)
        
        if not tools:
            return []
        
        tool_calls = []
        
        for iteration in range(num_iterations):
            # Select random tools for this iteration
            selected_tools = random.sample(
                tools, 
                min(num_tools, len(tools))
            )
            
            for i, tool in enumerate(selected_tools):
                tool_call = self._create_test_tool_call_raw(tool, iteration, i)
                tool_calls.append(tool_call)
        
        return tool_calls
    
    def _create_test_tool_call_raw(self, tool: ToolDefinition, iteration: int, index: int) -> Dict[str, Any]:
        """Create a test tool call in raw format"""
        
        tool_id = f"test_call_{iteration}_{index}_{random.randint(1000, 9999)}"
        
        # Generate test arguments based on tool type
        if tool.name == "run_command":
            commands = [
                "ls -la",
                "pwd", 
                "echo 'Hello from test tool'",
                "date",
                "whoami",
                f"grep -r 'test' . | head -3",
                "find . -name '*.py' | head -5",
                "git status --porcelain",
                f"echo 'Tool call #{iteration + 1}.{index + 1}'"
            ]
            
            arguments = {
                "command": random.choice(commands),
                "timeout": random.choice([10, 15, 30])
            }
            
        else:
            # For other tools, create generic test arguments
            arguments = {}
            
            # Add required parameters with test values
            properties = tool.parameters.get("properties", {})
            required = tool.parameters.get("required", [])
            
            for param in required:
                if param in properties:
                    param_type = properties[param].get("type", "string")
                    if param_type == "string":
                        arguments[param] = f"test_value_for_{param}_{iteration}_{index}"
                    elif param_type == "number":
                        arguments[param] = random.randint(1, 100)
                    elif param_type == "boolean":
                        arguments[param] = random.choice([True, False])
        
        return {
            "id": tool_id,
            "name": tool.name,
            "arguments": arguments
        }
    
    async def generate(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[ToolDefinition]] = None,
        **kwargs
    ) -> ChatResponse:
        """Generate response with optional tool calling"""
        
        if tools:
            self.available_tools = tools
        
        # Get the last user message
        last_message = None
        for msg in reversed(messages):
            if msg.role == "user":
                last_message = msg.content
                break
        
        if not last_message:
            last_message = "No user message found"
        
        # Parse command for tool calling
        tool_calls = self._parse_tool_command(last_message)
        
        # Generate response
        if tool_calls:
            response_content = f"Echo: {last_message}\n\n🔧 Calling {len(tool_calls)} tools as requested..."
        else:
            response_content = f"Echo: {last_message}"
        
        return ChatResponse(
            content=response_content,
            model=self.model,
            usage={
                "prompt_tokens": len(last_message.split()),
                "completion_tokens": len(response_content.split()),
                "total_tokens": len(last_message.split()) + len(response_content.split())
            },
            finish_reason="stop" if not tool_calls else "tool_calls",
            provider="echo_test",
            tool_calls=tool_calls,
            requires_tool_execution=bool(tool_calls)
        )
    
    def _parse_tool_command(self, message: str) -> List[ToolCall]:
        """Parse message for tool calling commands"""
        
        # Pattern: "call X tools Y times"
        pattern = r"call\s+(\d+)\s+tools?\s+(\d+)\s+times?"
        match = re.search(pattern, message.lower())
        
        if not match:
            return []
        
        num_tools = int(match.group(1))
        num_iterations = int(match.group(2))
        
        # Limit to reasonable numbers
        num_tools = min(num_tools, len(self.available_tools), 5)
        num_iterations = min(num_iterations, 3)
        
        if not self.available_tools:
            return []
        
        tool_calls = []
        
        for iteration in range(num_iterations):
            # Select random tools for this iteration
            selected_tools = random.sample(
                self.available_tools, 
                min(num_tools, len(self.available_tools))
            )
            
            for i, tool in enumerate(selected_tools):
                tool_call = self._create_test_tool_call(tool, iteration, i)
                tool_calls.append(tool_call)
        
        return tool_calls
    
    def _create_test_tool_call(self, tool: ToolDefinition, iteration: int, index: int) -> ToolCall:
        """Create a test tool call with realistic parameters"""
        
        tool_id = f"test_call_{iteration}_{index}_{random.randint(1000, 9999)}"
        
        # Generate test arguments based on tool type
        if tool.name == "run_command":
            commands = [
                "ls -la",
                "pwd",
                "echo 'Hello from test tool'",
                "date",
                "whoami",
                f"grep -r 'test' . | head -3",
                "find . -name '*.py' | head -5",
                "git status --porcelain",
                f"echo 'Tool call #{iteration + 1}.{index + 1}'"
            ]
            
            arguments = {
                "command": random.choice(commands),
                "timeout": random.choice([10, 15, 30])
            }
            
        else:
            # For other tools, create generic test arguments
            arguments = {}
            
            # Add required parameters with test values
            properties = tool.parameters.get("properties", {})
            required = tool.parameters.get("required", [])
            
            for param in required:
                if param in properties:
                    param_type = properties[param].get("type", "string")
                    if param_type == "string":
                        arguments[param] = f"test_value_for_{param}_{iteration}_{index}"
                    elif param_type == "number":
                        arguments[param] = random.randint(1, 100)
                    elif param_type == "boolean":
                        arguments[param] = random.choice([True, False])
        
        return ToolCall(
            id=tool_id,
            name=tool.name,
            arguments=arguments
        )
    
    async def stream_generate(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[ToolDefinition]] = None,
        **kwargs
    ) -> ChatResponse:
        """For streaming, just return the same as generate"""
        return await self.generate(messages, tools, **kwargs)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information"""
        return {
            "provider": "echo_test",
            "model": self.model,
            "type": "test",
            "supports_tools": True,
            "supports_streaming": True,
            "max_tokens": 1000,
            "description": "Echo test provider for debugging tool calling"
        }
    
    def validate_config(self) -> bool:
        """Validate provider configuration"""
        return True  # Always valid for testing