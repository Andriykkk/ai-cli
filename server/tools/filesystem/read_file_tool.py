"""
File Reading Tool
Read file contents with line range support
"""

from pathlib import Path
from typing import Dict, Any, Optional

from ..base_tool import BaseTool, ToolResult


class ReadFileTool(BaseTool):
    """
    Tool for reading file contents with optional line range
    
    Features:
    - Read entire file or specific line ranges
    - Line number display for LLM context
    - Binary file detection
    - File size limits for safety
    """
    
    # Security settings
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB max file size
    MAX_LINES_READ = 10000  # Maximum lines to read in one operation
    
    @property
    def name(self) -> str:
        return "read_file"
    
    @property
    def description(self) -> str:
        return "Read file contents with optional line range. Shows line numbers for context."
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to read (relative to project root)"
                },
                "start_line": {
                    "type": "number",
                    "description": "Starting line number (1-based, optional)",
                    "minimum": 1
                },
                "end_line": {
                    "type": "number", 
                    "description": "Ending line number (1-based, optional)",
                    "minimum": 1
                },
                "show_line_numbers": {
                    "type": "boolean",
                    "description": "Whether to show line numbers in output (default: true)",
                    "default": True
                }
            },
            "required": ["file_path"]
        }
    
    async def execute(self, project_path: str, **kwargs) -> ToolResult:
        """
        Read file contents
        
        Args:
            project_path: Project directory
            file_path: Path to file to read
            start_line: Starting line (1-based, optional)
            end_line: Ending line (1-based, optional)  
            show_line_numbers: Show line numbers in output
            
        Returns:
            ToolResult with file contents
        """
        file_path = kwargs.get("file_path", "").strip()
        start_line = kwargs.get("start_line")
        end_line = kwargs.get("end_line")
        show_line_numbers = kwargs.get("show_line_numbers", True)
        
        if not file_path:
            return ToolResult(
                success=False,
                content="",
                error="File path cannot be empty"
            )
        
        # Validate line parameters
        if start_line is not None and start_line < 1:
            return ToolResult(
                success=False,
                content="",
                error="start_line must be 1 or greater"
            )
        
        if end_line is not None and end_line < 1:
            return ToolResult(
                success=False,
                content="",
                error="end_line must be 1 or greater"
            )
        
        if start_line is not None and end_line is not None and start_line > end_line:
            return ToolResult(
                success=False,
                content="",
                error="start_line cannot be greater than end_line"
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
        
        # Check if file exists
        if not full_path.exists():
            return ToolResult(
                success=False,
                content="",
                error=f"File does not exist: {file_path}"
            )
        
        if not full_path.is_file():
            return ToolResult(
                success=False,
                content="",
                error=f"Path is not a file: {file_path}"
            )
        
        # Check file size
        file_size = full_path.stat().st_size
        if file_size > self.MAX_FILE_SIZE:
            return ToolResult(
                success=False,
                content="",
                error=f"File too large ({file_size // 1024 // 1024}MB, max {self.MAX_FILE_SIZE // 1024 // 1024}MB)"
            )
        
        try:
            # Read file content
            with open(full_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            total_lines = len(lines)
            
            # Apply line range if specified
            if start_line is not None or end_line is not None:
                start_idx = (start_line - 1) if start_line is not None else 0
                end_idx = end_line if end_line is not None else total_lines
                
                # Validate line numbers against file content
                if start_line is not None and start_line > total_lines:
                    return ToolResult(
                        success=False,
                        content="",
                        error=f"start_line ({start_line}) exceeds file length ({total_lines} lines)"
                    )
                
                if end_line is not None and end_line > total_lines:
                    return ToolResult(
                        success=False,
                        content="",
                        error=f"end_line ({end_line}) exceeds file length ({total_lines} lines)"
                    )
                
                lines = lines[start_idx:end_idx]
                actual_start = start_idx + 1
            else:
                actual_start = 1
            
            # Check if we're reading too many lines
            if len(lines) > self.MAX_LINES_READ:
                return ToolResult(
                    success=False,
                    content="",
                    error=f"Too many lines to read ({len(lines)} lines, max {self.MAX_LINES_READ}). Please specify a smaller range."
                )
            
            # Format output
            if show_line_numbers:
                # Calculate width for line numbers
                max_line_num = actual_start + len(lines) - 1
                width = len(str(max_line_num))
                
                formatted_lines = []
                for i, line in enumerate(lines):
                    line_num = actual_start + i
                    # Remove trailing newline for formatting, we'll add it back
                    line_content = line.rstrip('\n\r')
                    formatted_lines.append(f"{line_num:>{width}}│ {line_content}")
                
                content = '\n'.join(formatted_lines)
            else:
                # Just join the lines, preserving original formatting
                content = ''.join(lines).rstrip('\n\r')
            
            # Prepare metadata
            lines_read = len(lines)
            metadata = {
                "file_path": str(file_path),
                "total_lines": total_lines,
                "lines_read": lines_read,
                "file_size_bytes": file_size
            }
            
            if start_line is not None or end_line is not None:
                metadata["line_range"] = {
                    "start": actual_start,
                    "end": actual_start + lines_read - 1
                }
            
            return ToolResult(
                success=True,
                content=content,
                metadata=metadata
            )
            
        except UnicodeDecodeError:
            return ToolResult(
                success=False,
                content="",
                error="File is not a text file (binary file detected)"
            )
        except PermissionError:
            return ToolResult(
                success=False,
                content="",
                error=f"Permission denied: Cannot read {file_path}"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Error reading file: {str(e)}"
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
            ValueError: If path is invalid
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
        
        return full_path