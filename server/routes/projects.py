"""
Project Management Routes
API endpoints for CRUD operations on projects
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import sqlite3
from pathlib import Path

# Request/Response models
class ProjectCreate(BaseModel):
    name: str
    path: str
    description: str = ""

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    path: Optional[str] = None
    description: Optional[str] = None
    model_provider: Optional[str] = None
    model_name: Optional[str] = None
    memory_enabled: Optional[bool] = None
    tools_enabled: Optional[bool] = None

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

# Database setup
DB_PATH = Path.home() / ".ai-cli" / "ai_cli.db"

def get_db():
    """Get database connection"""
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Create router
router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=List[Project])
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


@router.post("", response_model=Project)
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


@router.put("/{project_id}", response_model=Project)
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


@router.delete("/{project_id}")
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


@router.post("/{project_id}/use")
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