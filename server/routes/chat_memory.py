"""
Chat Memory Routes
API endpoints for managing project chat history
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from memory.chat_memory import get_chat_memory, ChatMessage


# Request/Response models
class ChatHistoryResponse(BaseModel):
    messages: List[dict]
    total_count: int
    project_id: int


class ClearHistoryResponse(BaseModel):
    message: str
    deleted_count: int
    project_id: int


class MessageCountResponse(BaseModel):
    count: int
    project_id: int


class SearchRequest(BaseModel):
    query: str
    limit: int = 20


class SearchResponse(BaseModel):
    messages: List[dict]
    query: str
    project_id: int


# Create router
router = APIRouter(prefix="/projects", tags=["chat-memory"])


@router.get("/{project_id}/chat/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    project_id: int, 
    limit: Optional[int] = None
):
    """
    Get chat history for a project
    
    Args:
        project_id: Project ID to get history for
        limit: Maximum number of messages to return (optional)
        
    Returns:
        ChatHistoryResponse: Chat messages and metadata
    """
    try:
        chat_memory = get_chat_memory()
        
        if limit:
            messages = chat_memory.get_recent_history(project_id, limit)
        else:
            messages = chat_memory.get_project_history(project_id)
        
        total_count = chat_memory.get_message_count(project_id)
        
        return ChatHistoryResponse(
            messages=[msg.to_dict() for msg in messages],
            total_count=total_count,
            project_id=project_id
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to get chat history: {str(e)}"
        )


@router.get("/{project_id}/chat/history/recent", response_model=ChatHistoryResponse)
async def get_recent_chat_history(
    project_id: int, 
    limit: int = 50
):
    """
    Get recent chat history for a project (default 50 messages)
    
    Args:
        project_id: Project ID to get history for
        limit: Number of recent messages to return
        
    Returns:
        ChatHistoryResponse: Recent chat messages and metadata
    """
    try:
        chat_memory = get_chat_memory()
        messages = chat_memory.get_recent_history(project_id, limit)
        total_count = chat_memory.get_message_count(project_id)
        
        return ChatHistoryResponse(
            messages=[msg.to_dict() for msg in messages],
            total_count=total_count,
            project_id=project_id
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to get recent chat history: {str(e)}"
        )


@router.delete("/{project_id}/chat/history", response_model=ClearHistoryResponse)
async def clear_chat_history(project_id: int):
    """
    Clear all chat history for a project
    
    Args:
        project_id: Project ID to clear history for
        
    Returns:
        ClearHistoryResponse: Confirmation and deletion count
    """
    try:
        chat_memory = get_chat_memory()
        deleted_count = chat_memory.clear_project_history(project_id)
        
        return ClearHistoryResponse(
            message="Chat history cleared successfully",
            deleted_count=deleted_count,
            project_id=project_id
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to clear chat history: {str(e)}"
        )


@router.get("/{project_id}/chat/history/count", response_model=MessageCountResponse)
async def get_message_count(project_id: int):
    """
    Get total number of messages for a project
    
    Args:
        project_id: Project ID to count messages for
        
    Returns:
        MessageCountResponse: Message count for the project
    """
    try:
        chat_memory = get_chat_memory()
        count = chat_memory.get_message_count(project_id)
        
        return MessageCountResponse(
            count=count,
            project_id=project_id
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to get message count: {str(e)}"
        )


@router.post("/{project_id}/chat/history/search", response_model=SearchResponse)
async def search_chat_history(project_id: int, search_request: SearchRequest):
    """
    Search chat history for specific text
    
    Args:
        project_id: Project ID to search in
        search_request: Search parameters (query and limit)
        
    Returns:
        SearchResponse: Matching messages
    """
    try:
        chat_memory = get_chat_memory()
        messages = chat_memory.search_messages(
            project_id, 
            search_request.query, 
            search_request.limit
        )
        
        return SearchResponse(
            messages=[msg.to_dict() for msg in messages],
            query=search_request.query,
            project_id=project_id
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to search chat history: {str(e)}"
        )


@router.delete("/{project_id}/chat/history/messages/{message_id}")
async def delete_message(project_id: int, message_id: int):
    """
    Delete a specific message from chat history
    
    Args:
        project_id: Project ID (for validation)
        message_id: Message ID to delete
        
    Returns:
        dict: Confirmation message
    """
    try:
        chat_memory = get_chat_memory()
        deleted = chat_memory.delete_message(message_id)
        
        if not deleted:
            raise HTTPException(
                status_code=404, 
                detail="Message not found"
            )
        
        return {
            "message": "Message deleted successfully",
            "message_id": message_id,
            "project_id": project_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to delete message: {str(e)}"
        )