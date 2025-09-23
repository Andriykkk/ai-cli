"""
Shell Command Tool
Execute shell commands within project context
"""

import asyncio
import subprocess
import os
import shlex
from pathlib import Path
from typing import Dict, Any, List

from ..base_tool import BaseTool, ToolResult


class RunCommandTool(BaseTool):
    """
    Tool for executing shell commands within the project directory
    
    Security features:
    - Commands run in project directory context
    - Timeout protection
    - Basic command validation
    - Output size limits
    """
    
    # Security settings
    MAX_OUTPUT_SIZE = 1024 * 1024  # 1MB max output
    DEFAULT_TIMEOUT = 30  # 30 seconds default timeout
    MAX_TIMEOUT = 300  # 5 minutes max timeout
    
    # Dangerous commands that are blocked
    BLOCKED_COMMANDS = {
        'del', 'format', 'fdisk', 'mkfs',
        'dd', 'shred', 'wipe', 'shutdown', 'reboot', 'halt',
        'sudo', 'su', 'passwd', 'chmod', 'chown', 'chgrp',
        'mount', 'umount', 'kill', 'killall', 'pkill'
    }
    
    @property
    def name(self) -> str:
        return "run_command"
    
    @property
    def description(self) -> str:
        return "Execute shell commands to explore project structure, read files, and gather information. Use this for operations like 'ls', 'cat', 'grep', 'find', 'git status', etc."
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Shell command to execute (e.g., 'ls -la', 'cat src/main.py', 'grep -r TODO src/')"
                },
                "timeout": {
                    "type": "number",
                    "description": f"Command timeout in seconds (default: {self.DEFAULT_TIMEOUT}, max: {self.MAX_TIMEOUT})",
                    "minimum": 1,
                    "maximum": self.MAX_TIMEOUT,
                    "default": self.DEFAULT_TIMEOUT
                }
            },
            "required": ["command"]
        }
    
    async def execute(self, project_path: str, **kwargs) -> ToolResult:
        """
        Execute a shell command in the project directory
        
        Args:
            project_path: Project directory to run command in
            command: Shell command to execute
            timeout: Command timeout in seconds
            
        Returns:
            ToolResult with command output or error
        """
        command = kwargs.get("command", "").strip()
        timeout = kwargs.get("timeout", self.DEFAULT_TIMEOUT)
        
        if not command:
            return ToolResult(
                success=False,
                content="",
                error="Command cannot be empty"
            )
        
        # Validate timeout
        if timeout > self.MAX_TIMEOUT:
            timeout = self.MAX_TIMEOUT
        elif timeout < 1:
            timeout = self.DEFAULT_TIMEOUT
        
        # Security validation
        security_check = self._validate_command_security(command)
        if not security_check["safe"]:
            return ToolResult(
                success=False,
                content="",
                error=f"Command blocked for security: {security_check['reason']}"
            )
        
        # Validate project path
        project_dir = Path(project_path)
        if not project_dir.exists() or not project_dir.is_dir():
            return ToolResult(
                success=False,
                content="",
                error=f"Invalid project directory: {project_path}"
            )
        
        try:
            # Execute command
            result = await self._run_command_async(command, project_dir, timeout)
            
            # Check output size
            total_output = len(result["stdout"]) + len(result["stderr"])
            if total_output > self.MAX_OUTPUT_SIZE:
                return ToolResult(
                    success=False,
                    content=result["stdout"][:self.MAX_OUTPUT_SIZE // 2],
                    error=f"Output too large ({total_output} bytes). Truncated to {self.MAX_OUTPUT_SIZE // 2} bytes.",
                    metadata={
                        "truncated": True,
                        "original_size": total_output,
                        "exit_code": result["exit_code"]
                    }
                )
            
            # Format output
            output_parts = []
            if result["stdout"]:
                output_parts.append(f"{result['stdout']}")
            if result["stderr"]:
                output_parts.append(f"{result['stderr']}")
            
            content = "\n\n".join(output_parts) if output_parts else "(no output)"
            
            # Determine success based on exit code
            success = result["exit_code"] == 0
            error = None if success else f"Command exited with code {result['exit_code']}"
            
            return ToolResult(
                success=success,
                content=content,
                error=error,
                metadata={
                    "exit_code": result["exit_code"],
                    "command": command,
                    "working_directory": str(project_dir),
                    "timeout": timeout
                }
            )
            
        except asyncio.TimeoutError:
            return ToolResult(
                success=False,
                content="",
                error=f"Command timed out after {timeout} seconds",
                metadata={
                    "timeout": True,
                    "command": command
                }
            )
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"Command execution failed: {str(e)}",
                metadata={
                    "command": command,
                    "exception": str(e)
                }
            )
    
    def _validate_command_security(self, command: str) -> Dict[str, Any]:
        """
        Validate command for security issues
        
        Args:
            command: Command to validate
            
        Returns:
            Dict with 'safe' boolean and 'reason' string
        """
        # Handle empty command
        if not command.strip():
            return {"safe": False, "reason": "Empty command"}
            
        # Parse command to get all commands (including in chains)
        try:
            command_lower = command.lower()
            
            # Check for dangerous patterns first (before parsing)
            dangerous_patterns = [
                '> /dev/', '>/dev/',
                'curl', 'wget', 'nc ', 'netcat',
                '&& del ', '; del ',
                'eval', 'exec', '$(', '`',
                'os.system', 'subprocess.call', 'subprocess.run'
            ]
            
            for pattern in dangerous_patterns:
                if pattern in command_lower:
                    return {"safe": False, "reason": f"Command contains dangerous pattern: {pattern}"}
            
            # Check for command chaining and validate each command
            # Split on common command separators
            import re
            command_parts = re.split(r'[;&|]+', command)
            
            for part in command_parts:
                part = part.strip()
                if not part:
                    continue
                    
                try:
                    # Split individual command safely
                    parts = shlex.split(part)
                    if not parts:
                        continue
                    
                    base_command = parts[0].split('/')[-1].lower()  # Get command name without path, lowercase
                    
                    # Check against blocked commands (case insensitive)
                    if base_command in self.BLOCKED_COMMANDS:
                        return {"safe": False, "reason": f"Command '{base_command}' is blocked for security"}
                        
                except ValueError as e:
                    # If we can't parse this part safely, it might be malformed
                    return {"safe": False, "reason": f"Invalid command syntax: {str(e)}"}
            
            return {"safe": True, "reason": "Command passed security validation"}
            
        except Exception as e:
            return {"safe": False, "reason": f"Command validation error: {str(e)}"}
    
    async def _run_command_async(
        self, 
        command: str, 
        working_dir: Path, 
        timeout: float
    ) -> Dict[str, Any]:
        """
        Run command asynchronously with timeout
        
        Args:
            command: Command to run
            working_dir: Working directory
            timeout: Timeout in seconds
            
        Returns:
            Dict with stdout, stderr, and exit_code
        """
        # Create subprocess
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(working_dir),
            env=os.environ.copy()
        )
        
        try:
            # Wait for completion with timeout
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
            
            return {
                "stdout": stdout.decode('utf-8', errors='replace'),
                "stderr": stderr.decode('utf-8', errors='replace'),
                "exit_code": process.returncode
            }
            
        except asyncio.TimeoutError:
            # Kill the process if it times out
            try:
                process.kill()
                await process.wait()
            except:
                pass
            raise
    
    def get_usage_examples(self) -> List[str]:
        """Get usage examples for this tool"""
        return [
            "ls -la",
            "cat src/main.py",
            "find . -name '*.py' | head -10",
            "grep -r 'TODO' src/",
            "git status",
            "git log --oneline -5",
            "tree -L 2",
            "wc -l src/*.py",
            "head -20 README.md"
        ]