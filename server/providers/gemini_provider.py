"""
Google Gemini Provider
Implementation for Google's Gemini API with function calling support
"""

import json
import httpx
from typing import Dict, List, Optional, Any, AsyncIterator
from datetime import datetime

from core.base_provider import BaseModelProvider
from core.base_types import ChatMessage, ChatResponse, ToolDefinition, ToolCall


class GeminiProvider(BaseModelProvider):
    """
    Google Gemini API provider with function calling support
    
    Formats tools/messages for Gemini API and handles responses
    """
    
    def __init__(self, api_key: str, model: str = "gemini-pro", **config):
        super().__init__(api_key, model, **config)
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        
        # HTTP client
        timeout = config.get("timeout", 30)
        self.client = httpx.AsyncClient(timeout=timeout)
    
    @property
    def provider_name(self) -> str:
        return "gemini"
    
    def format_messages(self, messages: List[ChatMessage]) -> List[Dict[str, Any]]:
        """
        Convert our messages to Gemini format
        
        Gemini format:
        {
            "role": "user" | "model",
            "parts": [
                {"text": "content"} or
                {"functionCall": {"name": "...", "args": {...}}} or
                {"functionResponse": {"name": "...", "response": {...}}}
            ]
        }
        """
        gemini_messages = []
        
        for msg in messages:
            # Skip system messages - Gemini handles them differently
            if msg.role == "system":
                continue
            
            # Convert role names
            role = "user" if msg.role == "user" else "model"
            
            if msg.tool_calls:
                # Assistant message with function calls
                parts = []
                if msg.content:
                    parts.append({"text": msg.content})
                
                for tool_call in msg.tool_calls:
                    parts.append({
                        "functionCall": {
                            "name": tool_call["name"],
                            "args": tool_call.get("arguments", {})
                        }
                    })
                
                gemini_messages.append({"role": role, "parts": parts})
                
            elif msg.role == "tool":
                # Tool result message
                gemini_messages.append({
                    "role": "user",  # Tool results are user messages in Gemini
                    "parts": [{
                        "functionResponse": {
                            "name": msg.tool_call_id,
                            "response": {"content": msg.content}
                        }
                    }]
                })
                
            else:
                # Regular text message
                gemini_messages.append({
                    "role": role,
                    "parts": [{"text": msg.content}]
                })
        
        return gemini_messages
    
    def format_tools(self, tools: List[ToolDefinition]) -> List[Dict[str, Any]]:
        """
        Convert our tools to Gemini format
        
        Gemini format:
        {
            "function_declarations": [
                {
                    "name": "function_name",
                    "description": "Clear explanation",
                    "parameters": {
                        "type": "object",
                        "properties": {...},
                        "required": [...]
                    }
                }
            ]
        }
        """
        if not tools:
            return []
        
        function_declarations = []
        for tool in tools:
            function_declarations.append({
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters
            })
        
        return [{"function_declarations": function_declarations}]
    
    async def call_api(
        self, 
        messages: List[Dict[str, Any]], 
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Make API call to Gemini"""
        
        # Build request payload
        payload = {
            "contents": messages,
            "generationConfig": {
                "temperature": kwargs.get("temperature", self.config.get("temperature", 0.7)),
                "maxOutputTokens": kwargs.get("max_tokens", self.config.get("max_tokens", 4000)),
                "candidateCount": 1
            }
        }
        
        if tools:
            payload["tools"] = tools
        
        # Make request
        url = f"{self.base_url}/models/{self.model}:generateContent"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key
        }
        
        try:
            response = await self.client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Gemini API error: {str(e)}")
    
    async def call_api_stream(
        self, 
        messages: List[Dict[str, Any]], 
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> AsyncIterator[Dict[str, Any]]:
        """Make streaming API call to Gemini"""
        
        # Build request payload (same as non-streaming)
        payload = {
            "contents": messages,
            "generationConfig": {
                "temperature": kwargs.get("temperature", self.config.get("temperature", 0.7)),
                "maxOutputTokens": kwargs.get("max_tokens", self.config.get("max_tokens", 4000)),
                "candidateCount": 1
            }
        }
        
        if tools:
            payload["tools"] = tools
        
        # Make streaming request
        url = f"{self.base_url}/models/{self.model}:streamGenerateContent"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key
        }
        
        try:
            async with self.client.stream("POST", url, json=payload, headers=headers) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line.strip():
                        try:
                            yield json.loads(line)
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            raise Exception(f"Gemini streaming error: {str(e)}")
    
    def parse_response(self, raw_response: Dict[str, Any]) -> ChatResponse:
        """Parse Gemini response to our standard format"""
        
        candidates = raw_response.get("candidates", [])
        if not candidates:
            raise Exception("No candidates in Gemini response")
        
        candidate = candidates[0]
        parts = candidate.get("content", {}).get("parts", [])
        
        # Extract content and tool calls
        content = ""
        tool_calls = []
        
        for part in parts:
            if "text" in part:
                content += part["text"]
            elif "functionCall" in part:
                func_call = part["functionCall"]
                tool_calls.append(ToolCall(
                    id=f"call_{int(datetime.now().timestamp() * 1000)}",
                    name=func_call["name"],
                    arguments=func_call.get("args", {})
                ))
        
        # Determine finish reason
        finish_reason = candidate.get("finishReason", "STOP").lower()
        if finish_reason == "stop":
            finish_reason = "stop"
        elif len(tool_calls) > 0:
            finish_reason = "tool_calls"
        
        # Extract usage
        usage = {}
        if "usageMetadata" in raw_response:
            metadata = raw_response["usageMetadata"]
            usage = {
                "prompt_tokens": metadata.get("promptTokenCount", 0),
                "completion_tokens": metadata.get("candidatesTokenCount", 0),
                "total_tokens": metadata.get("totalTokenCount", 0)
            }
        
        return ChatResponse(
            content=content,
            model=self.model,
            usage=usage,
            finish_reason=finish_reason,
            provider="gemini",
            tool_calls=tool_calls if tool_calls else None,
            requires_tool_execution=len(tool_calls) > 0
        )
    
    def parse_stream_chunk(self, chunk: Dict[str, Any]) -> Optional[ChatResponse]:
        """Parse a streaming chunk to our standard format"""
        try:
            # For Gemini streaming, each chunk has the same structure as regular response
            return self.parse_response(chunk)
        except Exception:
            # Skip invalid chunks
            return None

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
