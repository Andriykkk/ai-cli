"""
Chat Manager - Orchestrates AI conversations with tool calling loops
"""

from typing import Dict, List, Optional, Any, AsyncIterator
from dataclasses import dataclass
from enum import Enum

from .base_provider import BaseModelProvider
from .base_types import ChatMessage, ChatResponse, ToolDefinition, ToolCall
from tools.tool_manager import get_tool_manager
from memory.chat_memory import get_chat_memory


class ConversationState(Enum):
    """States in the conversation flow"""
    GENERATING = "generating"  # AI is generating response
    TOOL_APPROVAL = "tool_approval"  # Waiting for user to approve tool calls
    TOOL_EXECUTING = "tool_executing"  # Executing approved tools
    COMPLETED = "completed"  # Conversation completed


@dataclass
class ConversationStep:
    """Represents one step in the conversation"""
    state: ConversationState
    content: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    tool_results: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None


class ChatManager:
    """
    Orchestrates AI conversations with tool calling support
    
    Responsibilities:
    - Manage conversation flow with AI provider
    - Handle tool calling loops with user approval
    - Stream responses back to client
    - Save conversation to memory
    """
    
    def __init__(self, provider: BaseModelProvider, project_id: int, project_path: str):
        """
        Initialize chat manager
        
        Args:
            provider: AI model provider (e.g., GeminiProvider)
            project_id: Project ID for memory and settings
            project_path: Path to project directory for tools
        """
        self.provider = provider
        self.project_id = project_id
        self.project_path = project_path
        self.tool_manager = get_tool_manager()
        self.chat_memory = get_chat_memory()
        
        # Conversation state
        self.messages: List[ChatMessage] = []
        self.available_tools: List[ToolDefinition] = []
        self.max_tool_iterations = 10
    
    def set_available_tools(self, tools: List[ToolDefinition]):
        """Set the tools available for this conversation"""
        self.available_tools = tools
    
    async def start_conversation(
        self, 
        user_message: str,
        conversation_history: Optional[List[ChatMessage]] = None
    ) -> AsyncIterator[ConversationStep]:
        """
        Start a new conversation with tool calling support
        
        Args:
            user_message: User's input message
            conversation_history: Previous conversation messages
            
        Yields:
            ConversationStep objects representing each step in the conversation
        """
        
        # Initialize conversation with history + new message
        self.messages = conversation_history or []
        self.messages.append(ChatMessage(
            role="user",
            content=user_message
        ))
        
        # Start the tool calling loop
        iteration = 0
        while iteration < self.max_tool_iterations:
            iteration += 1
            
            # Generate AI response
            yield ConversationStep(state=ConversationState.GENERATING)
            
            try:
                print("Generating AI response...", self.messages, self.available_tools)
                response = await self.provider.generate(
                    messages=self.messages,
                    tools=self.available_tools
                )
                print("Generated AI response:", response)
                
                # Add AI response to conversation
                ai_message = ChatMessage(
                    role="assistant",
                    content=response.content,
                    tool_calls=self._format_tool_calls_for_message(response.tool_calls) if response.tool_calls else None
                )
                self.messages.append(ai_message)
                
                # If no tool calls, conversation is complete
                if not response.tool_calls:
                    yield ConversationStep(
                        state=ConversationState.COMPLETED,
                        content=response.content
                    )
                    
                    # Save to memory
                    await self._save_to_memory(user_message, response.content)
                    return
                
                # AI wants to use tools - ask for user approval
                yield ConversationStep(
                    state=ConversationState.TOOL_APPROVAL,
                    content=response.content,
                    tool_calls=response.tool_calls
                )
                
                # Wait for user approval (this will be handled by the endpoint)
                return
                
            except Exception as e:
                yield ConversationStep(
                    state=ConversationState.COMPLETED,
                    error=f"AI generation error: {str(e)}"
                )
                return
    
    async def handle_tool_approval(
        self, 
        approved_tools: List[str],  # List of approved tool call IDs
        denied_tools: List[str]     # List of denied tool call IDs
    ) -> AsyncIterator[ConversationStep]:
        """
        Handle user's tool approval decision and continue conversation
        
        Args:
            approved_tools: List of tool call IDs that user approved
            denied_tools: List of tool call IDs that user denied
            
        Yields:
            ConversationStep objects for tool execution and continued conversation
        """
        
        # Get the last assistant message with tool calls
        print(f"DEBUG: handle_tool_approval called with {len(approved_tools)} approved, {len(denied_tools)} denied")
        print(f"DEBUG: Messages in conversation: {len(self.messages)}")
        
        if not self.messages:
            yield ConversationStep(
                state=ConversationState.COMPLETED,
                error="No messages in conversation history"
            )
            return
            
        last_message = self.messages[-1]
        print(f"DEBUG: Last message role: {last_message.role}, has tool_calls: {bool(last_message.tool_calls)}")
        
        if not last_message.tool_calls:
            yield ConversationStep(
                state=ConversationState.COMPLETED,
                error="No tool calls found to process"
            )
            return
        
        # Execute approved tools
        yield ConversationStep(state=ConversationState.TOOL_EXECUTING)
        
        tool_results = []
        
        for tool_call_data in last_message.tool_calls:
            tool_call_id = tool_call_data["id"]
            tool_name = tool_call_data["name"]
            tool_args = tool_call_data["arguments"]
            
            if tool_call_id in approved_tools:
                # Execute the tool
                try:
                    result = await self.tool_manager.execute_tool(
                        tool_name=tool_name,
                        project_path=self.project_path,
                        **tool_args
                    )
                    
                    tool_results.append({
                        "tool_call_id": tool_call_id,
                        "name": tool_name,
                        "content": result.content if result.success else f"Error: {result.error}",
                        "success": result.success
                    })
                    
                except Exception as e:
                    tool_results.append({
                        "tool_call_id": tool_call_id,
                        "name": tool_name,
                        "content": f"Tool execution error: {str(e)}",
                        "success": False
                    })
            
            elif tool_call_id in denied_tools:
                # User denied this tool
                tool_results.append({
                    "tool_call_id": tool_call_id,
                    "name": tool_name,
                    "content": "User denied tool execution",
                    "success": False
                })
        
        # Add tool results to conversation
        for result in tool_results:
            tool_message = ChatMessage(
                role="tool",
                content=result["content"],
                tool_call_id=result["name"]  # Gemini uses tool name as ID
            )
            self.messages.append(tool_message)
        
        # Continue conversation with tool results
        yield ConversationStep(
            state=ConversationState.GENERATING,
            tool_results=tool_results
        )
        
        # Generate AI's next response
        try:
            response = await self.provider.generate(
                messages=self.messages,
                tools=self.available_tools
            )
            
            # Add AI response to conversation
            ai_message = ChatMessage(
                role="assistant",
                content=response.content,
                tool_calls=self._format_tool_calls_for_message(response.tool_calls) if response.tool_calls else None
            )
            self.messages.append(ai_message)
            
            # Check if AI wants to use more tools
            if response.tool_calls:
                yield ConversationStep(
                    state=ConversationState.TOOL_APPROVAL,
                    content=response.content,
                    tool_calls=response.tool_calls
                )
            else:
                # Conversation complete
                yield ConversationStep(
                    state=ConversationState.COMPLETED,
                    content=response.content
                )
                
                # Save final conversation to memory
                await self._save_final_conversation()
                
        except Exception as e:
            yield ConversationStep(
                state=ConversationState.COMPLETED,
                error=f"AI generation error: {str(e)}"
            )
    
    def _format_tool_calls_for_message(self, tool_calls: List[ToolCall]) -> List[Dict[str, Any]]:
        """Format tool calls for ChatMessage storage"""
        return [
            {
                "id": tc.id,
                "name": tc.name,
                "arguments": tc.arguments
            }
            for tc in tool_calls
        ]
    
    async def _save_to_memory(self, user_message: str, ai_response: str):
        """Save simple conversation to memory"""
        try:
            self.chat_memory.save_message(
                project_id=self.project_id,
                user_message=user_message,
                ai_response=ai_response
            )
        except Exception as e:
            print(f"Failed to save to memory: {e}")
    
    async def _save_final_conversation(self):
        """Save complete conversation with tool calls to memory"""
        try:
            # Extract user message and final AI response
            user_msg = None
            final_response = None
            
            for msg in self.messages:
                if msg.role == "user" and not user_msg:
                    user_msg = msg.content
                elif msg.role == "assistant":
                    final_response = msg.content
            
            if user_msg and final_response:
                self.chat_memory.save_message(
                    project_id=self.project_id,
                    user_message=user_msg,
                    ai_response=final_response
                )
        except Exception as e:
            print(f"Failed to save final conversation: {e}")