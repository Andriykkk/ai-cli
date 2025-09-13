# AI CLI - Code Development Assistant

A Python-based CLI tool that provides AI-powered assistance for code development with project memory and tool calling capabilities.

## Features

- 🎯 **Project Management**: Organize your coding projects with persistent configurations
- 💬 **Interactive Chat**: Chat with AI models directly in your terminal  
- 🔧 **Tool Calling**: AI can execute tools and commands to help with development
- 🧠 **Memory**: Project-specific memory for context retention
- 🔌 **Multiple Providers**: Support for DeepSeek, OpenAI, and local models via Ollama

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd ai-cli
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install in development mode:
```bash
pip install -e .
```

## Usage

### Start the CLI interface:
```bash
ai-cli
```

### Command line options:
```bash
# Add a new project
ai-cli add-project "My Project" "/path/to/project" --description "Project description"

# List all projects
ai-cli list-projects

# Remove a project
ai-cli remove-project "My Project"
```

## Configuration

Configuration is stored in `~/.ai-cli/config.json`. The first time you run the CLI, it will be created automatically.

## Project Structure

```
ai-cli/
├── src/ai_cli/
│   ├── __init__.py
│   ├── cli.py          # Main CLI entry point
│   ├── config.py       # Configuration management
│   └── ui.py           # User interface components
├── pyproject.toml      # Package configuration
├── requirements.txt    # Dependencies
└── README.md
```

## Next Steps

- [ ] Implement AI model integration (DeepSeek, OpenAI, Ollama)
- [ ] Add tool calling system
- [ ] Implement project memory with vector embeddings
- [ ] Add file operations and shell command tools
- [ ] API key management