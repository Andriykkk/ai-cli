"""
File Writing Tool
Create or overwrite files with content
"""

import os
from pathlib import Path
from typing import Dict, Any

from ..base_tool import BaseTool, ToolResult


class WriteFileTool(BaseTool):
    """
    Tool for creating or overwriting files with content
    
    Security features:
    - Path validation and traversal protection
    - File size limits
    - Directory creation control
    - System file protection
    """
    
    # Security settings
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB max file size
    
    # Blocked file patterns for security
    BLOCKED_PATTERNS = [
        "/etc/", "/usr/", "/var/", "/sys/", "/proc/", "/dev/",
        "passwd", "shadow", "sudoers", ".ssh/", ".git/config"
    ]
    
    @property
    def name(self) -> str:
        return "write_file"
    
    @property
    def description(self) -> str:
        return "Create or overwrite a file with the specified content. Creates parent directories if needed."
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to create/overwrite (relative to project root)"
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file"
                }
            },
            "required": ["file_path", "content"]
        }
    
    async def execute(self, project_path: str, **kwargs) -> ToolResult:
        """
        Write content to a file
        
        Args:
            project_path: Project directory
            file_path: Path to file to write
            content: Content to write
            
        Returns:
            ToolResult with write result
        """
        file_path = kwargs.get("file_path", "").strip()
        content = kwargs.get("content", "")
        
        if not file_path:
            return ToolResult(
                success=False,
                content="",
                error="File path cannot be empty"
            )
        
        # Validate content size
        if len(content.encode('utf-8')) > self.MAX_FILE_SIZE:
            return ToolResult(
                success=False,
                content="",
                error=f"Content too large (max {self.MAX_FILE_SIZE // 1024 // 1024}MB)"
            )
        
        # Validate and resolve file path
        try:
            full_path = self._resolve_file_path(project_path, file_path)
        except ValueError as e:
            return ToolResult(
                success=False,
                content="",
                error=str(e)
            )
        
        try:
            # Create parent directories if they don't exist
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Check if file exists (for metadata)
            file_existed = full_path.exists()
            old_size = full_path.stat().st_size if file_existed else 0
            
            # Write content to file
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Get new file stats
            new_size = full_path.stat().st_size
            # Count lines like text editors: final newline doesn't create extra line
            if not content:
                lines_written = 0
            elif content.endswith('\n'):
                lines_written = max(1, content.count('\n'))
            else:
                lines_written = content.count('\n') + 1
            
            action = "overwritten" if file_existed else "created"
            
            return ToolResult(
                success=True,
                content=content,  # Return the actual content for UI display
                metadata={
                    "file_path": str(file_path),
                    "action": action,
                    "bytes_written": new_size,
                    "lines_written": lines_written,
                    "old_size": old_size if file_existed else None,
                    "operation_summary": f"File {action} successfully: {file_path}"
                }
            )
            
        except PermissionError:
            return ToolResult(
                success=False,
                content="",
                error=f"Permission denied: Cannot write to {file_path}"
            )
        except OSError as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Error writing file: {str(e)}"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Unexpected error writing file: {str(e)}"
            )
    
    def _resolve_file_path(self, project_path: str, file_path: str) -> Path:
        """
        Resolve and validate file path
        
        Args:
            project_path: Project root directory
            file_path: Relative file path
            
        Returns:
            Path: Resolved absolute path
            
        Raises:
            ValueError: If path is invalid or dangerous
        """
        project_dir = Path(project_path)
        if not project_dir.exists() or not project_dir.is_dir():
            raise ValueError(f"Invalid project directory: {project_path}")
        
        # Handle absolute paths by making them relative to project
        if file_path.startswith('/'):
            file_path = file_path.lstrip('/')
        
        # Resolve the path
        full_path = (project_dir / file_path).resolve()
        
        # Security: Ensure path is within project directory
        try:
            full_path.relative_to(project_dir.resolve())
        except ValueError:
            raise ValueError(f"Path outside project directory: {file_path}")
        
        # Security: Check against blocked patterns
        path_str = str(full_path).lower()
        for pattern in self.BLOCKED_PATTERNS:
            if pattern in path_str:
                raise ValueError(f"Cannot write to system location: {file_path}")
        
        return full_path