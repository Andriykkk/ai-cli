"""
Tests for EditFileTool
"""

import pytest
import os
from pathlib import Path

from tools.filesystem.edit_file_tool import EditFileTool


class TestEditFileTool:
    """Test cases for EditFileTool"""
    
    @pytest.fixture
    def tool(self):
        """Create EditFileTool instance"""
        return EditFileTool()
    
    @pytest.fixture
    def test_file_content(self):
        """Sample file content for testing"""
        return """def hello_world():
    print("Hello, World!")
    return "greeting"

def calculate(x, y):
    result = x + y
    return result

class TestClass:
    def __init__(self):
        self.value = 42
"""
    
    @pytest.mark.asyncio
    async def test_basic_edit(self, tool, temp_project_dir, test_file_content):
        """Test basic find and replace functionality"""
        # Create test file
        test_file = Path(temp_project_dir) / "test.py"
        test_file.write_text(test_file_content)
        
        # Edit the file
        result = await tool.execute(
            project_path=temp_project_dir,
            file_path="test.py",
            old_text='print("Hello, World!")',
            new_text='print("Hello, Python!")'
        )
        
        assert result.success is True
        assert "File edited successfully" in result.content
        assert result.metadata["occurrences_replaced"] == 1
        
        # Verify the edit
        new_content = test_file.read_text()
        assert 'print("Hello, Python!")' in new_content
        assert 'print("Hello, World!")' not in new_content
        
        # Verify backup was created
        backup_file = test_file.with_suffix(".py.backup")
        assert backup_file.exists()
        assert 'print("Hello, World!")' in backup_file.read_text()
    
    @pytest.mark.asyncio
    async def test_multiline_edit(self, tool, temp_project_dir, test_file_content):
        """Test editing multiline text blocks"""
        test_file = Path(temp_project_dir) / "test.py"
        test_file.write_text(test_file_content)
        
        old_text = """def calculate(x, y):
    result = x + y
    return result"""
        
        new_text = """def calculate(x, y, operation='+'):
    if operation == '+':
        result = x + y
    elif operation == '*':
        result = x * y
    else:
        result = x + y
    return result"""
        
        result = await tool.execute(
            project_path=temp_project_dir,
            file_path="test.py",
            old_text=old_text,
            new_text=new_text
        )
        
        assert result.success is True
        new_content = test_file.read_text()
        assert "operation='+'" in new_content
        assert "elif operation == '*':" in new_content
    
    @pytest.mark.asyncio
    async def test_exact_whitespace_matching(self, tool, temp_project_dir):
        """Test that whitespace must match exactly"""
        content = "def test():\n    print('hello')\n    return True"
        test_file = Path(temp_project_dir) / "test.py"
        test_file.write_text(content)
        
        # This should fail - wrong indentation
        result = await tool.execute(
            project_path=temp_project_dir,
            file_path="test.py",
            old_text="def test():\nprint('hello')",  # Missing indentation
            new_text="def test():\nprint('hi')"
        )
        
        assert result.success is False
        assert "Text not found" in result.error
    
    @pytest.mark.asyncio
    async def test_multiple_occurrences_rejected(self, tool, temp_project_dir):
        """Test that multiple occurrences are rejected for safety"""
        content = """print("test")
print("test")
print("different")"""
        test_file = Path(temp_project_dir) / "test.py"
        test_file.write_text(content)
        
        result = await tool.execute(
            project_path=temp_project_dir,
            file_path="test.py",
            old_text='print("test")',
            new_text='print("modified")'
        )
        
        assert result.success is False
        assert "appears 2 times" in result.error
        assert "more specific" in result.error
    
    @pytest.mark.asyncio
    async def test_text_not_found_with_context(self, tool, temp_project_dir, test_file_content):
        """Test helpful error when text is not found"""
        test_file = Path(temp_project_dir) / "test.py"
        test_file.write_text(test_file_content)
        
        result = await tool.execute(
            project_path=temp_project_dir,
            file_path="test.py",
            old_text='print("Goodbye, World!")',  # Not in file
            new_text='print("Hello, Python!")'
        )
        
        assert result.success is False
        assert "Text not found" in result.error
        # Should show context from similar line
        assert "│" in result.error  # Line number format
    
    @pytest.mark.asyncio
    async def test_empty_old_text_rejected(self, tool, temp_project_dir):
        """Test that empty old_text is rejected"""
        test_file = Path(temp_project_dir) / "test.py"
        test_file.write_text("some content")
        
        result = await tool.execute(
            project_path=temp_project_dir,
            file_path="test.py",
            old_text="",
            new_text="new content"
        )
        
        assert result.success is False
        assert "Old text cannot be empty" in result.error
    
    @pytest.mark.asyncio
    async def test_file_not_found(self, tool, temp_project_dir):
        """Test error when file doesn't exist"""
        result = await tool.execute(
            project_path=temp_project_dir,
            file_path="nonexistent.py",
            old_text="old",
            new_text="new"
        )
        
        assert result.success is False
        assert "File does not exist" in result.error
    
    @pytest.mark.asyncio
    async def test_path_traversal_blocked(self, tool, temp_project_dir):
        """Test that path traversal is blocked"""
        result = await tool.execute(
            project_path=temp_project_dir,
            file_path="../../../etc/passwd",
            old_text="old",
            new_text="new"
        )
        
        assert result.success is False
        assert "Path outside project directory" in result.error
    
    @pytest.mark.asyncio
    async def test_system_file_blocked(self, tool, temp_project_dir):
        """Test that system files are blocked"""
        # Create a file that matches blocked pattern
        system_dir = Path(temp_project_dir) / "etc"
        system_dir.mkdir()
        passwd_file = system_dir / "passwd"
        passwd_file.write_text("root:x:0:0:root:/root:/bin/bash")
        
        result = await tool.execute(
            project_path=temp_project_dir,
            file_path="etc/passwd",
            old_text="root",
            new_text="admin"
        )
        
        assert result.success is False
        assert "Cannot edit system file" in result.error
    
    @pytest.mark.asyncio
    async def test_binary_file_rejected(self, tool, temp_project_dir):
        """Test that binary files are rejected"""
        # Create a binary file
        binary_file = Path(temp_project_dir) / "test.bin"
        binary_file.write_bytes(b'\x00\x01\x02\x03\xff\xfe')
        
        result = await tool.execute(
            project_path=temp_project_dir,
            file_path="test.bin",
            old_text="anything",
            new_text="replacement"
        )
        
        assert result.success is False
        assert "binary file detected" in result.error
    
    @pytest.mark.asyncio
    async def test_large_file_rejected(self, tool, temp_project_dir):
        """Test that large files are rejected"""
        # Create a file larger than the limit
        large_content = "x" * (11 * 1024 * 1024)  # 11MB, exceeds 10MB limit
        large_file = Path(temp_project_dir) / "large.txt"
        large_file.write_text(large_content)
        
        result = await tool.execute(
            project_path=temp_project_dir,
            file_path="large.txt",
            old_text="x",
            new_text="y"
        )
        
        assert result.success is False
        assert "File too large" in result.error
    
    @pytest.mark.asyncio
    async def test_permission_error(self, tool, temp_project_dir):
        """Test handling of permission errors"""
        test_file = Path(temp_project_dir) / "readonly.txt"
        test_file.write_text("content")
        test_file.chmod(0o444)  # Read-only
        
        try:
            result = await tool.execute(
                project_path=temp_project_dir,
                file_path="readonly.txt",
                old_text="content",
                new_text="new content"
            )
            
            # On some systems this might still work, on others it will fail
            if not result.success:
                assert "Permission denied" in result.error
        finally:
            # Restore permissions for cleanup
            test_file.chmod(0o644)
    
    @pytest.mark.asyncio
    async def test_metadata_information(self, tool, temp_project_dir):
        """Test that metadata contains useful information"""
        content = "line1\nline2\nline3"
        test_file = Path(temp_project_dir) / "test.txt"
        test_file.write_text(content)
        
        result = await tool.execute(
            project_path=temp_project_dir,
            file_path="test.txt",
            old_text="line2",
            new_text="modified line2"
        )
        
        assert result.success is True
        metadata = result.metadata
        assert metadata["file_path"] == "test.txt"
        assert metadata["old_length"] == 5  # len("line2")
        assert metadata["new_length"] == 14  # len("modified line2")
        assert metadata["line_difference"] == 0  # No line count change
        assert metadata["occurrences_replaced"] == 1
        assert "backup_created" in metadata
    
    @pytest.mark.asyncio
    async def test_line_difference_calculation(self, tool, temp_project_dir):
        """Test that line differences are calculated correctly"""
        content = "single line"
        test_file = Path(temp_project_dir) / "test.txt"
        test_file.write_text(content)
        
        result = await tool.execute(
            project_path=temp_project_dir,
            file_path="test.txt",
            old_text="single line",
            new_text="line 1\nline 2\nline 3"
        )
        
        assert result.success is True
        assert result.metadata["line_difference"] == 2  # Added 2 lines
    
    @pytest.mark.asyncio
    async def test_nested_directory_file(self, tool, temp_project_dir):
        """Test editing files in nested directories"""
        nested_dir = Path(temp_project_dir) / "src" / "utils"
        nested_dir.mkdir(parents=True)
        
        test_file = nested_dir / "helper.py"
        test_file.write_text("def helper():\n    return 'help'")
        
        result = await tool.execute(
            project_path=temp_project_dir,
            file_path="src/utils/helper.py",
            old_text="return 'help'",
            new_text="return 'assistance'"
        )
        
        assert result.success is True
        new_content = test_file.read_text()
        assert "return 'assistance'" in new_content
    
    @pytest.mark.asyncio
    async def test_empty_file_path(self, tool, temp_project_dir):
        """Test that empty file path is rejected"""
        result = await tool.execute(
            project_path=temp_project_dir,
            file_path="",
            old_text="old",
            new_text="new"
        )
        
        assert result.success is False
        assert "File path cannot be empty" in result.error
    
    @pytest.mark.asyncio
    async def test_invalid_project_directory(self, tool):
        """Test that invalid project directory is rejected"""
        result = await tool.execute(
            project_path="/nonexistent/directory",
            file_path="test.py",
            old_text="old",
            new_text="new"
        )
        
        assert result.success is False
        assert "Invalid project directory" in result.error