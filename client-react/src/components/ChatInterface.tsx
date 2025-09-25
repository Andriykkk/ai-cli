import React, { useState, useRef, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { Message } from '../types';
import { InlineToolApproval } from './InlineToolApproval';
import { ToolResults } from './ToolResults';

export function ChatInterface() {
  const { state, dispatch, api } = useApp();
  const [input, setInput] = useState('');
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const messagesRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const isVisible = state.currentScreen === 'chat';

  useEffect(() => {
    if (isVisible && state.currentProject) {
      loadChatHistory();
    }
  }, [isVisible, state.currentProject]);

  // Auto-scroll to bottom when messages change or when entering chat
  useEffect(() => {
    if (messagesRef.current && isVisible) {
      messagesRef.current.scrollTop = messagesRef.current.scrollHeight;
    }
  }, [state.messages, isVisible]);

  const loadChatHistory = async () => {
    if (!state.currentProject) return;

    try {
      dispatch({ type: 'SET_LOADING', payload: { loading: true, message: 'Loading chat history...' } });
      const { messages } = await api.getChatHistory(state.currentProject.id);

      // Convert server format to client format
      const convertedMessages: Message[] = [];
      messages.forEach((histMsg: any, histMsgIndex: number) => {
        try {
          // Try to parse the message as JSON structure
          const structuredData = JSON.parse(histMsg.message);

          // If it's an array of messages (new format), reconstruct them
          if (Array.isArray(structuredData)) {
            const toolResults: any[] = [];
            const thisConversationMessages: Message[] = [];

            // First pass: collect all messages and tool results for this conversation
            structuredData.forEach((msgData: any, index: number) => {
              if (msgData.role === 'tool') {
                toolResults.push(msgData);
                return;
              }

              const message: Message = {
                id: `${histMsg.id}-${msgData.role}-${index}`,
                role: msgData.role,
                content: msgData.content,
                timestamp: msgData.timestamp ? new Date(msgData.timestamp) : new Date(histMsg.timestamp),
              };

              // Add tool calls for assistant messages
              if (msgData.role === 'assistant' && msgData.tool_calls) {
                message.tool_calls = msgData.tool_calls;
                // Don't set needsApproval for historical messages
                message.needsApproval = false;
              }

              thisConversationMessages.push(message);
            });


            // Second pass: associate tool results with assistant messages by sequence
            if (toolResults.length > 0) {
              let toolResultIndex = 0;

              // Go through this conversation's messages in order
              thisConversationMessages.forEach(message => {
                if (message.role === 'assistant' && message.tool_calls && toolResultIndex < toolResults.length) {
                  // Get the next tool results for this message (same number as tool calls)
                  const numToolCalls = message.tool_calls.length;
                  const messageToolResults = toolResults.slice(toolResultIndex, toolResultIndex + numToolCalls);
                  toolResultIndex += numToolCalls;

                  if (messageToolResults.length > 0) {
                    message.tool_results = messageToolResults.map((toolResult, index) => {
                      const correspondingToolCall = message.tool_calls![index];
                      return {
                        tool_call_id: correspondingToolCall.id,
                        name: correspondingToolCall.name,
                        content: toolResult.content,
                        success: true, // Assume success if stored
                        command: correspondingToolCall.name === 'run_command' ?
                          correspondingToolCall.arguments?.command : undefined,
                        metadata: toolResult.metadata || {}
                      };
                    });
                  }
                }
              });
            }

            // Add this conversation's messages to the global array
            convertedMessages.push(...thisConversationMessages);
          } else {
            // Fallback: treat as plain user message (shouldn't happen with new format)
            convertedMessages.push({
              id: `${histMsg.id}-user`,
              role: 'user',
              content: histMsg.message,
              timestamp: new Date(histMsg.timestamp),
            });
            convertedMessages.push({
              id: `${histMsg.id}-assistant`,
              role: 'assistant',
              content: histMsg.response,
              timestamp: new Date(histMsg.timestamp),
            });
          }
        } catch (e) {
          // Fallback for old format (plain text)
          convertedMessages.push({
            id: `${histMsg.id}-user`,
            role: 'user',
            content: histMsg.message,
            timestamp: new Date(histMsg.timestamp),
          });
          convertedMessages.push({
            id: `${histMsg.id}-assistant`,
            role: 'assistant',
            content: histMsg.response,
            timestamp: new Date(histMsg.timestamp),
          });
        }
      });

      dispatch({ type: 'SET_MESSAGES', payload: convertedMessages });
    } catch (error) {
      dispatch({ type: 'SET_ERROR', payload: 'Failed to load chat history: ' + (error as Error).message });
      // Show welcome message if history fails
      const welcomeMessage: Message = {
        id: 'welcome',
        role: 'assistant',
        content: `Welcome to ${state.currentProject?.name}!\n\nI'm ready to help with your project.`,
        timestamp: new Date(),
      };
      dispatch({ type: 'SET_MESSAGES', payload: [welcomeMessage] });
    } finally {
      dispatch({ type: 'SET_LOADING', payload: { loading: false } });
    }
  };


  const handleSendMessage = async () => {
    if (!input.trim() || !state.currentProject) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
    };

    // Show user message immediately
    dispatch({ type: 'ADD_MESSAGE', payload: userMessage });
    dispatch({ type: 'SET_CONVERSATION_STATE', payload: 'generating' });

    // Add to command history
    const newHistory = [input.trim(), ...state.commandHistory.slice(0, 49)];
    dispatch({ type: 'SET_COMMAND_HISTORY', payload: newHistory });
    dispatch({ type: 'SET_HISTORY_INDEX', payload: -1 });

    const messageContent = input.trim();
    setInput('');

    try {
      abortControllerRef.current = new AbortController();
      const stream = await api.sendMessage({
        message: messageContent,
        project_id: state.currentProject.id,
      }, abortControllerRef.current.signal);

      let assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: '',
        timestamp: new Date(),
      };

      let assistantMessageAdded = false;

      await api.parseStreamingResponse(
        stream,
        (data) => {
          // Handle streaming data based on conversation state
          // Capture session_id when provided
          if (data.session_id) {
            console.log('Updating session_id:', data.session_id);
            dispatch({ type: 'SET_SESSION_ID', payload: data.session_id });
          }

          switch (data.state) {
            case 'generating':
              dispatch({ type: 'SET_CONVERSATION_STATE', payload: 'generating' });
              break;

            case 'tool_approval':
              // Always process tool calls when they exist, regardless of content
              if (data.tool_calls && data.session_id) {
                // Set content if provided
                if (data.content) {
                  assistantMessage.content = data.content;
                }

                assistantMessage.tool_calls = data.tool_calls;
                assistantMessage.needsApproval = true;
                assistantMessage.sessionId = data.session_id;

                if (assistantMessageAdded) {
                  dispatch({ type: 'SET_MESSAGES', payload: [...state.messages.slice(0, -1), assistantMessage] });
                } else {
                  dispatch({ type: 'ADD_MESSAGE', payload: assistantMessage });
                  assistantMessageAdded = true;
                }

                // Set pending tool calls for modal approval
                dispatch({
                  type: 'SET_PENDING_TOOL_CALLS',
                  payload: {
                    content: data.content || '',
                    toolCalls: data.tool_calls.map((tc: any) => ({
                      id: tc.id,
                      name: tc.name,
                      arguments: tc.arguments
                    })),
                    sessionId: data.session_id
                  }
                });
              }

              dispatch({ type: 'SET_CONVERSATION_STATE', payload: 'tool_approval' });
              break;

            case 'tool_executing':
              dispatch({ type: 'SET_CONVERSATION_STATE', payload: 'tool_executing' });
              break;

            case 'completed':
              if (data.error) {
                const errorMessage: Message = {
                  id: (Date.now() + 2).toString(),
                  role: 'assistant',
                  content: `Error: ${data.error}`,
                  timestamp: new Date(),
                };
                dispatch({ type: 'ADD_MESSAGE', payload: errorMessage });
              } else if (data.content) {
                if (assistantMessageAdded) {
                  // Update existing message
                  assistantMessage.content = data.content;
                  dispatch({ type: 'SET_MESSAGES', payload: [...state.messages.slice(0, -1), assistantMessage] });
                } else {
                  // Add new message
                  const finalMessage: Message = {
                    id: (Date.now() + 2).toString(),
                    role: 'assistant',
                    content: data.content,
                    timestamp: new Date(),
                  };
                  dispatch({ type: 'ADD_MESSAGE', payload: finalMessage });
                }
              }
              dispatch({ type: 'SET_CONVERSATION_STATE', payload: 'idle' });
              dispatch({ type: 'SET_SESSION_ID', payload: null }); // Clear session when complete
              break;
          }

          // Handle incremental content updates during generation
          if (data.content && data.state !== 'tool_approval' && data.state !== 'completed') {
            assistantMessage.content += data.content;
            if (assistantMessageAdded) {
              dispatch({ type: 'SET_MESSAGES', payload: [...state.messages.slice(0, -1), assistantMessage] });
            } else {
              dispatch({ type: 'ADD_MESSAGE', payload: assistantMessage });
              assistantMessageAdded = true;
            }
          }
        },
        (error) => {
          dispatch({ type: 'SET_ERROR', payload: 'Failed to send message: ' + error.message });
          dispatch({ type: 'SET_CONVERSATION_STATE', payload: 'idle' });
        },
        () => {
          dispatch({ type: 'SET_CONVERSATION_STATE', payload: 'idle' });
        }
      );
    } catch (error) {
      dispatch({ type: 'SET_ERROR', payload: 'Failed to send message: ' + (error as Error).message });
      dispatch({ type: 'SET_CONVERSATION_STATE', payload: 'idle' });
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    } else if (e.key === 'ArrowUp') {
      // Navigate history up
      if (state.historyIndex < state.commandHistory.length - 1) {
        const newIndex = state.historyIndex + 1;
        dispatch({ type: 'SET_HISTORY_INDEX', payload: newIndex });
        setInput(state.commandHistory[newIndex]);
      }
    } else if (e.key === 'ArrowDown') {
      // Navigate history down
      if (state.historyIndex > 0) {
        const newIndex = state.historyIndex - 1;
        dispatch({ type: 'SET_HISTORY_INDEX', payload: newIndex });
        setInput(state.commandHistory[newIndex]);
      } else if (state.historyIndex === 0) {
        dispatch({ type: 'SET_HISTORY_INDEX', payload: -1 });
        setInput('');
      }
    }
  };

  if (!isVisible) {
    return null;
  }

  return (
    <div className="screen" id="chat-interface">
      <div className="chat-container">
        <div className="messages" ref={messagesRef}>
          {state.messages.length === 0 ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
              <p>Welcome to your AI assistant!</p>
              <p>Type a message below to start chatting.</p>
            </div>
          ) : (
            state.messages.map(message => (
              <div key={message.id} className={`message ${message.role}`}>
                <div className="message-content">{message.content}</div>
                {message.thinking && (
                  <div className="message-thinking">
                    <details>
                      <summary>Thinking...</summary>
                      <pre>{message.thinking}</pre>
                    </details>
                  </div>
                )}
                {message.needsApproval && message.tool_calls && message.sessionId && (
                  <InlineToolApproval
                    messageId={message.id}
                    toolCalls={message.tool_calls}
                    sessionId={message.sessionId}
                  />
                )}
                {message.tool_results && (
                  <ToolResults toolResults={message.tool_results} />
                )}
              </div>
            ))
          )}

          {/* Loading indicator when model is responding */}
          {(state.conversationState === 'generating' || state.conversationState === 'tool_executing') && (
            <div className="message assistant loading">
              <div className="message-content">
                <div className="loading-dots">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
                <span className="loading-text">
                  {state.conversationState === 'generating' ? 'AI is thinking...' : 'Executing tools...'}
                </span>
              </div>
            </div>
          )}
        </div>

        <div className="input-container">
          <div className="input-wrapper">
            <div className="input-prompt"></div>
            <textarea
              className="input-field"
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Type your message..."
              rows={1}
            />
            <button
              className="send-button"
              onClick={handleSendMessage}
              disabled={!input.trim() || !state.currentProject || state.conversationState !== 'idle'}
            >
              Send
            </button>
          </div>
          <div className="input-status">
            Type your message and press Enter
          </div>
        </div>
      </div>
    </div>
  );
}