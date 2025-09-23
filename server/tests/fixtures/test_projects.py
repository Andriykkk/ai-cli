"""
Test project fixtures and utilities
"""

import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any


def create_python_project(temp_dir: str) -> Dict[str, Any]:
    """Create a Python project structure for testing"""
    project_path = Path(temp_dir)
    
    # Create directory structure
    (project_path / "src").mkdir()
    (project_path / "tests").mkdir()
    (project_path / "docs").mkdir()
    (project_path / "scripts").mkdir()
    
    # Create Python files
    (project_path / "src" / "__init__.py").write_text("")
    (project_path / "src" / "main.py").write_text('''#!/usr/bin/env python3
"""Main application module"""

def main():
    print("Hello, World!")
    return 0

if __name__ == "__main__":
    main()
''')
    
    (project_path / "src" / "utils.py").write_text('''"""Utility functions"""

def helper_function():
    """A helper function for testing"""
    return "test_result"

def calculate(a, b):
    """Calculate sum"""
    return a + b

class TestClass:
    """Test class for grep testing"""
    def __init__(self):
        self.value = "TODO: implement this"
        
    def method(self):
        return "method_result"
''')
    
    # Create test files
    (project_path / "tests" / "__init__.py").write_text("")
    (project_path / "tests" / "test_main.py").write_text('''"""Tests for main module"""
import unittest
from src.main import main

class TestMain(unittest.TestCase):
    def test_main(self):
        self.assertEqual(main(), 0)
''')
    
    # Create documentation
    (project_path / "README.md").write_text('''# Test Project

This is a test project for testing shell commands.

## Features
- Python application
- Unit tests
- Documentation

## TODO
- Add more features
- Improve documentation
''')
    
    (project_path / "docs" / "api.md").write_text('''# API Documentation

## Functions

### main()
The main function of the application.

### helper_function()
A utility function that returns test data.
''')
    
    # Create configuration files
    (project_path / "requirements.txt").write_text('''requests==2.28.0
pytest==7.2.0
black==22.10.0
flake8==5.0.4
''')
    
    (project_path / "pyproject.toml").write_text('''[build-system]
requires = ["setuptools", "wheel"]

[tool.black]
line-length = 88

[tool.pytest.ini_options]
testpaths = ["tests"]
''')
    
    (project_path / ".gitignore").write_text('''__pycache__/
*.pyc
*.pyo
*.pyd
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

.env
.venv
env/
venv/
ENV/
''')
    
    # Create shell scripts
    (project_path / "scripts" / "build.sh").write_text('''#!/bin/bash
echo "Building project..."
python -m pytest tests/
echo "Build complete"
''')
    
    (project_path / "scripts" / "run.sh").write_text('''#!/bin/bash
echo "Starting application..."
python src/main.py
''')
    
    # Make scripts executable
    (project_path / "scripts" / "build.sh").chmod(0o755)
    (project_path / "scripts" / "run.sh").chmod(0o755)
    
    return {
        "path": str(project_path),
        "files": {
            "python": ["src/main.py", "src/utils.py", "tests/test_main.py"],
            "docs": ["README.md", "docs/api.md"],
            "configs": ["requirements.txt", "pyproject.toml", ".gitignore"],
            "scripts": ["scripts/build.sh", "scripts/run.sh"]
        },
        "structure": {
            "directories": ["src", "tests", "docs", "scripts"],
            "total_files": 11
        }
    }


def create_web_project(temp_dir: str) -> Dict[str, Any]:
    """Create a web project structure for testing"""
    project_path = Path(temp_dir)
    
    # Create directory structure
    (project_path / "public").mkdir()
    (project_path / "src").mkdir()
    (project_path / "src" / "components").mkdir()
    (project_path / "src" / "styles").mkdir()
    
    # Create HTML file
    (project_path / "public" / "index.html").write_text('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test Web App</title>
    <link rel="stylesheet" href="../src/styles/main.css">
</head>
<body>
    <div id="app">
        <h1>Hello, World!</h1>
        <p>This is a test web application.</p>
    </div>
    <script src="../src/main.js"></script>
</body>
</html>
''')
    
    # Create JavaScript files
    (project_path / "src" / "main.js").write_text('''// Main application script
console.log("Application starting...");

function initApp() {
    const app = document.getElementById('app');
    if (app) {
        console.log("App initialized");
        // TODO: Add more functionality
    }
}

document.addEventListener('DOMContentLoaded', initApp);
''')
    
    (project_path / "src" / "components" / "header.js").write_text('''// Header component
function createHeader() {
    const header = document.createElement('header');
    header.innerHTML = '<h1>Test App</h1>';
    return header;
}

export { createHeader };
''')
    
    # Create CSS files
    (project_path / "src" / "styles" / "main.css").write_text('''/* Main styles */
body {
    font-family: Arial, sans-serif;
    margin: 0;
    padding: 20px;
    background-color: #f5f5f5;
}

#app {
    max-width: 800px;
    margin: 0 auto;
    background: white;
    padding: 20px;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

h1 {
    color: #333;
    text-align: center;
}

/* TODO: Add more styles */
''')
    
    # Create package.json
    (project_path / "package.json").write_text('''{
  "name": "test-web-project",
  "version": "1.0.0",
  "description": "A test web project",
  "main": "src/main.js",
  "scripts": {
    "start": "python -m http.server 8000",
    "build": "echo 'Building project...'",
    "test": "echo 'Running tests...'"
  },
  "keywords": ["test", "web", "javascript"],
  "author": "Test User",
  "license": "MIT"
}
''')
    
    return {
        "path": str(project_path),
        "files": {
            "html": ["public/index.html"],
            "javascript": ["src/main.js", "src/components/header.js"],
            "css": ["src/styles/main.css"],
            "configs": ["package.json"]
        },
        "structure": {
            "directories": ["public", "src", "src/components", "src/styles"],
            "total_files": 5
        }
    }