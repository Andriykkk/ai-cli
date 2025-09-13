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

# Database models
class ProjectCreate(BaseModel):
    name: str
    path: str
    description: str = ""

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    path: Optional[str] = None
    description: Optional[str] = None

class Project(BaseModel):
    id: int
    name: str
    path: str
    description: str
    model_provider: str = "deepseek"
    model_name: str = "deepseek-chat"
    created_at: str
    last_used: Optional[str] = None
    memory_enabled: bool = True
    tools_enabled: bool = True

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
    
    # Save to chat history
    with get_db() as conn:
        conn.execute("""
            INSERT INTO chat_history (project_id, message, response, timestamp)
            VALUES (?, ?, ?, ?)
        """, (
            chat_message.project_id,
            chat_message.message,
            response,
            datetime.now().isoformat()
        ))
        conn.commit()
    
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

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )