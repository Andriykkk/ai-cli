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
                # Build optimized context to avoid memory/token limits
                provider_messages = self._build_provider_context()
                
                response = await self.provider.generate(
                    messages=provider_messages,
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
                    
                    # Save to memory using the same method as tool conversations
                    await self._save_final_conversation()
                    return
                
                # AI wants to use tools - ask for user approval
                print(f"DEBUG: About to yield TOOL_APPROVAL with {len(response.tool_calls)} tool calls")
                print(f"DEBUG: Tool calls: {[{'id': tc.id, 'name': tc.name} for tc in response.tool_calls]}")
                
                yield ConversationStep(
                    state=ConversationState.TOOL_APPROVAL,
                    content=response.content,
                    tool_calls=response.tool_calls
                )
                
                print("DEBUG: Successfully yielded TOOL_APPROVAL step")
                # Wait for user approval (this will be handled by the endpoint)
                return
                
            except Exception as e:
                yield ConversationStep(
                    state=ConversationState.COMPLETED,
                    error=f"AI generation error: {str(e)}"
                )
                return
    
    async def continue_conversation_after_tools(
        self, 
        approved_tools: List[str],  # List of approved tool call IDs
        denied_tools: List[str]     # List of denied tool call IDs
    ) -> AsyncIterator[ConversationStep]:
        """
        Continue conversation after tool approval - this now supports multi-step tool calling
        
        Args:
            approved_tools: List of tool call IDs that user approved
            denied_tools: List of tool call IDs that user denied
            
        Yields:
            ConversationStep objects for tool execution and continued conversation
        """
        
        # Get the last assistant message with tool calls
        
        if not self.messages:
            yield ConversationStep(
                state=ConversationState.COMPLETED,
                error="No messages in conversation history"
            )
            return
            
        last_message = self.messages[-1]
        
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
        
        # Continue the conversation loop after tool execution
        yield ConversationStep(
            state=ConversationState.GENERATING,
            tool_results=tool_results
        )
        
        # Start a continuous loop for multi-step conversations
        iteration = 0
        while iteration < self.max_tool_iterations:
            iteration += 1
            
            try:
                # Generate AI's next response
                provider_messages = self._build_provider_context()
                response = await self.provider.generate(
                    messages=provider_messages,
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
                    # Stop here and wait for the next tool approval - the frontend will call this method again
                    return
                else:
                    # No more tool calls - check if this is truly the end or if we need another iteration
                    
                    # Only do additional generation for providers that need it (like echo_test)
                    if self.provider.provider_name == "echo_test":
                        # For providers like echo_test that require multiple generate() calls to complete multi-step tasks
                        yield ConversationStep(
                            state=ConversationState.GENERATING,
                            content=response.content
                        )
                        
                        # Try one more generation to see if the provider wants to continue
                        provider_messages = self._build_provider_context()
                        next_response = await self.provider.generate(
                            messages=provider_messages,
                            tools=self.available_tools
                        )
                        
                        if next_response.tool_calls:
                            # Provider wants to continue with more tools
                            next_ai_message = ChatMessage(
                                role="assistant",
                                content=next_response.content,
                                tool_calls=self._format_tool_calls_for_message(next_response.tool_calls)
                            )
                            self.messages.append(next_ai_message)
                            
                            yield ConversationStep(
                                state=ConversationState.TOOL_APPROVAL,
                                content=next_response.content,
                                tool_calls=next_response.tool_calls
                            )
                            return  # Wait for next tool approval
                        else:
                            # No more tools needed, conversation is complete
                            if next_response.content and next_response.content != response.content:
                                # If the next response has different content, update the conversation
                                final_ai_message = ChatMessage(
                                    role="assistant",
                                    content=next_response.content,
                                    tool_calls=None
                                )
                                self.messages.append(final_ai_message)
                                
                                yield ConversationStep(
                                    state=ConversationState.COMPLETED,
                                    content=next_response.content
                                )
                            else:
                                yield ConversationStep(
                                    state=ConversationState.COMPLETED,
                                    content=response.content
                                )
                            
                            # Save final conversation to memory
                            await self._save_final_conversation()
                            return
                    else:
                        # For other providers (like Gemini), conversation is complete after tool execution
                        yield ConversationStep(
                            state=ConversationState.COMPLETED,
                            content=response.content
                        )
                        
                        # Save final conversation to memory
                        await self._save_final_conversation()
                        return
                        
            except Exception as e:
                yield ConversationStep(
                    state=ConversationState.COMPLETED,
                    error=f"AI generation error: {str(e)}"
                )
                return
    
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
    
    def _build_provider_context(self, max_messages: int = 20) -> List[ChatMessage]:
        """
        Build optimized message context for provider to avoid memory/token limits
        
        Args:
            max_messages: Maximum number of recent messages to include
            
        Returns:
            List of recent messages suitable for provider
        """
        if len(self.messages) <= max_messages:
            return self.messages
        
        # Take the most recent messages to stay within limits
        recent_messages = self.messages[-max_messages:]
        
        # Always include the first user message if it's a tool command
        # to preserve context for multi-step operations
        if len(self.messages) > max_messages:
            first_message = self.messages[0]
            if first_message.role == "user":
                # Check if first message contains tool command patterns
                import re
                tool_pattern = r"call\s+(\d+)\s+tools?\s+(\d+)\s+times?"
                if re.search(tool_pattern, first_message.content.lower()):
                    # Include first message and remove oldest from recent to maintain count
                    recent_messages = [first_message] + recent_messages[1:]
        
        return recent_messages
    
    async def _save_final_conversation(self):
        """Save the structured conversation thread to memory"""
        try:
            # Find the last user message that started this conversation
            user_msg = None
            last_user_index = -1
            for i, msg in enumerate(self.messages):
                if msg.role == "user":
                    last_user_index = i
                    user_msg = msg.content
            
            if last_user_index == -1 or not user_msg:
                print("No user message found for saving")
                return
            
            # Build structured conversation data starting from the last user message
            conversation_messages = []
            
            # Add the user message
            from datetime import datetime
            conversation_messages.append({
                "role": "user",
                "content": user_msg,
                "timestamp": datetime.now().isoformat()
            })
            
            # Add all messages after the user message
            for i in range(last_user_index + 1, len(self.messages)):
                msg = self.messages[i]
                
                if msg.role == "assistant":
                    # Structure assistant message with tool calls and results
                    message_data = {
                        "role": "assistant",
                        "content": msg.content,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    # Add tool calls if present
                    if msg.tool_calls:
                        message_data["tool_calls"] = msg.tool_calls
                    
                    conversation_messages.append(message_data)
                    
                elif msg.role == "tool":
                    # Add tool results to the conversation
                    conversation_messages.append({
                        "role": "tool",
                        "content": msg.content,
                        "tool_call_id": msg.tool_call_id,
                        "timestamp": datetime.now().isoformat()
                    })
            
            if conversation_messages:
                # Save as JSON in the user_message field and a summary in ai_response
                import json
                structured_data = json.dumps(conversation_messages)
                
                # Create a readable summary for the response field
                summary_parts = []
                for msg_data in conversation_messages:
                    if msg_data["role"] == "assistant":
                        summary_parts.append(msg_data["content"])
                    elif msg_data["role"] == "tool":
                        tool_name = msg_data.get("tool_call_id", "unknown_tool")
                        summary_parts.append(f"[Tool: {tool_name}]\n{msg_data['content']}")
                
                summary = "\n\n".join(summary_parts) if summary_parts else "No response content"
                
                print(f"Saving structured conversation: user='{user_msg[:50]}...', {len(conversation_messages)} messages")
                self.chat_memory.save_message(
                    project_id=self.project_id,
                    user_message=structured_data,  # JSON structure in message field
                    ai_response=summary  # Human-readable summary in response field
                )
            else:
                print("No conversation messages found for saving")
        except Exception as e:
            print(f"Failed to save final conversation: {e}")