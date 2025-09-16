"""
Chat Routes
API endpoints for chat functionality
"""

import asyncio
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import sqlite3
from pathlib import Path

from memory.chat_memory import get_chat_memory

# Request/Response models
class ChatMessage(BaseModel):
    message: str
    project_id: int

class ChatResponse(BaseModel):
    response: str
    timestamp: str

# Database setup
DB_PATH = Path.home() / ".ai-cli" / "ai_cli.db"

def get_db():
    """Get database connection"""
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

async def is_chat_memory_enabled(project_id: int) -> bool:
    """Check if chat memory is enabled for a project"""
    try:
        with get_db() as conn:
            # Get project settings
            cursor = conn.execute(
                "SELECT config_data FROM project_settings WHERE project_id = ?", 
                (project_id,)
            )
            row = cursor.fetchone()
            
            if row:
                config_data = json.loads(row["config_data"])
                chat_memory_config = config_data.get("chat_memory", {})
                return chat_memory_config.get("enabled", {}).get("value", True)
            else:
                # Default to enabled if no settings exist
                return True
                
    except Exception as e:
        # Default to enabled on error
        print(f"Error checking chat memory setting: {e}")
        return True

# Create router
router = APIRouter(tags=["chat"])


def generate_claude_style_response(message: str) -> str:
    """Generate a Claude-style structured response for demo purposes"""
    
    # Different response patterns based on message content
    if "hello" in message.lower() or "hi" in message.lower():
        return """● Hello! I'm your AI coding assistant ready to help with your project.

● **Available Commands:**
  - Code analysis and review
  - Bug fixing and debugging  
  - Feature implementation
  - Documentation generation
  - Code refactoring suggestions

● **Project Integration:**
  I have access to your project context and can help with:
  - File system operations
  - Git operations  
  - Package management
  - Testing and deployment

● **Getting Started:**
  Try asking me something like:
  - "Analyze the main.py file"
  - "Help me fix this bug in my React component"
  - "Generate a README for this project" 
  - "Refactor this function to be more efficient"
  
What would you like to work on first?"""

    elif "error" in message.lower() or "bug" in message.lower():
        return """● I'll help you debug that issue! Let me analyze the problem.

● **Debugging Process:**
  ⎿ 🔍 **Step 1:** Identify the error source
     🔍 **Step 2:** Analyze the error context
     🔍 **Step 3:** Suggest potential fixes
     🔍 **Step 4:** Implement the solution

● **Common Error Types:**
  - Syntax errors
  - Runtime exceptions  
  - Logic errors
  - Performance issues
  - Memory leaks

● **To help you better, please provide:**
  - The specific error message
  - The code that's causing the issue
  - Expected vs actual behavior
  - Any relevant stack traces

```python
# Example: If you have a Python error like this:
def broken_function():
    result = undefined_variable  # NameError
    return result
```

● **Next Steps:**
  Share your error details and I'll provide a targeted solution!"""

    elif "code" in message.lower() or "analyze" in message.lower():
        return """● I'll analyze your code! Let me break down what I can help with.

● **Code Analysis Services:**
  
  **🔍 Static Analysis:**
  - Code quality assessment
  - Best practices review
  - Security vulnerability detection
  - Performance optimization suggestions

  **📊 Metrics & Insights:**
  - Code complexity analysis
  - Test coverage evaluation  
  - Documentation completeness
  - Maintainability scoring

● **Update(analysis-results)**
  ⎿ Found 3 areas for improvement in your codebase                              
       ```python
    23    def get_user_data(user_id):
    24 -      # TODO: Add input validation
    24 +      if not user_id or not isinstance(user_id, int):
    25 +          raise ValueError("Invalid user_id")
    26        return database.fetch_user(user_id)
       ```

● **Recommendations:**
  - ✅ Add input validation to public functions
  - ✅ Implement proper error handling
  - ✅ Add type hints for better code clarity
  - ✅ Consider adding unit tests

Which specific file or function would you like me to analyze in detail?"""

    else:
        return f"""● I received your message: "{message}"

● **Understanding Your Request:**
  I'm analyzing what you're asking for and preparing a helpful response.

● **AI Integration Status:**
  ⎿ 🔄 **Current Status:** Demo mode active
     🔧 **Integration:** DeepSeek, OpenAI, and Ollama models coming soon
     📊 **Features:** Full tool calling and project context awareness

● **Available Now:**
  - Project management and organization
  - File structure analysis
  - Basic code formatting
  - Development workflow assistance

● **Coming Soon:**
  - Full AI model integration
  - Advanced code generation
  - Intelligent debugging
  - Automated refactoring

● **Try asking me about:**
  - Project structure and organization
  - Code review and best practices
  - Development workflows
  - Tool recommendations

How can I help you with your project today?"""


@router.post("/chat", response_model=ChatResponse)
async def send_message(chat_message: ChatMessage):
    """Send a message to AI (placeholder for now)"""
    # TODO: Integrate with actual AI models (DeepSeek, OpenAI, Ollama)
    
    # Add 1 second delay to demo the loader
    await asyncio.sleep(1)
    
    # Create a Claude-style response for demo
    response = generate_claude_style_response(chat_message.message)
    
    # Save to chat history using ChatMemory class (if chat memory is enabled)
    if await is_chat_memory_enabled(chat_message.project_id):
        chat_memory = get_chat_memory()
        chat_memory.save_message(
            project_id=chat_message.project_id,
            user_message=chat_message.message,
            ai_response=response
        )
    
    return ChatResponse(
        response=response,
        timestamp=datetime.now().isoformat()
    )