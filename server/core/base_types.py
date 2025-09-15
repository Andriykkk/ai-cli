from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, AsyncGenerator
from dataclasses import dataclass
from enum import Enum
import json

class ModelType(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    DEEPSEEK = "deepseek"
    HUGGINGFACE = "huggingface"
    OLLAMA = "ollama"
    CUSTOM_GPU = "custom_gpu"

@dataclass
class ChatMessage:
    role: str  # "user", "assistant", "system", "tool"
    content: str
    tool_calls: Optional[List[Dict]] = None
    tool_call_id: Optional[str] = None
    timestamp: Optional[str] = None

@dataclass
class ToolCall:
    id: str
    name: str
    arguments: Dict[str, Any]

@dataclass
class ToolResult:
    tool_call_id: str
    name: str
    content: str
    success: bool
    error: Optional[str] = None

@dataclass
class ChatResponse:
    content: str
    model: str
    usage: Dict
    finish_reason: str
    provider: str
    tool_calls: Optional[List[ToolCall]] = None
    requires_tool_execution: bool = False

@dataclass
class ModelConfig:
    model_name: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4000
    timeout: int = 30
    extra_params: Optional[Dict] = None

@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: Dict[str, Any]
    
    def to_openai_format(self) -> Dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }
    
    def to_anthropic_format(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.parameters
        }
    
    def to_gemini_format(self) -> Dict:
        return {
            "function_declarations": [{
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }]
        }