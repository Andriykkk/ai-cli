"""
Settings Routes
API endpoints for global and project settings management
"""

import json
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import sqlite3
from pathlib import Path

# Request/Response models
class GlobalSettings(BaseModel):
    config_name: str = "global"
    config_data: dict

class ProjectSettings(BaseModel):
    project_id: int
    config_data: dict

# Database setup
DB_PATH = Path.home() / ".ai-cli" / "ai_cli.db"

def get_db():
    """Get database connection"""
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

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
            "options": ["openai", "anthropic", "gemini", "deepseek", "huggingface", "custom_gpu", "ollama", "echo_test"]
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
            },
            "echo_test": {
                "api_key": {"type": "text", "value": "test-key", "masked": False},
                "model": {"type": "text", "value": "echo-test"}
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
        }
    },
    "chat_management": {
        "clear_history": {"type": "action", "label": "Clear Chat History", "description": "Delete all conversation history for this project", "destructive": True}
    },
    "project_config": {
        "tool_confirmation": {
            "type": "selector",
            "value": "dangerous_only",
            "options": ["always", "dangerous_only", "never"]
        }
    }
}

# Create router
router = APIRouter(prefix="/settings", tags=["settings"])


# Global settings endpoints
@router.get("/global")
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


@router.put("/global")
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


@router.get("/global/defaults")
async def get_default_global_settings():
    """Get default global settings"""
    return DEFAULT_GLOBAL_SETTINGS


@router.post("/global/reset")
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
@router.get("/projects/{project_id}")
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


@router.put("/projects/{project_id}")
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


@router.get("/projects/{project_id}/defaults")
async def get_default_project_settings(project_id: int):
    """Get default project settings"""
    with get_db() as conn:
        # Check if project exists
        cursor = conn.execute("SELECT id FROM projects WHERE id = ?", (project_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Project not found")
    
    return DEFAULT_PROJECT_SETTINGS


@router.post("/projects/{project_id}/reset")
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