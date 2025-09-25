"""
File Editing Tool
Edit files using find-and-replace operations
"""

import os
import shutil
from pathlib import Path
from typing import Dict, Any

from ..base_tool import BaseTool, ToolResult


class EditFileTool(BaseTool):
    """
    Tool for editing files using find-and-replace operations
    
    Security features:
    - Path validation and traversal protection
    - File backup before editing
    - Exact text matching required
    - File size limits
    """
    
    # Security settings
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB max file size
    BACKUP_SUFFIX = ".backup"
    
    # Blocked file patterns for security
    BLOCKED_PATTERNS = [
        "/etc/", "/usr/", "/var/", "/sys/", "/proc/", "/dev/",
        "passwd", "shadow", "sudoers", ".ssh/", ".git/config"
    ]
    
    @property
    def name(self) -> str:
        return "edit_file"
    
    @property
    def description(self) -> str:
        return "Edit files by finding exact text and replacing it with new text. Creates backup before editing."
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to edit (relative to project root)"
                },
                "old_text": {
                    "type": "string", 
                    "description": "Exact text to find and replace (must match exactly including whitespace)"
                },
                "new_text": {
                    "type": "string",
                    "description": "New text to replace the old text with"
                }
            },
            "required": ["file_path", "old_text", "new_text"]
        }
    
    async def execute(self, project_path: str, **kwargs) -> ToolResult:
        """
        Edit a file using find-and-replace
        
        Args:
            project_path: Project directory
            file_path: Path to file to edit
            old_text: Exact text to find
            new_text: Text to replace with
            
        Returns:
            ToolResult with edit result
        """
        file_path = kwargs.get("file_path", "").strip()
        old_text = kwargs.get("old_text", "")
        new_text = kwargs.get("new_text", "")
        
        if not file_path:
            return ToolResult(
                success=False,
                content="",
                error="File path cannot be empty"
            )
        
        if not old_text:
            return ToolResult(
                success=False,
                content="", 
                error="Old text cannot be empty"
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
        
        # Check file size
        if full_path.stat().st_size > self.MAX_FILE_SIZE:
            return ToolResult(
                success=False,
                content="",
                error=f"File too large (max {self.MAX_FILE_SIZE // 1024 // 1024}MB)"
            )
        
        try:
            # Read current file content
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if old_text exists
            if old_text not in content:
                # Provide helpful context about what's actually in the file
                lines = content.split('\n')
                context_lines = []
                
                # Try to find similar content by looking for common keywords
                old_lines = old_text.split('\n')
                if old_lines:
                    first_line = old_lines[0].strip()
                    # Extract meaningful words (remove common symbols)
                    import re
                    keywords = re.findall(r'\w+', first_line.lower())
                    
                    for i, line in enumerate(lines):
                        line_words = re.findall(r'\w+', line.lower())
                        # Check if any significant keyword matches
                        if keywords and any(word in line_words for word in keywords if len(word) > 2):
                            start = max(0, i - 2)
                            end = min(len(lines), i + 5)
                            context_lines = lines[start:end]
                            break
                
                if context_lines:
                    context = '\n'.join(f"{start+i+1:3d}│ {line}" for i, line in enumerate(context_lines))
                    error_msg = f"Text not found. Similar content found:\n{context}"
                else:
                    error_msg = "Text not found in file"
                
                return ToolResult(
                    success=False,
                    content="",
                    error=error_msg
                )
            
            # Count occurrences
            occurrences = content.count(old_text)
            if occurrences > 1:
                return ToolResult(
                    success=False,
                    content="",
                    error=f"Text appears {occurrences} times in file. Please be more specific to match exactly one occurrence."
                )
            
            # Create backup
            backup_path = full_path.with_suffix(full_path.suffix + self.BACKUP_SUFFIX)
            shutil.copy2(full_path, backup_path)
            
            # Perform replacement
            new_content = content.replace(old_text, new_text)
            
            # Write new content
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            # Calculate changes
            old_lines = old_text.count('\n') + 1
            new_lines = new_text.count('\n') + 1
            line_diff = new_lines - old_lines
            
            # Create a simple diff-like display for the content
            diff_content = f"--- {file_path} (original)\n+++ {file_path} (edited)\n\n"
            diff_content += f"@@ Replaced content @@\n"
            diff_content += f"- {old_text}\n"
            diff_content += f"+ {new_text}"
            
            return ToolResult(
                success=True,
                content=diff_content,
                metadata={
                    "file_path": str(file_path),
                    "backup_created": str(backup_path),
                    "old_length": len(old_text),
                    "new_length": len(new_text), 
                    "line_difference": line_diff,
                    "occurrences_replaced": 1,
                    "old_text": old_text,
                    "new_text": new_text,
                    "operation_summary": f"File edited successfully. Replaced {len(old_text)} characters with {len(new_text)} characters."
                }
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
                error=f"Permission denied: Cannot edit {file_path}"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Error editing file: {str(e)}"
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
                raise ValueError(f"Cannot edit system file: {file_path}")
        
        return full_path