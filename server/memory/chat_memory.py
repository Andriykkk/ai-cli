"""
Chat Memory Management for Project Conversations
Handles saving, loading, and managing chat history for projects
"""

import sqlite3
from datetime import datetime
from typing import List, Dict, Optional, Any
from pathlib import Path
from dataclasses import dataclass


@dataclass
class ChatMessage:
    """Represents a single chat message with metadata"""
    id: int
    project_id: int
    message: str
    response: str
    timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "project_id": self.project_id,
            "message": self.message,
            "response": self.response,
            "timestamp": self.timestamp
        }


class ChatMemory:
    """
    Manages chat history for projects using SQLite storage
    Separate from AI memory tools - this is just conversation persistence
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """Initialize chat memory with database connection"""
        if db_path is None:
            db_path = Path.home() / ".ai-cli" / "ai_cli.db"
        
        self.db_path = db_path
        self._ensure_database_exists()
    
    def _ensure_database_exists(self):
        """Ensure the database and chat_history table exist"""
        self.db_path.parent.mkdir(exist_ok=True)
        
        with self._get_connection() as conn:
            # Create index for better performance on project_id queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_chat_history_project_timestamp 
                ON chat_history(project_id, timestamp DESC)
            """)
            conn.commit()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def save_message(self, project_id: int, user_message: str, ai_response: str) -> int:
        """
        Save a chat message pair to the database
        
        Args:
            project_id: The project this conversation belongs to
            user_message: User's input message
            ai_response: AI's response message
            
        Returns:
            int: ID of the saved chat message
        """
        timestamp = datetime.now().isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO chat_history (project_id, message, response, timestamp)
                VALUES (?, ?, ?, ?)
            """, (project_id, user_message, ai_response, timestamp))
            
            message_id = cursor.lastrowid
            conn.commit()
            return message_id
    
    def get_project_history(self, project_id: int, limit: Optional[int] = None) -> List[ChatMessage]:
        """
        Get chat history for a specific project
        
        Args:
            project_id: The project to get history for
            limit: Maximum number of messages to return (None for all)
            
        Returns:
            List[ChatMessage]: List of chat messages ordered by timestamp (oldest first)
        """
        with self._get_connection() as conn:
            query = """
                SELECT id, project_id, message, response, timestamp
                FROM chat_history 
                WHERE project_id = ? 
                ORDER BY timestamp ASC
            """
            
            if limit:
                query += f" LIMIT {limit}"
            
            cursor = conn.execute(query, (project_id,))
            rows = cursor.fetchall()
            
            return [
                ChatMessage(
                    id=row["id"],
                    project_id=row["project_id"],
                    message=row["message"],
                    response=row["response"],
                    timestamp=row["timestamp"]
                )
                for row in rows
            ]
    
    def get_recent_history(self, project_id: int, limit: int = 50) -> List[ChatMessage]:
        """
        Get recent chat history for a project (most recent messages)
        
        Args:
            project_id: The project to get history for
            limit: Number of recent messages to return
            
        Returns:
            List[ChatMessage]: List of recent messages ordered by timestamp (oldest first)
        """
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT id, project_id, message, response, timestamp
                FROM chat_history 
                WHERE project_id = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (project_id, limit))
            
            rows = cursor.fetchall()
            
            # Reverse to get oldest first (chronological order for display)
            messages = [
                ChatMessage(
                    id=row["id"],
                    project_id=row["project_id"],
                    message=row["message"],
                    response=row["response"],
                    timestamp=row["timestamp"]
                )
                for row in reversed(rows)
            ]
            
            return messages
    
    def clear_project_history(self, project_id: int) -> int:
        """
        Clear all chat history for a project
        
        Args:
            project_id: The project to clear history for
            
        Returns:
            int: Number of messages deleted
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM chat_history WHERE project_id = ?", 
                (project_id,)
            )
            deleted_count = cursor.rowcount
            conn.commit()
            return deleted_count
    
    def get_message_count(self, project_id: int) -> int:
        """
        Get total number of messages for a project
        
        Args:
            project_id: The project to count messages for
            
        Returns:
            int: Number of messages in project history
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) as count FROM chat_history WHERE project_id = ?",
                (project_id,)
            )
            return cursor.fetchone()["count"]
    
    def delete_message(self, message_id: int) -> bool:
        """
        Delete a specific message from history
        
        Args:
            message_id: ID of the message to delete
            
        Returns:
            bool: True if message was deleted, False if not found
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM chat_history WHERE id = ?",
                (message_id,)
            )
            deleted = cursor.rowcount > 0
            conn.commit()
            return deleted
    
    def search_messages(self, project_id: int, query: str, limit: int = 20) -> List[ChatMessage]:
        """
        Search for messages containing specific text
        
        Args:
            project_id: The project to search in
            query: Text to search for
            limit: Maximum number of results
            
        Returns:
            List[ChatMessage]: Messages containing the search query
        """
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT id, project_id, message, response, timestamp
                FROM chat_history 
                WHERE project_id = ? AND (message LIKE ? OR response LIKE ?)
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (project_id, f"%{query}%", f"%{query}%", limit))
            
            rows = cursor.fetchall()
            
            return [
                ChatMessage(
                    id=row["id"],
                    project_id=row["project_id"],
                    message=row["message"],
                    response=row["response"],
                    timestamp=row["timestamp"]
                )
                for row in rows
            ]


# Singleton instance for global use
_chat_memory_instance = None


def get_chat_memory() -> ChatMemory:
    """Get the global ChatMemory instance"""
    global _chat_memory_instance
    if _chat_memory_instance is None:
        _chat_memory_instance = ChatMemory()
    return _chat_memory_instance