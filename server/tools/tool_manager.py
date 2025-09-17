"""
Tool Manager
Central registry and executor for all tools
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

from .base_tool import BaseTool, ToolResult


class ToolManager:
    """
    Central manager for all tools
    
    Responsibilities:
    - Register and discover tools
    - Execute tools with validation
    - Provide tool schemas for AI models
    - Handle tool permissions and security
    """
    
    def __init__(self):
        """Initialize the tool manager"""
        self.tools: Dict[str, BaseTool] = {}
        self.logger = logging.getLogger(__name__)
    
    def register_tool(self, tool: BaseTool) -> None:
        """
        Register a tool with the manager
        
        Args:
            tool: Tool instance to register
            
        Raises:
            ValueError: If tool name already exists or tool is invalid
        """
        if not isinstance(tool, BaseTool):
            raise ValueError(f"Tool must inherit from BaseTool, got {type(tool)}")
        
        tool_name = tool.name
        if tool_name in self.tools:
            raise ValueError(f"Tool '{tool_name}' is already registered")
        
        self.tools[tool_name] = tool
        self.logger.info(f"Registered tool: {tool_name}")
    
    def unregister_tool(self, tool_name: str) -> bool:
        """
        Unregister a tool
        
        Args:
            tool_name: Name of the tool to unregister
            
        Returns:
            bool: True if tool was unregistered, False if not found
        """
        if tool_name in self.tools:
            del self.tools[tool_name]
            self.logger.info(f"Unregistered tool: {tool_name}")
            return True
        return False
    
    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """
        Get a specific tool by name
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            BaseTool instance or None if not found
        """
        return self.tools.get(tool_name)
    
    def get_all_tools(self) -> List[BaseTool]:
        """
        Get all registered tools
        
        Returns:
            List of all registered tools
        """
        return list(self.tools.values())
    
    def get_tool_names(self) -> List[str]:
        """
        Get names of all registered tools
        
        Returns:
            List of tool names
        """
        return list(self.tools.keys())
    
    def has_tool(self, tool_name: str) -> bool:
        """
        Check if a tool is registered
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            bool: True if tool exists
        """
        return tool_name in self.tools
    
    async def execute_tool(
        self, 
        tool_name: str, 
        project_path: str,
        **kwargs
    ) -> ToolResult:
        """
        Execute a tool with given parameters
        
        Args:
            tool_name: Name of the tool to execute
            project_path: Path to the project directory
            **kwargs: Tool-specific parameters
            
        Returns:
            ToolResult: Result of tool execution
        """
        # Check if tool exists
        if tool_name not in self.tools:
            return ToolResult(
                success=False,
                content="",
                error=f"Tool '{tool_name}' not found. Available tools: {', '.join(self.tools.keys())}"
            )
        
        tool = self.tools[tool_name]
        
        # Validate parameters
        if not tool.validate_parameters(**kwargs):
            return ToolResult(
                success=False,
                content="",
                error=f"Invalid parameters for tool '{tool_name}'. Expected: {tool.parameters}"
            )
        
        # Validate project path
        if not self._validate_project_path(project_path):
            return ToolResult(
                success=False,
                content="",
                error=f"Invalid project path: {project_path}"
            )
        
        try:
            self.logger.info(f"Executing tool '{tool_name}' with params: {kwargs}")
            
            # Execute the tool
            result = await tool.execute(project_path=project_path, **kwargs)
            
            self.logger.info(f"Tool '{tool_name}' completed successfully: {result.success}")
            return result
            
        except Exception as e:
            error_msg = f"Tool '{tool_name}' execution failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            return ToolResult(
                success=False,
                content="",
                error=error_msg
            )
    
    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """
        Get schema definitions for all tools (for AI model tool calling)
        
        Returns:
            List of tool schemas compatible with AI model APIs
        """
        return [tool.get_schema() for tool in self.tools.values()]
    
    def get_available_tools(self) -> List['ToolDefinition']:
        """
        Get available tools as ToolDefinition objects
        
        Returns:
            List of ToolDefinition objects for all registered tools
        """
        from core.base_types import ToolDefinition
        
        tool_definitions = []
        for tool in self.tools.values():
            schema = tool.get_schema()
            tool_def = ToolDefinition(
                name=schema["name"],
                description=schema["description"], 
                parameters=schema["parameters"]
            )
            tool_definitions.append(tool_def)
        
        return tool_definitions
    
    def get_enabled_tools_schema(self, enabled_tools: List[str]) -> List[Dict[str, Any]]:
        """
        Get schema definitions for specific enabled tools
        
        Args:
            enabled_tools: List of tool names to include
            
        Returns:
            List of tool schemas for enabled tools only
        """
        schemas = []
        for tool_name in enabled_tools:
            if tool_name in self.tools:
                schemas.append(self.tools[tool_name].get_schema())
        return schemas
    
    def _validate_project_path(self, project_path: str) -> bool:
        """
        Validate that the project path is safe and exists
        
        Args:
            project_path: Path to validate
            
        Returns:
            bool: True if path is valid
        """
        try:
            path = Path(project_path)
            
            # Check if path exists
            if not path.exists():
                return False
            
            # Check if it's a directory
            if not path.is_dir():
                return False
            
            # Basic security: ensure it's an absolute path
            if not path.is_absolute():
                return False
            
            # TODO: Add more security checks as needed
            # - Check if path is within allowed directories
            # - Check for symlink attacks
            # - Check permissions
            
            return True
            
        except Exception:
            return False
    
    def get_tool_info(self) -> Dict[str, Dict[str, Any]]:
        """
        Get detailed information about all registered tools
        
        Returns:
            Dictionary with tool info for debugging/admin purposes
        """
        info = {}
        for name, tool in self.tools.items():
            info[name] = {
                "description": tool.description,
                "parameters": tool.parameters,
                "class": tool.__class__.__name__
            }
        return info
    
    def clear_tools(self) -> None:
        """Clear all registered tools (useful for testing)"""
        self.tools.clear()
        self.logger.info("Cleared all registered tools")


# Global tool manager instance
_tool_manager_instance = None


def get_tool_manager() -> ToolManager:
    """Get the global ToolManager instance"""
    global _tool_manager_instance
    if _tool_manager_instance is None:
        _tool_manager_instance = ToolManager()
    return _tool_manager_instance