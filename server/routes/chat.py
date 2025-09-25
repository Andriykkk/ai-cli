"""
Chat Routes
API endpoints for chat functionality
"""

import asyncio
import json
import logging
import traceback
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ValidationError
import sqlite3
from pathlib import Path

from memory.chat_memory import get_chat_memory
from core.chat_manager import ChatManager, ConversationStep
from core.base_types import ChatMessage as CoreChatMessage, ToolDefinition
from core.session_manager import get_session_manager
from providers.gemini_provider import GeminiProvider
from providers.echo_test_provider import EchoTestProvider
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
    session_id: str
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

# Chat memory is always enabled now

# Setup logger
logger = logging.getLogger(__name__)

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
        logger.info(f"Getting settings for project {project_id}")
        with get_db() as conn:
            cursor = conn.execute(
                "SELECT config_data FROM project_settings WHERE project_id = ?", 
                (project_id,)
            )
            row = cursor.fetchone()
            
            if row:
                config_data = json.loads(row["config_data"])
                logger.info(f"Found project settings: {config_data}")
                return config_data
            else:
                logger.warning(f"No settings found for project {project_id}, using defaults")
                # Default settings
                default_settings = {
                    "ai_provider": {
                        "type": {"value": "gemini"},
                        "api_key": {"value": ""},
                        "model": {"value": "gemini-pro"}
                    }
                }
                return default_settings
    except Exception as e:
        logger.error(f"Error getting project settings: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {}

async def create_chat_manager(project_id: int, project_path: str) -> Optional[ChatManager]:
    """Create ChatManager with configured AI provider"""
    try:
        settings = await get_project_settings(project_id)
        ai_config = settings.get("ai_provider", {})
        
        # Handle the actual database structure
        default_provider = ai_config.get("default_provider", {}).get("value", "gemini")
        providers = ai_config.get("providers", {})
        
        # Get provider config
        provider_config = providers.get(default_provider, {})
        api_key = provider_config.get("api_key", {}).get("value", "")
        model = provider_config.get("model", {}).get("value", "gemini-pro")
        
        logger.info(f"Creating chat manager: provider={default_provider}, model={model}, has_api_key={bool(api_key)}")
        
        # Create provider
        if default_provider == "gemini":
            if not api_key:
                logger.error(f"No API key configured for provider {default_provider}")
                return None
            provider = GeminiProvider(api_key=api_key, model=model)
        elif default_provider == "echo_test":
            print("##### USING ECHO TEST PROVIDER")
            provider = EchoTestProvider(api_key=api_key or "test-key", model=model)
        else:
            logger.error(f"Unsupported provider type: {default_provider}")
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
        logger.info(f"Setting {len(available_tools)} available tools")
        chat_manager.set_available_tools(available_tools)
        
        return chat_manager
        
    except Exception as e:
        logger.error(f"Error creating chat manager: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

@router.post("/chat/stream")
async def send_message_stream(chat_message: ChatMessage):
    """Send a message to AI with streaming response and tool calling"""
    
    try:
        logger.info(f"Stream request for project {chat_message.project_id}")
        
        # Get project path from database
        with get_db() as conn:
            cursor = conn.execute("SELECT path FROM projects WHERE id = ?", (chat_message.project_id,))
            row = cursor.fetchone()
            if not row:
                logger.error(f"Project {chat_message.project_id} not found")
                raise HTTPException(status_code=404, detail="Project not found")
            project_path = row["path"]
        
        # Create chat manager
        chat_manager = await create_chat_manager(chat_message.project_id, project_path)
        if not chat_manager:
            logger.error(f"Failed to create chat manager for project {chat_message.project_id}")
            raise HTTPException(status_code=400, detail="AI provider not configured or API key missing")
        
        # Create session for this conversation
        session_manager = get_session_manager()
        session_id = session_manager.create_session(chat_message.project_id, project_path, chat_manager)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in stream endpoint: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    
    # Get conversation history (always enabled)
    conversation_history = []
    chat_memory = get_chat_memory()
    history = chat_memory.get_recent_history(chat_message.project_id, limit=20)
    
    # Convert to CoreChatMessage format
    for msg in history:
        conversation_history.append(CoreChatMessage(
            role="user",
            content=msg.message
        ))
        conversation_history.append(CoreChatMessage(
            role="assistant",
            content=msg.response
        ))
    
    async def stream_generator():
        try:
            logger.info(f"Starting conversation stream for: {chat_message.message}")
            async for step in chat_manager.start_conversation(
                user_message=chat_message.message,
                conversation_history=conversation_history
            ):
                logger.info(f"Yielding step: state={step.state}, content={step.content[:100] if step.content else None}, tool_calls={len(step.tool_calls) if step.tool_calls else 0}")
                
                # Convert tool_calls to JSON serializable format
                tool_calls_json = None
                if step.tool_calls:
                    tool_calls_json = [
                        {
                            "id": tc.id,
                            "name": tc.name,
                            "arguments": tc.arguments
                        }
                        for tc in step.tool_calls
                    ]
                
                # Send step as JSON line
                step_data = {
                    "type": "conversation_step",
                    "state": step.state.value,
                    "content": step.content,
                    "tool_calls": tool_calls_json,
                    "tool_results": step.tool_results,
                    "error": step.error,
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat()
                }
                yield f"data: {json.dumps(step_data)}\n\n"
                logger.info(f"Successfully yielded step: {step.state.value}")
                
                # Clean up session when conversation is complete (no tool calls)
                if step.state.value == "completed":
                    session_manager.cleanup_session(session_id)
                    logger.info(f"Cleaned up completed session {session_id}")
                elif step.state.value == "tool_approval":
                    logger.info(f"Tool approval step yielded, keeping session {session_id} alive")
            
            logger.info("Conversation stream completed")
                
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
    """Handle user's tool approval decision using session state"""
    
    # Get session manager and retrieve active session
    session_manager = get_session_manager()
    session = session_manager.get_session(approval_request.session_id)
    
    if not session:
        logger.error(f"Session {approval_request.session_id} not found or expired")
        raise HTTPException(status_code=404, detail="Session not found or expired")
    
    if session.project_id != approval_request.project_id:
        logger.error(f"Session project mismatch: {session.project_id} != {approval_request.project_id}")
        raise HTTPException(status_code=400, detail="Session project mismatch")
    
    # Use the existing chat manager with preserved state
    chat_manager = session.chat_manager
    logger.info(f"Using session {approval_request.session_id} with {len(chat_manager.messages)} messages")
    
    async def approval_stream_generator():
        try:
            async for step in chat_manager.continue_conversation_after_tools(
                approved_tools=approval_request.approved_tools,
                denied_tools=approval_request.denied_tools
            ):
                # Convert tool_calls to JSON serializable format (same as original endpoint)
                tool_calls_json = None
                if step.tool_calls:
                    tool_calls_json = [
                        {
                            "id": tc.id,
                            "name": tc.name,
                            "arguments": tc.arguments
                        }
                        for tc in step.tool_calls
                    ]
                
                # Send step as JSON line
                step_data = {
                    "type": "conversation_step",
                    "state": step.state.value,
                    "content": step.content,
                    "tool_calls": tool_calls_json,
                    "tool_results": step.tool_results,
                    "error": step.error,
                    "session_id": approval_request.session_id,
                    "timestamp": datetime.now().isoformat()
                }
                yield f"data: {json.dumps(step_data)}\n\n"
                
                # Clean up session when conversation is complete
                if step.state.value == "completed":
                    session_manager.cleanup_session(approval_request.session_id)
                    logger.info(f"Cleaned up completed session {approval_request.session_id}")
                
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

@router.delete("/chat/history/{project_id}")
async def clear_chat_history(project_id: int):
    """Clear all chat history for a project"""
    try:
        chat_memory = get_chat_memory()
        deleted_count = chat_memory.clear_project_history(project_id)
        
        return {
            "success": True,
            "message": f"Cleared {deleted_count} messages from chat history",
            "deleted_count": deleted_count
        }
        
    except Exception as e:
        logger.error(f"Error clearing chat history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to clear chat history: {str(e)}")