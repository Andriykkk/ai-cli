"""
Google Gemini Provider
Implementation for Google's Gemini API with function calling support
"""

import json
import httpx
import re
import logging
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
        logger = logging.getLogger(__name__)
        logger.info(f"Formatting {len(messages)} messages for Gemini")
        
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
                logger.info(f"Formatting tool result: name={msg.tool_call_id}, content_length={len(msg.content) if msg.content else 0}")
                tool_response = {
                    "role": "user",  # Tool results are user messages in Gemini
                    "parts": [{
                        "functionResponse": {
                            "name": msg.tool_call_id,
                            "response": {"content": msg.content}
                        }
                    }]
                }
                gemini_messages.append(tool_response)
                
            else:
                # Regular text message
                gemini_messages.append({
                    "role": role,
                    "parts": [{"text": msg.content}]
                })
        
        logger.info(f"Formatted {len(gemini_messages)} messages for Gemini API")
        for i, msg in enumerate(gemini_messages):
            role = msg.get('role', 'unknown')
            parts_count = len(msg.get('parts', []))
            logger.info(f"Message {i}: role={role}, parts={parts_count}")
            for j, part in enumerate(msg.get('parts', [])):
                part_type = list(part.keys())[0] if part else "empty"
                logger.info(f"  Part {j}: type={part_type}")
        
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
            import logging
            logger = logging.getLogger(__name__)
            
            logger.info(f"Making Gemini API request to {url}")
            logger.info(f"Payload keys: {list(payload.keys())}")
            logger.info(f"Messages count: {len(payload.get('contents', []))}")
            logger.info(f"Tools provided: {bool(tools)}")
            if payload.get('contents'):
                last_msg = payload['contents'][-1] if payload['contents'] else None
                logger.info(f"Last message role: {last_msg.get('role') if last_msg else None}")
            
            response = await self.client.post(url, json=payload, headers=headers)
            
            if not response.is_success:
                logger.error(f"Gemini API HTTP {response.status_code}: {response.text}")
                try:
                    error_details = response.json()
                    logger.error(f"Gemini error details: {error_details}")
                except:
                    logger.error(f"Raw error response: {response.text}")
            
            response.raise_for_status()
            result = response.json()
            logger.info(f"Gemini response received with {len(result.get('candidates', []))} candidates")
            return result
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Gemini API error: {str(e)}")
            logger.error(f"Request payload structure: {json.dumps(payload, indent=2)}")
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
            logger.warning("No candidates in Gemini response, returning empty response")
            logger.warning(f"Raw response: {json.dumps(raw_response, indent=2)}")
            
            # Check if there's a finishReason in the response that explains why
            finish_reason = "stop"
            if "candidates" in raw_response and len(raw_response["candidates"]) == 0:
                # Look for any metadata about why there are no candidates
                if "promptFeedback" in raw_response:
                    feedback = raw_response["promptFeedback"]
                    logger.warning(f"Prompt feedback: {feedback}")
                    if "blockReason" in feedback:
                        finish_reason = f"blocked_{feedback['blockReason']}"
            
            return ChatResponse(
                content="",
                model=self.model,
                usage={},
                finish_reason=finish_reason,
                provider="gemini",
                tool_calls=None,
                requires_tool_execution=False
            )
        
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
                import random
                tool_calls.append(ToolCall(
                    id=f"gemini_call_{int(datetime.now().timestamp())}_{random.randint(1000, 9999)}",
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
