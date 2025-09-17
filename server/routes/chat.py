"""
Chat Routes
API endpoints for chat functionality
"""

import asyncio
import json
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import sqlite3
from pathlib import Path

from memory.chat_memory import get_chat_memory
from core.chat_manager import ChatManager, ConversationStep
from core.base_types import ChatMessage as CoreChatMessage, ToolDefinition
from providers.gemini_provider import GeminiProvider
from tools.tool_manager import get_tool_manager

# Request/Response models
class ChatMessage(BaseModel):
    message: str
    project_id: int

class ChatResponse(BaseModel):
    response: str
    timestamp: str

class ToolApprovalRequest(BaseModel):
    project_id: int
    approved_tools: List[str]
    denied_tools: List[str]

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


async def get_project_settings(project_id: int) -> dict:
    """Get project settings including AI provider config"""
    try:
        with get_db() as conn:
            cursor = conn.execute(
                "SELECT config_data FROM project_settings WHERE project_id = ?", 
                (project_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return json.loads(row["config_data"])
            else:
                # Default settings
                return {
                    "ai_provider": {
                        "type": {"value": "gemini"},
                        "api_key": {"value": ""},
                        "model": {"value": "gemini-pro"}
                    }
                }
    except Exception as e:
        print(f"Error getting project settings: {e}")
        return {}

async def create_chat_manager(project_id: int, project_path: str) -> Optional[ChatManager]:
    """Create ChatManager with configured AI provider"""
    settings = await get_project_settings(project_id)
    ai_config = settings.get("ai_provider", {})
    
    provider_type = ai_config.get("type", {}).get("value", "gemini")
    api_key = ai_config.get("api_key", {}).get("value", "")
    model = ai_config.get("model", {}).get("value", "gemini-pro")
    
    if not api_key:
        return None
    
    # Create provider (only Gemini for now)
    if provider_type == "gemini":
        provider = GeminiProvider(api_key=api_key, model=model)
    else:
        return None
    
    # Create chat manager
    chat_manager = ChatManager(
        provider=provider,
        project_id=project_id,
        project_path=project_path
    )
    
    # Set available tools
    tool_manager = get_tool_manager()
    available_tools = tool_manager.get_available_tools()
    chat_manager.set_available_tools(available_tools)
    
    return chat_manager

@router.post("/chat/stream")
async def send_message_stream(chat_message: ChatMessage):
    """Send a message to AI with streaming response and tool calling"""
    
    # Get project path from database
    try:
        with get_db() as conn:
            cursor = conn.execute("SELECT path FROM projects WHERE id = ?", (chat_message.project_id,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Project not found")
            project_path = row["path"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    # Create chat manager
    chat_manager = await create_chat_manager(chat_message.project_id, project_path)
    if not chat_manager:
        raise HTTPException(status_code=400, detail="AI provider not configured or API key missing")
    
    # Get conversation history if chat memory is enabled
    conversation_history = []
    if await is_chat_memory_enabled(chat_message.project_id):
        chat_memory = get_chat_memory()
        history = chat_memory.get_recent_history(chat_message.project_id, limit=20)
        
        # Convert to CoreChatMessage format
        for msg in history:
            conversation_history.append(CoreChatMessage(
                role="user",
                content=msg.user_message
            ))
            conversation_history.append(CoreChatMessage(
                role="assistant",
                content=msg.ai_response
            ))
    
    async def stream_generator():
        try:
            async for step in chat_manager.start_conversation(
                user_message=chat_message.message,
                conversation_history=conversation_history
            ):
                # Send step as JSON line
                step_data = {
                    "type": "conversation_step",
                    "state": step.state.value,
                    "content": step.content,
                    "tool_calls": step.tool_calls,
                    "tool_results": step.tool_results,
                    "error": step.error,
                    "timestamp": datetime.now().isoformat()
                }
                yield f"data: {json.dumps(step_data)}\n\n"
                
        except Exception as e:
            error_data = {
                "type": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            yield f"data: {json.dumps(error_data)}\n\n"
    
    return StreamingResponse(
        stream_generator(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache"}
    )

@router.post("/chat/tool-approval")
async def handle_tool_approval(approval_request: ToolApprovalRequest):
    """Handle user's tool approval decision"""
    
    # Get project path from database
    try:
        with get_db() as conn:
            cursor = conn.execute("SELECT path FROM projects WHERE id = ?", (approval_request.project_id,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Project not found")
            project_path = row["path"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    # Create chat manager (should reuse conversation state in real implementation)
    chat_manager = await create_chat_manager(approval_request.project_id, project_path)
    if not chat_manager:
        raise HTTPException(status_code=400, detail="AI provider not configured or API key missing")
    
    async def approval_stream_generator():
        try:
            async for step in chat_manager.handle_tool_approval(
                approved_tools=approval_request.approved_tools,
                denied_tools=approval_request.denied_tools
            ):
                # Send step as JSON line
                step_data = {
                    "type": "conversation_step",
                    "state": step.state.value,
                    "content": step.content,
                    "tool_calls": step.tool_calls,
                    "tool_results": step.tool_results,
                    "error": step.error,
                    "timestamp": datetime.now().isoformat()
                }
                yield f"data: {json.dumps(step_data)}\n\n"
                
        except Exception as e:
            error_data = {
                "type": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            yield f"data: {json.dumps(error_data)}\n\n"
    
    return StreamingResponse(
        approval_stream_generator(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache"}
    )