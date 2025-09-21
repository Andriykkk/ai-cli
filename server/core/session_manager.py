"""
Simple MCP-like Session Manager
Maintains conversation state during tool calling workflows
"""

import uuid
import time
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from core.base_types import ChatMessage
from core.chat_manager import ChatManager


@dataclass
class ConversationSession:
    """Represents an active conversation session"""
    session_id: str
    project_id: int
    project_path: str
    chat_manager: ChatManager
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity = time.time()
    
    def is_expired(self, timeout: float = 3600) -> bool:
        """Check if session has expired (default 1 hour)"""
        return time.time() - self.last_activity > timeout


class SessionManager:
    """
    Manages active conversation sessions for tool calling
    
    This replaces the need to recreate ChatManager instances and lose state
    during tool approval workflows
    """
    
    def __init__(self):
        self.sessions: Dict[str, ConversationSession] = {}
        self.project_sessions: Dict[int, str] = {}  # project_id -> session_id mapping
    
    def create_session(self, project_id: int, project_path: str, chat_manager: ChatManager) -> str:
        """Create a new conversation session"""
        session_id = str(uuid.uuid4())
        
        # Clean up any existing session for this project
        self.cleanup_project_session(project_id)
        
        session = ConversationSession(
            session_id=session_id,
            project_id=project_id,
            project_path=project_path,
            chat_manager=chat_manager
        )
        
        self.sessions[session_id] = session
        self.project_sessions[project_id] = session_id
        
        print(f"Created session {session_id} for project {project_id}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        """Get session by ID"""
        session = self.sessions.get(session_id)
        if session:
            session.update_activity()
        return session
    
    def get_project_session(self, project_id: int) -> Optional[ConversationSession]:
        """Get active session for a project"""
        session_id = self.project_sessions.get(project_id)
        if session_id:
            return self.get_session(session_id)
        return None
    
    def cleanup_project_session(self, project_id: int):
        """Clean up existing session for a project"""
        if project_id in self.project_sessions:
            old_session_id = self.project_sessions[project_id]
            if old_session_id in self.sessions:
                del self.sessions[old_session_id]
            del self.project_sessions[project_id]
    
    def cleanup_session(self, session_id: str):
        """Clean up a specific session"""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            # Remove from project mapping
            if session.project_id in self.project_sessions:
                del self.project_sessions[session.project_id]
            # Remove session
            del self.sessions[session_id]
            print(f"Cleaned up session {session_id}")
    
    def cleanup_expired_sessions(self, timeout: float = 3600):
        """Clean up expired sessions"""
        expired_sessions = [
            session_id for session_id, session in self.sessions.items()
            if session.is_expired(timeout)
        ]
        
        for session_id in expired_sessions:
            self.cleanup_session(session_id)
        
        if expired_sessions:
            print(f"Cleaned up {len(expired_sessions)} expired sessions")
    
    def get_session_count(self) -> int:
        """Get number of active sessions"""
        return len(self.sessions)


# Global session manager instance
_session_manager = SessionManager()


def get_session_manager() -> SessionManager:
    """Get the global session manager instance"""
    return _session_manager