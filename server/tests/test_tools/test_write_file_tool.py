"""
Tests for WriteFileTool
"""

import pytest
import os
from pathlib import Path

from tools.filesystem.write_file_tool import WriteFileTool


class TestWriteFileTool:
    """Test cases for WriteFileTool"""
    
    @pytest.fixture
    def tool(self):
        """Create WriteFileTool instance"""
        return WriteFileTool()
    
    @pytest.mark.asyncio
    async def test_create_new_file(self, tool, temp_project_dir):
        """Test creating a new file"""
        content = "print('Hello, World!')\n"
        
        result = await tool.execute(
            project_path=temp_project_dir,
            file_path="hello.py",
            content=content
        )
        
        assert result.success is True
        assert "File created successfully" in result.content
        assert result.metadata["action"] == "created"
        assert result.metadata["bytes_written"] == len(content.encode())
        assert result.metadata["lines_written"] == 1
        assert result.metadata["old_size"] is None
        
        # Verify file was created
        test_file = Path(temp_project_dir) / "hello.py"
        assert test_file.exists()
        assert test_file.read_text() == content
    
    @pytest.mark.asyncio
    async def test_overwrite_existing_file(self, tool, temp_project_dir):
        """Test overwriting an existing file"""
        # Create initial file
        test_file = Path(temp_project_dir) / "test.py"
        initial_content = "old content"
        test_file.write_text(initial_content)
        initial_size = len(initial_content.encode())
        
        new_content = "new content with more text"
        result = await tool.execute(
            project_path=temp_project_dir,
            file_path="test.py",
            content=new_content
        )
        
        assert result.success is True
        assert "File overwritten successfully" in result.content
        assert result.metadata["action"] == "overwritten"
        assert result.metadata["bytes_written"] == len(new_content.encode())
        assert result.metadata["old_size"] == initial_size
        
        # Verify file was overwritten
        assert test_file.read_text() == new_content
    
    @pytest.mark.asyncio
    async def test_create_nested_directories(self, tool, temp_project_dir):
        """Test creating files in nested directories that don't exist"""
        content = "nested file content"
        
        result = await tool.execute(
            project_path=temp_project_dir,
            file_path="src/utils/helper.py",
            content=content
        )
        
        assert result.success is True
        assert "File created successfully" in result.content
        
        # Verify directories were created
        nested_file = Path(temp_project_dir) / "src" / "utils" / "helper.py"
        assert nested_file.exists()
        assert nested_file.read_text() == content
        assert nested_file.parent.exists()
        assert nested_file.parent.parent.exists()
    
    @pytest.mark.asyncio
    async def test_empty_content(self, tool, temp_project_dir):
        """Test writing empty content"""
        result = await tool.execute(
            project_path=temp_project_dir,
            file_path="empty.txt",
            content=""
        )
        
        assert result.success is True
        assert result.metadata["bytes_written"] == 0
        assert result.metadata["lines_written"] == 0
        
        test_file = Path(temp_project_dir) / "empty.txt"
        assert test_file.exists()
        assert test_file.read_text() == ""
    
    @pytest.mark.asyncio
    async def test_multiline_content(self, tool, temp_project_dir):
        """Test writing multiline content"""
        content = """#!/usr/bin/env python3
# -*- coding: utf-8 -*-

def main():
    print("Hello, World!")

if __name__ == "__main__":
    main()
"""
        
        result = await tool.execute(
            project_path=temp_project_dir,
            file_path="script.py",
            content=content
        )
        
        assert result.success is True
        # Content ends with newline, so line count should be max(1, newline_count)
        expected_lines = max(1, content.count('\n')) if content.endswith('\n') else content.count('\n') + 1
        assert result.metadata["lines_written"] == expected_lines
        
        test_file = Path(temp_project_dir) / "script.py"
        assert test_file.read_text() == content
    
    @pytest.mark.asyncio
    async def test_unicode_content(self, tool, temp_project_dir):
        """Test writing Unicode content"""
        content = "Hello 世界! 🌍\nПривет мир!\n"
        
        result = await tool.execute(
            project_path=temp_project_dir,
            file_path="unicode.txt",
            content=content
        )
        
        assert result.success is True
        test_file = Path(temp_project_dir) / "unicode.txt"
        assert test_file.read_text() == content
    
    @pytest.mark.asyncio
    async def test_large_content_rejected(self, tool, temp_project_dir):
        """Test that content larger than limit is rejected"""
        large_content = "x" * (11 * 1024 * 1024)  # 11MB, exceeds 10MB limit
        
        result = await tool.execute(
            project_path=temp_project_dir,
            file_path="large.txt",
            content=large_content
        )
        
        assert result.success is False
        assert "Content too large" in result.error
        assert "10MB" in result.error
    
    @pytest.mark.asyncio
    async def test_empty_file_path(self, tool, temp_project_dir):
        """Test that empty file path is rejected"""
        result = await tool.execute(
            project_path=temp_project_dir,
            file_path="",
            content="content"
        )
        
        assert result.success is False
        assert "File path cannot be empty" in result.error
    
    @pytest.mark.asyncio
    async def test_path_traversal_blocked(self, tool, temp_project_dir):
        """Test that path traversal is blocked"""
        result = await tool.execute(
            project_path=temp_project_dir,
            file_path="../../../etc/passwd",
            content="malicious content"
        )
        
        assert result.success is False
        assert "Path outside project directory" in result.error
    
    @pytest.mark.asyncio
    async def test_system_location_blocked(self, tool, temp_project_dir):
        """Test that system locations are blocked"""
        result = await tool.execute(
            project_path=temp_project_dir,
            file_path="etc/passwd",
            content="malicious content"
        )
        
        assert result.success is False
        assert "Cannot write to system location" in result.error
    
    @pytest.mark.asyncio
    async def test_absolute_path_converted(self, tool, temp_project_dir):
        """Test that absolute paths are converted to relative"""
        content = "test content"
        
        result = await tool.execute(
            project_path=temp_project_dir,
            file_path="/subdir/test.txt",  # Absolute path
            content=content
        )
        
        assert result.success is True
        
        # Should create file at subdir/test.txt relative to project
        test_file = Path(temp_project_dir) / "subdir" / "test.txt"
        assert test_file.exists()
        assert test_file.read_text() == content
    
    @pytest.mark.asyncio
    async def test_permission_error_handling(self, tool, temp_project_dir):
        """Test handling of permission errors"""
        # Create a directory with no write permissions
        readonly_dir = Path(temp_project_dir) / "readonly"
        readonly_dir.mkdir()
        readonly_dir.chmod(0o444)  # Read-only
        
        try:
            result = await tool.execute(
                project_path=temp_project_dir,
                file_path="readonly/test.txt",
                content="content"
            )
            
            # On some systems this might still work, on others it will fail
            if not result.success:
                assert "Permission denied" in result.error
        finally:
            # Restore permissions for cleanup
            readonly_dir.chmod(0o755)
    
    @pytest.mark.asyncio
    async def test_invalid_project_directory(self, tool):
        """Test that invalid project directory is rejected"""
        result = await tool.execute(
            project_path="/nonexistent/directory",
            file_path="test.py",
            content="content"
        )
        
        assert result.success is False
        assert "Invalid project directory" in result.error
    
    @pytest.mark.asyncio
    async def test_various_file_extensions(self, tool, temp_project_dir):
        """Test writing files with various extensions"""
        test_cases = [
            ("script.py", "print('Python')"),
            ("style.css", "body { color: red; }"),
            ("page.html", "<h1>Hello</h1>"),
            ("data.json", '{"key": "value"}'),
            ("README.md", "# Project Title"),
            ("config.yml", "key: value"),
            ("no_extension", "content without extension")
        ]
        
        for file_path, content in test_cases:
            result = await tool.execute(
                project_path=temp_project_dir,
                file_path=file_path,
                content=content
            )
            
            assert result.success is True, f"Failed to write {file_path}"
            
            test_file = Path(temp_project_dir) / file_path
            assert test_file.exists()
            assert test_file.read_text() == content
    
    @pytest.mark.asyncio
    async def test_line_counting_edge_cases(self, tool, temp_project_dir):
        """Test line counting for various content types"""
        test_cases = [
            ("", 0),  # Empty content
            ("single line", 1),  # No newline at end
            ("single line\n", 1),  # Single newline at end
            ("line1\nline2", 2),  # Two lines, no final newline
            ("line1\nline2\n", 2),  # Two lines with final newline
            ("\n\n\n", 3),  # Only newlines
        ]
        
        for content, expected_lines in test_cases:
            result = await tool.execute(
                project_path=temp_project_dir,
                file_path=f"test_{expected_lines}_lines.txt",
                content=content
            )
            
            assert result.success is True
            assert result.metadata["lines_written"] == expected_lines, \
                f"Expected {expected_lines} lines for content {repr(content)}, got {result.metadata['lines_written']}"
    
    @pytest.mark.asyncio
    async def test_metadata_completeness(self, tool, temp_project_dir):
        """Test that metadata contains all expected fields"""
        content = "line 1\nline 2\nline 3"
        
        result = await tool.execute(
            project_path=temp_project_dir,
            file_path="metadata_test.txt",
            content=content
        )
        
        assert result.success is True
        metadata = result.metadata
        
        # Check all expected metadata fields
        assert "file_path" in metadata
        assert "action" in metadata
        assert "bytes_written" in metadata
        assert "lines_written" in metadata
        assert "old_size" in metadata
        
        assert metadata["file_path"] == "metadata_test.txt"
        assert metadata["action"] == "created"
        assert metadata["bytes_written"] == len(content.encode())
        assert metadata["lines_written"] == 3
        assert metadata["old_size"] is None
    
    @pytest.mark.asyncio
    async def test_replace_vs_create_metadata(self, tool, temp_project_dir):
        """Test that metadata correctly distinguishes create vs overwrite"""
        file_path = "replace_test.txt"
        
        # First write (create)
        result1 = await tool.execute(
            project_path=temp_project_dir,
            file_path=file_path,
            content="original content"
        )
        
        assert result1.success is True
        assert result1.metadata["action"] == "created"
        assert result1.metadata["old_size"] is None
        
        # Second write (overwrite)
        result2 = await tool.execute(
            project_path=temp_project_dir,
            file_path=file_path,
            content="new content"
        )
        
        assert result2.success is True
        assert result2.metadata["action"] == "overwritten"
        assert result2.metadata["old_size"] == len("original content".encode())