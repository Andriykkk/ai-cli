#!/usr/bin/env python3

"""
AI CLI Server - FastAPI backend for project management and AI interactions
"""

import os
from datetime import datetime
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import sqlite3
import json
from pathlib import Path

# Import all route modules
from routes.basic import router as basic_router
from routes.projects import router as projects_router
from routes.chat import router as chat_router
from routes.settings import router as settings_router
from routes.chat_memory import router as chat_memory_router

# Models are now defined in their respective route files

# Database setup
DB_PATH = Path.home() / ".ai-cli" / "ai_cli.db"

def get_db():
    """Get database connection"""
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Initialize database with required tables"""
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                path TEXT NOT NULL,
                description TEXT DEFAULT '',
                model_provider TEXT DEFAULT 'deepseek',
                model_name TEXT DEFAULT 'deepseek-chat',
                created_at TEXT NOT NULL,
                last_used TEXT,
                memory_enabled BOOLEAN DEFAULT 1,
                tools_enabled BOOLEAN DEFAULT 1
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                response TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects (id)
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS global_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                config_name TEXT UNIQUE NOT NULL,
                config_data TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS project_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                config_data TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
                UNIQUE(project_id)
            )
        """)
        
        conn.commit()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup"""
    init_database()
    yield

# FastAPI app
app = FastAPI(
    title="AI CLI Server",
    description="Backend server for AI-powered CLI tool",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all route modules
app.include_router(basic_router)
app.include_router(projects_router)
app.include_router(chat_router)
app.include_router(settings_router)
app.include_router(chat_memory_router)

# Routes
@app.get("/")
async def root():
    return {"message": "AI CLI Server", "version": "0.1.0"}

@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

@app.get("/projects", response_model=List[Project])
async def get_projects():
    """Get all projects"""
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM projects ORDER BY created_at DESC")
        projects = []
        for row in cursor.fetchall():
            projects.append(Project(
                id=row["id"],
                name=row["name"],
                path=row["path"],
                description=row["description"] or "",
                model_provider=row["model_provider"],
                model_name=row["model_name"],
                created_at=row["created_at"],
                last_used=row["last_used"],
                memory_enabled=bool(row["memory_enabled"]),
                tools_enabled=bool(row["tools_enabled"])
            ))
        return projects

@app.post("/projects", response_model=Project)
async def create_project(project: ProjectCreate):
    """Create a new project"""
    try:
        with get_db() as conn:
            # Check for duplicate names only (paths can be duplicated)
            cursor = conn.execute(
                "SELECT id FROM projects WHERE name = ?", 
                (project.name,)
            )
            if cursor.fetchone():
                raise HTTPException(
                    status_code=400, 
                    detail="Project with this name already exists"
                )
            
            # Create project
            cursor = conn.execute("""
                INSERT INTO projects (name, path, description, created_at)
                VALUES (?, ?, ?, ?)
            """, (project.name, project.path, project.description, datetime.now().isoformat()))
            
            project_id = cursor.lastrowid
            conn.commit()
            
            # Return created project
            cursor = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
            row = cursor.fetchone()
            
            return Project(
                id=row["id"],
                name=row["name"],
                path=row["path"],
                description=row["description"] or "",
                model_provider=row["model_provider"],
                model_name=row["model_name"],
                created_at=row["created_at"],
                last_used=row["last_used"],
                memory_enabled=bool(row["memory_enabled"]),
                tools_enabled=bool(row["tools_enabled"])
            )
            
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=400, 
            detail="Project with this name already exists"
        )

@app.put("/projects/{project_id}", response_model=Project)
async def update_project(project_id: int, project_update: ProjectUpdate):
    """Update a project"""
    with get_db() as conn:
        # Check if project exists
        cursor = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        existing = cursor.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Build update query with validation
        updates = []
        params = []
        
        if project_update.name is not None:
            # Check if new name conflicts with other projects
            cursor = conn.execute(
                "SELECT id FROM projects WHERE name = ? AND id != ?", 
                (project_update.name, project_id)
            )
            if cursor.fetchone():
                raise HTTPException(
                    status_code=400, 
                    detail="Project with this name already exists"
                )
            updates.append("name = ?")
            params.append(project_update.name)
            
        if project_update.path is not None:
            # Paths can be duplicated, so no validation needed
            updates.append("path = ?")
            params.append(project_update.path)
            
        if project_update.description is not None:
            updates.append("description = ?")
            params.append(project_update.description)
        
        if updates:
            params.append(project_id)
            query = f"UPDATE projects SET {', '.join(updates)} WHERE id = ?"
            conn.execute(query, params)
            conn.commit()
        
        # Return updated project
        cursor = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        row = cursor.fetchone()
        
        return Project(
            id=row["id"],
            name=row["name"],
            path=row["path"],
            description=row["description"] or "",
            model_provider=row["model_provider"],
            model_name=row["model_name"],
            created_at=row["created_at"],
            last_used=row["last_used"],
            memory_enabled=bool(row["memory_enabled"]),
            tools_enabled=bool(row["tools_enabled"])
        )

@app.delete("/projects/{project_id}")
async def delete_project(project_id: int):
    """Delete a project"""
    with get_db() as conn:
        cursor = conn.execute("SELECT id FROM projects WHERE id = ?", (project_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Project not found")
        
        conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        conn.execute("DELETE FROM chat_history WHERE project_id = ?", (project_id,))
        conn.commit()
        
        return {"message": "Project deleted successfully"}

@app.post("/projects/{project_id}/use")
async def use_project(project_id: int):
    """Mark project as used (update last_used timestamp)"""
    with get_db() as conn:
        cursor = conn.execute("SELECT id FROM projects WHERE id = ?", (project_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Project not found")
        
        conn.execute(
            "UPDATE projects SET last_used = ? WHERE id = ?",
            (datetime.now().isoformat(), project_id)
        )
        conn.commit()
        
        return {"message": "Project usage updated"}

@app.post("/chat", response_model=ChatResponse)
async def send_message(chat_message: ChatMessage):
    """Send a message to AI (placeholder for now)"""
    # TODO: Integrate with actual AI models (DeepSeek, OpenAI, Ollama)
    
    # Add 1 second delay to demo the loader
    import asyncio
    await asyncio.sleep(1)
    
    # Create a Claude-style response for demo
    response = generate_claude_style_response(chat_message.message)
    
    # Save to chat history using ChatMemory class
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

# Default global settings (UI, system-wide preferences)
DEFAULT_GLOBAL_SETTINGS = {
    "ui": {
        "theme": {
            "type": "selector",
            "value": "default",
            "options": ["default", "dark", "light", "custom"]
        },
        "response_animation": {"type": "boolean", "value": True},
        "show_token_usage": {"type": "boolean", "value": True},
        "show_response_time": {"type": "boolean", "value": True},
        "auto_scroll": {"type": "boolean", "value": True}
    },
    "system": {
        "request_timeout": {"type": "number", "value": 30, "min": 1, "max": 300},
        "max_retry_attempts": {"type": "number", "value": 3, "min": 1, "max": 10},
        "streaming": {"type": "boolean", "value": True},
        "debug_mode": {"type": "boolean", "value": False}
    }
}

# Default project settings (AI provider, tools, memory)
DEFAULT_PROJECT_SETTINGS = {
    "ai_provider": {
        "default_provider": {
            "type": "selector",
            "value": "openai",
            "options": ["openai", "anthropic", "gemini", "deepseek", "huggingface", "custom_gpu", "ollama"]
        },
        "providers": {
            "openai": {
                "api_key": {"type": "text", "value": "", "masked": True},
                "model": {"type": "text", "value": "gpt-4"},
                "base_url": {"type": "text", "value": "", "optional": True},
                "organization_id": {"type": "text", "value": "", "optional": True}
            },
            "anthropic": {
                "api_key": {"type": "text", "value": "", "masked": True},
                "model": {"type": "text", "value": "claude-3-sonnet-20240229"}
            },
            "gemini": {
                "api_key": {"type": "text", "value": "", "masked": True},
                "model": {"type": "text", "value": "gemini-pro"}
            },
            "deepseek": {
                "api_key": {"type": "text", "value": "", "masked": True},
                "model": {"type": "text", "value": "deepseek-chat"}
            },
            "huggingface": {
                "api_key": {"type": "text", "value": "", "masked": True},
                "model": {"type": "text", "value": "microsoft/DialoGPT-medium"},
                "base_url": {"type": "text", "value": "", "optional": True}
            },
            "custom_gpu": {
                "api_key": {"type": "text", "value": "", "masked": True},
                "model": {"type": "text", "value": ""},
                "base_url": {"type": "text", "value": ""}
            },
            "ollama": {
                "base_url": {"type": "text", "value": "http://localhost:11434"},
                "model": {"type": "text", "value": "llama2"}
            }
        }
    },
    "generation": {
        "temperature": {"type": "number", "value": 0.7, "min": 0.0, "max": 2.0, "step": 0.1},
        "max_tokens": {"type": "number", "value": 4000, "min": 1, "max": 32000},
        "top_p": {"type": "number", "value": 1.0, "min": 0.0, "max": 1.0, "step": 0.1},
        "frequency_penalty": {"type": "number", "value": 0, "min": -2.0, "max": 2.0, "step": 0.1},
        "presence_penalty": {"type": "number", "value": 0, "min": -2.0, "max": 2.0, "step": 0.1},
        "timeout": {"type": "number", "value": 30, "min": 1, "max": 300}
    },
    "tools": {
        "filesystem": {
            "enabled": {"type": "boolean", "value": True},
            "read_files": {"type": "boolean", "value": True},
            "write_files": {"type": "boolean", "value": True},
            "list_directory": {"type": "boolean", "value": True},
            "search_files": {"type": "boolean", "value": True}
        },
        "shell": {
            "enabled": {"type": "boolean", "value": True},
            "run_commands": {"type": "boolean", "value": True},
            "get_environment": {"type": "boolean", "value": True}
        },
        "web": {
            "enabled": {"type": "boolean", "value": True},
            "web_search": {"type": "boolean", "value": True},
            "fetch_url": {"type": "boolean", "value": True}
        },
        "memory": {
            "enabled": {"type": "boolean", "value": True},
            "save_memory": {"type": "boolean", "value": True},
            "retrieve_memory": {"type": "boolean", "value": True}
        }
    },
    "memory": {
        "backend": {
            "type": "selector",
            "value": "sqlite",
            "options": ["sqlite", "postgresql", "vector_db"]
        },
        "conversation_history": {"type": "boolean", "value": True},
        "max_context_length": {"type": "number", "value": 8000, "min": 1000, "max": 50000},
        "summarization": {"type": "boolean", "value": True},
        "auto_save": {
            "type": "selector",
            "value": "every_message",
            "options": ["every_message", "every_5_messages", "manual"]
        }
    },
    "project_config": {
        "tool_confirmation": {
            "type": "selector",
            "value": "dangerous_only",
            "options": ["always", "dangerous_only", "never"]
        }
    }
}

# Global settings endpoints
@app.get("/settings/global")
async def get_global_settings():
    """Get current global settings"""
    with get_db() as conn:
        cursor = conn.execute("SELECT config_data FROM global_settings WHERE config_name = ?", ("global",))
        row = cursor.fetchone()
        
        if row:
            return json.loads(row["config_data"])
        else:
            # Return default global settings if none exist
            return DEFAULT_GLOBAL_SETTINGS

@app.put("/settings/global")
async def update_global_settings(settings: GlobalSettings):
    """Update global settings"""
    with get_db() as conn:
        cursor = conn.execute("SELECT id FROM global_settings WHERE config_name = ?", (settings.config_name,))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing settings
            conn.execute("""
                UPDATE global_settings SET config_data = ?, updated_at = ? WHERE config_name = ?
            """, (json.dumps(settings.config_data), datetime.now().isoformat(), settings.config_name))
        else:
            # Insert new settings
            conn.execute("""
                INSERT INTO global_settings (config_name, config_data, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            """, (
                settings.config_name, 
                json.dumps(settings.config_data), 
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
        
        conn.commit()
        return {"message": "Global settings updated successfully"}

@app.get("/settings/global/defaults")
async def get_default_global_settings():
    """Get default global settings"""
    return DEFAULT_GLOBAL_SETTINGS

@app.post("/settings/global/reset")
async def reset_global_settings():
    """Reset global settings to defaults"""
    with get_db() as conn:
        cursor = conn.execute("SELECT id FROM global_settings WHERE config_name = ?", ("global",))
        existing = cursor.fetchone()
        
        if existing:
            conn.execute("""
                UPDATE global_settings SET config_data = ?, updated_at = ? WHERE config_name = ?
            """, (json.dumps(DEFAULT_GLOBAL_SETTINGS), datetime.now().isoformat(), "global"))
        else:
            conn.execute("""
                INSERT INTO global_settings (config_name, config_data, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            """, (
                "global", 
                json.dumps(DEFAULT_GLOBAL_SETTINGS), 
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
        
        conn.commit()
        return {"message": "Global settings reset to defaults"}

# Project settings endpoints
@app.get("/projects/{project_id}/settings")
async def get_project_settings(project_id: int):
    """Get project-specific settings"""
    with get_db() as conn:
        # Check if project exists
        cursor = conn.execute("SELECT id FROM projects WHERE id = ?", (project_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get project settings
        cursor = conn.execute("SELECT config_data FROM project_settings WHERE project_id = ?", (project_id,))
        row = cursor.fetchone()
        
        if row:
            return json.loads(row["config_data"])
        else:
            # Return default project settings if none exist
            return DEFAULT_PROJECT_SETTINGS

@app.put("/projects/{project_id}/settings")
async def update_project_settings(project_id: int, settings: ProjectSettings):
    """Update project-specific settings"""
    with get_db() as conn:
        # Check if project exists
        cursor = conn.execute("SELECT id FROM projects WHERE id = ?", (project_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Check if project settings exist
        cursor = conn.execute("SELECT id FROM project_settings WHERE project_id = ?", (project_id,))
        existing = cursor.fetchone()
        
        if existing:
            # Update existing settings
            conn.execute("""
                UPDATE project_settings SET config_data = ?, updated_at = ? WHERE project_id = ?
            """, (json.dumps(settings.config_data), datetime.now().isoformat(), project_id))
        else:
            # Insert new settings
            conn.execute("""
                INSERT INTO project_settings (project_id, config_data, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            """, (
                project_id,
                json.dumps(settings.config_data), 
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
        
        conn.commit()
        return {"message": "Project settings updated successfully"}

@app.get("/projects/{project_id}/settings/defaults")
async def get_default_project_settings(project_id: int):
    """Get default project settings"""
    with get_db() as conn:
        # Check if project exists
        cursor = conn.execute("SELECT id FROM projects WHERE id = ?", (project_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Project not found")
    
    return DEFAULT_PROJECT_SETTINGS

@app.post("/projects/{project_id}/settings/reset")
async def reset_project_settings(project_id: int):
    """Reset project settings to defaults"""
    with get_db() as conn:
        # Check if project exists
        cursor = conn.execute("SELECT id FROM projects WHERE id = ?", (project_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Check if project settings exist
        cursor = conn.execute("SELECT id FROM project_settings WHERE project_id = ?", (project_id,))
        existing = cursor.fetchone()
        
        if existing:
            conn.execute("""
                UPDATE project_settings SET config_data = ?, updated_at = ? WHERE project_id = ?
            """, (json.dumps(DEFAULT_PROJECT_SETTINGS), datetime.now().isoformat(), project_id))
        else:
            conn.execute("""
                INSERT INTO project_settings (project_id, config_data, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            """, (
                project_id,
                json.dumps(DEFAULT_PROJECT_SETTINGS), 
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
        
        conn.commit()
        return {"message": "Project settings reset to defaults"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )