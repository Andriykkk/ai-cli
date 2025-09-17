"""
Base Tool Interface
Abstract base class that all tools must implement
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
import json


@dataclass
class ToolResult:
    """Standard result format for all tool executions"""
    success: bool
    content: str
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "success": self.success,
            "content": self.content,
            "error": self.error,
            "metadata": self.metadata
        }
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2)


class BaseTool(ABC):
    """
    Abstract base class for all tools
    
    All tools must implement:
    - name: Unique identifier for the tool
    - description: Human-readable description
    - parameters: JSON Schema for tool parameters
    - execute(): The main tool functionality
    """
    
    def __init__(self):
        """Initialize the tool"""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name identifier for this tool"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what this tool does"""
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """
        JSON Schema definition for tool parameters
        
        Example:
        {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Shell command to execute"
                }
            },
            "required": ["command"]
        }
        """
        pass
    
    @abstractmethod
    async def execute(self, project_path: str, **kwargs) -> ToolResult:
        """
        Execute the tool with given parameters
        
        Args:
            project_path: Path to the current project directory
            **kwargs: Tool-specific parameters as defined in parameters schema
            
        Returns:
            ToolResult: Standard result object
        """
        pass
    
    def get_schema(self) -> Dict[str, Any]:
        """
        Get the complete tool schema for AI model tool calling
        
        Returns:
            Dict containing tool name, description, and parameters schema
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }
    
    def validate_parameters(self, **kwargs) -> bool:
        """
        Validate that provided parameters match the schema
        
        Args:
            **kwargs: Parameters to validate
            
        Returns:
            bool: True if parameters are valid
            
        Note: This is a basic implementation. For production use,
        consider using jsonschema library for proper validation.
        """
        required_params = self.parameters.get("required", [])
        properties = self.parameters.get("properties", {})
        
        # Check required parameters
        for param in required_params:
            if param not in kwargs:
                return False
        
        # Check parameter types (basic validation)
        for param, value in kwargs.items():
            if param in properties:
                param_type = properties[param].get("type")
                if param_type == "string" and not isinstance(value, str):
                    return False
                elif param_type == "number" and not isinstance(value, (int, float)):
                    return False
                elif param_type == "boolean" and not isinstance(value, bool):
                    return False
                elif param_type == "array" and not isinstance(value, list):
                    return False
                elif param_type == "object" and not isinstance(value, dict):
                    return False
        
        return True
    
    def __str__(self) -> str:
        """String representation of the tool"""
        return f"Tool({self.name}): {self.description}"
    
    def __repr__(self) -> str:
        """Detailed representation of the tool"""
        return f"<{self.__class__.__name__}(name='{self.name}')>"