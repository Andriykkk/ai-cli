"""Configuration management for AI CLI."""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel
from datetime import datetime


class ProjectConfig(BaseModel):
    """Configuration for a single project."""
    name: str
    path: str
    description: str = ""
    model_provider: str = "deepseek"  # deepseek, openai, ollama
    model_name: str = "deepseek-chat"
    created_at: str
    last_used: Optional[str] = None
    memory_enabled: bool = True
    tools_enabled: bool = True


class Config(BaseModel):
    """Main configuration container."""
    projects: List[ProjectConfig] = []
    default_model_provider: str = "deepseek"
    default_model_name: str = "deepseek-chat"
    api_keys: Dict[str, str] = {}


class ConfigManager:
    """Manages configuration persistence and loading."""
    
    def __init__(self):
        self.config_dir = Path.home() / ".ai-cli"
        self.config_file = self.config_dir / "config.json"
        self.config_dir.mkdir(exist_ok=True)
    
    def load_config(self) -> Config:
        """Load configuration from file."""
        if not self.config_file.exists():
            return Config()
        
        try:
            with open(self.config_file, 'r') as f:
                data = json.load(f)
            return Config(**data)
        except (json.JSONDecodeError, ValueError):
            return Config()
    
    def save_config(self, config: Config) -> None:
        """Save configuration to file."""
        # Ensure directory exists
        self.config_dir.mkdir(exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(config.model_dump(), f, indent=2)
    
    def add_project(self, name: str, path: str, description: str = "") -> ProjectConfig:
        """Add a new project to configuration."""
        config = self.load_config()
        
        # Check if project already exists
        for project in config.projects:
            if project.name == name or project.path == path:
                raise ValueError(f"Project with name '{name}' or path '{path}' already exists")
        
        project = ProjectConfig(
            name=name,
            path=path,
            description=description,
            created_at=datetime.now().isoformat()
        )
        
        config.projects.append(project)
        self.save_config(config)
        return project
    
    def remove_project(self, name: str) -> bool:
        """Remove a project from configuration."""
        config = self.load_config()
        original_count = len(config.projects)
        config.projects = [p for p in config.projects if p.name != name]
        
        if len(config.projects) < original_count:
            self.save_config(config)
            return True
        return False
    
    def get_project(self, name: str) -> Optional[ProjectConfig]:
        """Get a specific project by name."""
        config = self.load_config()
        for project in config.projects:
            if project.name == name:
                return project
        return None
    
    def update_project_last_used(self, name: str) -> None:
        """Update the last used timestamp for a project."""
        config = self.load_config()
        for project in config.projects:
            if project.name == name:
                project.last_used = datetime.now().isoformat()
                break
        self.save_config(config)
    
    def update_project(self, name: str, **kwargs) -> bool:
        """Update project properties and save automatically."""
        config = self.load_config()
        for project in config.projects:
            if project.name == name:
                for key, value in kwargs.items():
                    if hasattr(project, key):
                        setattr(project, key, value)
                self.save_config(config)
                return True
        return False