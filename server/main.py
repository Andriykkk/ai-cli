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

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )