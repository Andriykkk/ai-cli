"""
Tests for ReadFileTool
"""

import pytest
import os
from pathlib import Path

from tools.filesystem.read_file_tool import ReadFileTool


class TestReadFileTool:
    """Test cases for ReadFileTool"""
    
    @pytest.fixture
    def tool(self):
        """Create ReadFileTool instance"""
        return ReadFileTool()
    
    @pytest.fixture
    def multiline_content(self):
        """Sample multiline content for testing"""
        return """Line 1: First line
Line 2: Second line
Line 3: Third line
Line 4: Fourth line
Line 5: Fifth line
Line 6: Sixth line
Line 7: Seventh line
Line 8: Eighth line
Line 9: Ninth line
Line 10: Tenth line"""
    
    @pytest.mark.asyncio
    async def test_read_entire_file(self, tool, temp_project_dir, multiline_content):
        """Test reading entire file with line numbers"""
        test_file = Path(temp_project_dir) / "test.txt"
        test_file.write_text(multiline_content)
        
        result = await tool.execute(
            project_path=temp_project_dir,
            file_path="test.txt"
        )
        
        assert result.success is True
        assert "Line 1: First line" in result.content
        assert "Line 10: Tenth line" in result.content
        
        # Check line number formatting
        assert " 1│ Line 1: First line" in result.content
        assert "10│ Line 10: Tenth line" in result.content
        
        # Check metadata
        metadata = result.metadata
        assert metadata["total_lines"] == 10
        assert metadata["lines_read"] == 10
        assert metadata["file_path"] == "test.txt"
        assert "line_range" not in metadata  # No range specified
    
    @pytest.mark.asyncio
    async def test_read_with_line_range(self, tool, temp_project_dir, multiline_content):
        """Test reading specific line range"""
        test_file = Path(temp_project_dir) / "test.txt"
        test_file.write_text(multiline_content)
        
        result = await tool.execute(
            project_path=temp_project_dir,
            file_path="test.txt",
            start_line=3,
            end_line=6
        )
        
        assert result.success is True
        assert "Line 3: Third line" in result.content
        assert "Line 6: Sixth line" in result.content
        assert "Line 1: First line" not in result.content
        assert "Line 10: Tenth line" not in result.content
        
        # Check line numbering is correct
        assert "3│ Line 3: Third line" in result.content
        assert "6│ Line 6: Sixth line" in result.content
        
        # Check metadata
        metadata = result.metadata
        assert metadata["total_lines"] == 10
        assert metadata["lines_read"] == 4  # Lines 3-6 inclusive
        assert metadata["line_range"]["start"] == 3
        assert metadata["line_range"]["end"] == 6
    
    @pytest.mark.asyncio
    async def test_read_from_start_line(self, tool, temp_project_dir, multiline_content):
        """Test reading from specific start line to end"""
        test_file = Path(temp_project_dir) / "test.txt"
        test_file.write_text(multiline_content)
        
        result = await tool.execute(
            project_path=temp_project_dir,
            file_path="test.txt",
            start_line=8
        )
        
        assert result.success is True
        assert "Line 8: Eighth line" in result.content
        assert "Line 10: Tenth line" in result.content
        assert "Line 1: First line" not in result.content
        
        metadata = result.metadata
        assert metadata["lines_read"] == 3  # Lines 8-10
        assert metadata["line_range"]["start"] == 8
        assert metadata["line_range"]["end"] == 10
    
    @pytest.mark.asyncio
    async def test_read_to_end_line(self, tool, temp_project_dir, multiline_content):
        """Test reading from start to specific end line"""
        test_file = Path(temp_project_dir) / "test.txt"
        test_file.write_text(multiline_content)
        
        result = await tool.execute(
            project_path=temp_project_dir,
            file_path="test.txt",
            end_line=3
        )
        
        assert result.success is True
        assert "Line 1: First line" in result.content
        assert "Line 3: Third line" in result.content
        assert "Line 4: Fourth line" not in result.content
        
        metadata = result.metadata
        assert metadata["lines_read"] == 3  # Lines 1-3
        assert metadata["line_range"]["start"] == 1
        assert metadata["line_range"]["end"] == 3
    
    @pytest.mark.asyncio
    async def test_read_without_line_numbers(self, tool, temp_project_dir):
        """Test reading without line number formatting"""
        content = "First line\nSecond line\nThird line"
        test_file = Path(temp_project_dir) / "test.txt"
        test_file.write_text(content)
        
        result = await tool.execute(
            project_path=temp_project_dir,
            file_path="test.txt",
            show_line_numbers=False
        )
        
        assert result.success is True
        assert result.content == "First line\nSecond line\nThird line"
        assert "│" not in result.content  # No line number formatting
    
    @pytest.mark.asyncio
    async def test_read_empty_file(self, tool, temp_project_dir):
        """Test reading empty file"""
        test_file = Path(temp_project_dir) / "empty.txt"
        test_file.write_text("")
        
        result = await tool.execute(
            project_path=temp_project_dir,
            file_path="empty.txt"
        )
        
        assert result.success is True
        assert result.content == ""
        assert result.metadata["total_lines"] == 0
        assert result.metadata["lines_read"] == 0
    
    @pytest.mark.asyncio
    async def test_read_single_line_file(self, tool, temp_project_dir):
        """Test reading file with single line (no newline)"""
        content = "Single line without newline"
        test_file = Path(temp_project_dir) / "single.txt"
        test_file.write_text(content)
        
        result = await tool.execute(
            project_path=temp_project_dir,
            file_path="single.txt"
        )
        
        assert result.success is True
        assert "1│ Single line without newline" in result.content
        assert result.metadata["total_lines"] == 1
        assert result.metadata["lines_read"] == 1
    
    @pytest.mark.asyncio
    async def test_file_not_found(self, tool, temp_project_dir):
        """Test error when file doesn't exist"""
        result = await tool.execute(
            project_path=temp_project_dir,
            file_path="nonexistent.txt"
        )
        
        assert result.success is False
        assert "File does not exist" in result.error
    
    @pytest.mark.asyncio
    async def test_path_is_directory(self, tool, temp_project_dir):
        """Test error when path points to directory"""
        test_dir = Path(temp_project_dir) / "testdir"
        test_dir.mkdir()
        
        result = await tool.execute(
            project_path=temp_project_dir,
            file_path="testdir"
        )
        
        assert result.success is False
        assert "Path is not a file" in result.error
    
    @pytest.mark.asyncio
    async def test_invalid_line_parameters(self, tool, temp_project_dir):
        """Test validation of line parameters"""
        test_file = Path(temp_project_dir) / "test.txt"
        test_file.write_text("line1\nline2\nline3")
        
        # Test start_line < 1
        result = await tool.execute(
            project_path=temp_project_dir,
            file_path="test.txt",
            start_line=0
        )
        assert result.success is False
        assert "start_line must be 1 or greater" in result.error
        
        # Test end_line < 1
        result = await tool.execute(
            project_path=temp_project_dir,
            file_path="test.txt",
            end_line=0
        )
        assert result.success is False
        assert "end_line must be 1 or greater" in result.error
        
        # Test start_line > end_line
        result = await tool.execute(
            project_path=temp_project_dir,
            file_path="test.txt",
            start_line=5,
            end_line=3
        )
        assert result.success is False
        assert "start_line cannot be greater than end_line" in result.error
    
    @pytest.mark.asyncio
    async def test_line_range_exceeds_file(self, tool, temp_project_dir):
        """Test error when line range exceeds file length"""
        test_file = Path(temp_project_dir) / "short.txt"
        test_file.write_text("line1\nline2\nline3")  # 3 lines
        
        # Test start_line exceeds file
        result = await tool.execute(
            project_path=temp_project_dir,
            file_path="short.txt",
            start_line=5
        )
        assert result.success is False
        assert "start_line (5) exceeds file length (3 lines)" in result.error
        
        # Test end_line exceeds file
        result = await tool.execute(
            project_path=temp_project_dir,
            file_path="short.txt",
            end_line=10
        )
        assert result.success is False
        assert "end_line (10) exceeds file length (3 lines)" in result.error
    
    @pytest.mark.asyncio
    async def test_large_file_rejected(self, tool, temp_project_dir):
        """Test that files larger than limit are rejected"""
        # Create a file larger than 50MB limit
        large_content = "x" * (51 * 1024 * 1024)  # 51MB
        large_file = Path(temp_project_dir) / "large.txt"
        large_file.write_text(large_content)
        
        result = await tool.execute(
            project_path=temp_project_dir,
            file_path="large.txt"
        )
        
        assert result.success is False
        assert "File too large" in result.error
        assert "50MB" in result.error
    
    @pytest.mark.asyncio
    async def test_too_many_lines_rejected(self, tool, temp_project_dir):
        """Test that reading too many lines is rejected"""
        # Create file with more than MAX_LINES_READ lines
        large_content = "\n".join(f"Line {i}" for i in range(10001))  # 10001 lines
        test_file = Path(temp_project_dir) / "many_lines.txt"
        test_file.write_text(large_content)
        
        result = await tool.execute(
            project_path=temp_project_dir,
            file_path="many_lines.txt"
        )
        
        assert result.success is False
        assert "Too many lines to read" in result.error
        assert "10000" in result.error
    
    @pytest.mark.asyncio
    async def test_binary_file_rejected(self, tool, temp_project_dir):
        """Test that binary files are rejected"""
        binary_file = Path(temp_project_dir) / "binary.bin"
        binary_file.write_bytes(b'\x00\x01\x02\x03\xff\xfe')
        
        result = await tool.execute(
            project_path=temp_project_dir,
            file_path="binary.bin"
        )
        
        assert result.success is False
        assert "binary file detected" in result.error
    
    @pytest.mark.asyncio
    async def test_path_traversal_blocked(self, tool, temp_project_dir):
        """Test that path traversal is blocked"""
        result = await tool.execute(
            project_path=temp_project_dir,
            file_path="../../../etc/passwd"
        )
        
        assert result.success is False
        assert "Path outside project directory" in result.error
    
    @pytest.mark.asyncio
    async def test_unicode_content(self, tool, temp_project_dir):
        """Test reading files with Unicode content"""
        unicode_content = """Hello 世界! 🌍
Привет мир!
Bonjour le monde!
مرحبا بالعالم!"""
        
        test_file = Path(temp_project_dir) / "unicode.txt"
        test_file.write_text(unicode_content)
        
        result = await tool.execute(
            project_path=temp_project_dir,
            file_path="unicode.txt"
        )
        
        assert result.success is True
        assert "世界" in result.content
        assert "🌍" in result.content
        assert "Привет" in result.content
    
    @pytest.mark.asyncio
    async def test_line_number_width_formatting(self, tool, temp_project_dir):
        """Test that line number width adjusts correctly"""
        # Create file with 100+ lines to test width formatting
        content = "\n".join(f"Line {i:03d}" for i in range(1, 101))  # Lines 1-100
        test_file = Path(temp_project_dir) / "many_lines.txt"
        test_file.write_text(content)
        
        result = await tool.execute(
            project_path=temp_project_dir,
            file_path="many_lines.txt",
            start_line=95,
            end_line=100
        )
        
        assert result.success is True
        # Check that line numbers are properly aligned (3-digit width)
        assert " 95│" in result.content
        assert "100│" in result.content
        # Make sure line numbers are properly right-aligned with spaces
        lines = result.content.split('\n')
        assert any(" 95│" in line for line in lines)  # 95 should have leading space
        assert any("100│" in line for line in lines)  # 100 should have no leading space
    
    @pytest.mark.asyncio
    async def test_nested_directory_file(self, tool, temp_project_dir):
        """Test reading files in nested directories"""
        nested_dir = Path(temp_project_dir) / "src" / "utils"
        nested_dir.mkdir(parents=True)
        
        content = "def helper():\n    return 'help'"
        test_file = nested_dir / "helper.py"
        test_file.write_text(content)
        
        result = await tool.execute(
            project_path=temp_project_dir,
            file_path="src/utils/helper.py"
        )
        
        assert result.success is True
        assert "def helper():" in result.content
        assert "return 'help'" in result.content
    
    @pytest.mark.asyncio
    async def test_empty_file_path(self, tool, temp_project_dir):
        """Test that empty file path is rejected"""
        result = await tool.execute(
            project_path=temp_project_dir,
            file_path=""
        )
        
        assert result.success is False
        assert "File path cannot be empty" in result.error
    
    @pytest.mark.asyncio
    async def test_invalid_project_directory(self, tool):
        """Test that invalid project directory is rejected"""
        result = await tool.execute(
            project_path="/nonexistent/directory",
            file_path="test.txt"
        )
        
        assert result.success is False
        assert "Invalid project directory" in result.error
    
    @pytest.mark.asyncio
    async def test_permission_error(self, tool, temp_project_dir):
        """Test handling of permission errors"""
        test_file = Path(temp_project_dir) / "noperm.txt"
        test_file.write_text("content")
        test_file.chmod(0o000)  # No permissions
        
        try:
            result = await tool.execute(
                project_path=temp_project_dir,
                file_path="noperm.txt"
            )
            
            # On some systems this might still work, on others it will fail
            if not result.success:
                assert "Permission denied" in result.error
        finally:
            # Restore permissions for cleanup
            test_file.chmod(0o644)
    
    @pytest.mark.asyncio
    async def test_metadata_completeness(self, tool, temp_project_dir, multiline_content):
        """Test that metadata contains all expected information"""
        test_file = Path(temp_project_dir) / "meta_test.txt"
        test_file.write_text(multiline_content)
        file_size = test_file.stat().st_size
        
        result = await tool.execute(
            project_path=temp_project_dir,
            file_path="meta_test.txt",
            start_line=2,
            end_line=5
        )
        
        assert result.success is True
        metadata = result.metadata
        
        # Check all expected metadata fields
        assert metadata["file_path"] == "meta_test.txt"
        assert metadata["total_lines"] == 10
        assert metadata["lines_read"] == 4  # Lines 2-5
        assert metadata["file_size_bytes"] == file_size
        assert metadata["line_range"]["start"] == 2
        assert metadata["line_range"]["end"] == 5