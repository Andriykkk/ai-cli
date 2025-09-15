from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, AsyncGenerator
from .base_types import (
    ChatMessage, ChatResponse, ModelConfig, ToolDefinition, 
    ToolCall, ToolResult, ModelType
)

class BaseModelProvider(ABC):
    def __init__(self, config: ModelConfig):
        self.config = config
        self.model_type: Optional[ModelType] = None
        self.available_models: List[str] = []
        self.supports_tools: bool = False
        self.supports_streaming: bool = False
    
    @abstractmethod
    async def generate_response(
        self, 
        messages: List[ChatMessage],
        tools: Optional[List[ToolDefinition]] = None,
        **kwargs
    ) -> ChatResponse:
        """Generate a single response from the model"""
        pass
    
    @abstractmethod
    async def generate_stream(
        self, 
        messages: List[ChatMessage],
        tools: Optional[List[ToolDefinition]] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Generate streaming response from the model"""
        pass
    
    @abstractmethod
    def parse_tool_calls(self, response_data: Any) -> List[ToolCall]:
        """Parse tool calls from model response - provider specific"""
        pass
    
    @abstractmethod
    def format_tool_results(
        self, 
        tool_results: List[ToolResult]
    ) -> List[ChatMessage]:
        """Format tool execution results back to model format"""
        pass
    
    @abstractmethod
    def format_tools_for_model(
        self, 
        tools: List[ToolDefinition]
    ) -> Any:
        """Convert tool definitions to model-specific format"""
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """Validate provider configuration"""
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[str]:
        """Get list of available models"""
        pass
    
    @abstractmethod
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text"""
        pass
    
    def get_provider_info(self) -> Dict:
        """Get provider information"""
        return {
            "type": self.model_type.value if self.model_type else None,
            "models": self.available_models,
            "supports_tools": self.supports_tools,
            "supports_streaming": self.supports_streaming,
            "config": {
                "model_name": self.config.model_name,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens
            }
        }
    
    async def handle_conversation_with_tools(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[ToolDefinition]] = None,
        max_iterations: int = 10
    ) -> ChatResponse:
        """
        Handle complete conversation flow with tool calling loop.
        This is the main method that handles the tool calling cycle:
        1. Send messages to model
        2. If model wants to use tools, execute them
        3. Send tool results back to model
        4. Repeat until model gives final response
        """
        conversation = messages.copy()
        
        for iteration in range(max_iterations):
            # Generate response with current conversation
            response = await self.generate_response(
                conversation, 
                tools=tools
            )
            
            # If no tool calls needed, return final response
            if not response.requires_tool_execution or not response.tool_calls:
                return response
            
            # Add assistant's response with tool calls to conversation
            assistant_message = ChatMessage(
                role="assistant",
                content=response.content or "",
                tool_calls=[{
                    "id": tc.id,
                    "name": tc.name, 
                    "arguments": tc.arguments
                } for tc in response.tool_calls]
            )
            conversation.append(assistant_message)
            
            # This will be handled by ChatManager - execute tools and add results
            # For now, return response indicating tools need to be executed
            return response
        
        # If we hit max iterations, return what we have
        return response