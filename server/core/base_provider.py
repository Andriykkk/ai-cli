"""
Clean Base Provider Interface
Simplified and focused on core responsibilities
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, AsyncIterator
from .base_types import ChatMessage, ChatResponse, ToolDefinition


class BaseModelProvider(ABC):
    """
    Base class for all AI model providers
    
    SINGLE RESPONSIBILITY: Make API calls to AI providers and format data
    
    Does NOT handle:
    - Tool execution (that's ToolManager's job)
    - Tool calling loops (that's ChatManager's job)  
    - Conversation management (that's ChatManager's job)
    
    DOES handle:
    - Format our tools/messages for specific AI provider API
    - Make HTTP requests to AI provider
    - Parse responses back to our standard format
    """
    
    def __init__(self, api_key: str, model: str, **config):
        """
        Initialize provider with API credentials
        
        Args:
            api_key: API key for the provider
            model: Model name (e.g., "gemini-pro", "gpt-4", "claude-3")
            **config: Provider-specific config (temperature, max_tokens, etc.)
        """
        self.api_key = api_key
        self.model = model
        self.config = config
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider name (e.g., 'gemini', 'openai', 'anthropic')"""
        pass
    
    @abstractmethod
    def format_messages(self, messages: List[ChatMessage]) -> List[Dict[str, Any]]:
        """
        Convert our standard messages to provider's API format
        
        Our format: ChatMessage(role="user", content="hello", tool_calls=None)
        Provider formats vary:
        - OpenAI: [{"role": "user", "content": "hello"}]
        - Gemini: [{"role": "user", "parts": [{"text": "hello"}]}]
        - Claude: [{"role": "user", "content": "hello"}]
        
        Args:
            messages: List of our standard ChatMessage objects
            
        Returns:
            List formatted for this provider's API
        """
        pass
    
    @abstractmethod
    def format_tools(self, tools: List[ToolDefinition]) -> Any:
        """
        Convert our standard tools to provider's API format
        
        Our format: ToolDefinition(name="run_command", description="...", parameters={...})
        Provider formats vary:
        - OpenAI: [{"type": "function", "function": {...}}]
        - Gemini: [{"function_declarations": [{...}]}] 
        - Claude: [{"name": "...", "description": "...", "input_schema": {...}}]
        
        Args:
            tools: List of our standard ToolDefinition objects
            
        Returns:
            Tools formatted for this provider's API
        """
        pass
    
    @abstractmethod
    async def call_api(
        self, 
        messages: List[Dict[str, Any]], 
        tools: Optional[Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Make API call to the provider
        
        Args:
            messages: Messages in provider's format (from format_messages)
            tools: Tools in provider's format (from format_tools)
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
            
        Returns:
            Raw API response as dict
        """
        pass
    
    @abstractmethod
    async def call_api_stream(
        self, 
        messages: List[Dict[str, Any]], 
        tools: Optional[Any] = None,
        **kwargs
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Make streaming API call to the provider
        
        Args:
            messages: Messages in provider's format
            tools: Tools in provider's format  
            **kwargs: Additional parameters
            
        Yields:
            Raw API response chunks as dicts
        """
        pass
    
    @abstractmethod
    def parse_response(self, raw_response: Dict[str, Any]) -> ChatResponse:
        """
        Parse provider's API response to our standard format
        
        Args:
            raw_response: Raw response from call_api()
            
        Returns:
            ChatResponse in our standard format
        """
        pass
    
    @abstractmethod
    def parse_stream_chunk(self, chunk: Dict[str, Any]) -> Optional[ChatResponse]:
        """
        Parse a streaming chunk to our standard format
        
        Args:
            chunk: One chunk from call_api_stream()
            
        Returns:
            ChatResponse chunk or None if chunk should be skipped
        """
        pass
    
    # Convenience methods that combine the above
    async def generate(
        self, 
        messages: List[ChatMessage], 
        tools: Optional[List[ToolDefinition]] = None,
        **kwargs
    ) -> ChatResponse:
        """
        High-level method: generate single response
        
        Combines: format_messages + format_tools + call_api + parse_response
        """
        formatted_messages = self.format_messages(messages)
        formatted_tools = self.format_tools(tools) if tools else None
        raw_response = await self.call_api(formatted_messages, formatted_tools, **kwargs)
        return self.parse_response(raw_response)
    
    async def generate_stream(
        self, 
        messages: List[ChatMessage], 
        tools: Optional[List[ToolDefinition]] = None,
        **kwargs
    ) -> AsyncIterator[ChatResponse]:
        """
        High-level method: generate streaming response
        
        Combines: format_messages + format_tools + call_api_stream + parse_stream_chunk
        """
        formatted_messages = self.format_messages(messages)
        formatted_tools = self.format_tools(tools) if tools else None
        
        async for chunk in self.call_api_stream(formatted_messages, formatted_tools, **kwargs):
            parsed_chunk = self.parse_stream_chunk(chunk)
            if parsed_chunk:
                yield parsed_chunk
    
    def supports_tools(self) -> bool:
        """Whether this provider supports tool calling"""
        return True  # Override if provider doesn't support tools
    
    def supports_streaming(self) -> bool:
        """Whether this provider supports streaming"""
        return True  # Override if provider doesn't support streaming
    
    def validate_config(self) -> bool:
        """Validate provider configuration"""
        return bool(self.api_key and self.model)
    
    def __str__(self) -> str:
        return f"{self.provider_name}({self.model})"