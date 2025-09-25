import React, { useState, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { ToolCall } from '../types';

// Import the diff generator from FileOperationDisplay
const generateSimpleDiff = (oldContent: string, newContent: string) => {
  const oldLines = oldContent.split('\n');
  const newLines = newContent.split('\n');
  
  const maxLines = Math.max(oldLines.length, newLines.length);
  const diffLines = [];
  
  for (let i = 0; i < maxLines; i++) {
    const oldLine = oldLines[i];
    const newLine = newLines[i];
    
    if (oldLine === undefined && newLine !== undefined) {
      diffLines.push({ type: 'add', content: newLine, lineNum: i + 1 });
    } else if (oldLine !== undefined && newLine === undefined) {
      diffLines.push({ type: 'remove', content: oldLine, lineNum: i + 1 });
    } else if (oldLine !== newLine) {
      if (oldLine !== undefined) {
        diffLines.push({ type: 'remove', content: oldLine, lineNum: i + 1 });
      }
      if (newLine !== undefined) {
        diffLines.push({ type: 'add', content: newLine, lineNum: i + 1 });
      }
    } else {
      diffLines.push({ type: 'context', content: oldLine, lineNum: i + 1 });
    }
  }
  
  return diffLines;
};

export function ToolApproval() {
  const { state, dispatch, api } = useApp();
  const [approvals, setApprovals] = useState<Record<string, boolean | null>>({});
  
  // Initialize approvals when toolCalls change
  useEffect(() => {
    if (state.pendingToolCalls?.toolCalls) {
      setApprovals(Object.fromEntries(state.pendingToolCalls.toolCalls.map(tc => [tc.id, null])));
    }
  }, [state.pendingToolCalls?.toolCalls]);
  
  if (!state.pendingToolCalls) {
    return null;
  }

  const { content, toolCalls } = state.pendingToolCalls;

  const handleToggleApproval = (toolId: string) => {
    const currentApproval = approvals[toolId];
    const newApproval = currentApproval === true ? false : (currentApproval === false ? null : true);
    setApprovals(prev => ({ ...prev, [toolId]: newApproval }));
  };

  const handleApproveAll = () => {
    const newApprovals = Object.fromEntries(toolCalls.map(tc => [tc.id, true]));
    setApprovals(newApprovals);
  };

  const handleDenyAll = () => {
    const newApprovals = Object.fromEntries(toolCalls.map(tc => [tc.id, false]));
    setApprovals(newApprovals);
  };

  const handleClearAll = () => {
    const newApprovals = Object.fromEntries(toolCalls.map(tc => [tc.id, null]));
    setApprovals(newApprovals);
  };

  const handleExecute = async () => {
    if (!state.currentProject || !state.pendingToolCalls?.sessionId) return;
    
    const approved = Object.entries(approvals)
      .filter(([_, status]) => status === true)
      .map(([id, _]) => id);
    const denied = Object.entries(approvals)
      .filter(([_, status]) => status === false)
      .map(([id, _]) => id);
    
    if (approved.length > 0 || denied.length > 0) {
      // Extract session_id before clearing pending tool calls
      const sessionId = state.pendingToolCalls.sessionId;
      
      // Clear the pending tool calls
      dispatch({ type: 'SET_PENDING_TOOL_CALLS', payload: null });
      dispatch({ type: 'SET_CONVERSATION_STATE', payload: 'tool_executing' });
      
      try {
        console.log('Tool approval using session_id:', sessionId);
        const stream = await api.approveTools({
          approved_tools: approved,
          denied_tools: denied,
          project_id: state.currentProject.id,
          session_id: sessionId,
        });

        await api.parseStreamingResponse(
          stream,
          (data) => {
            // Handle tool execution results similar to main conversation
            // Update session_id if provided
            if (data.session_id && data.session_id !== state.sessionId) {
              dispatch({ type: 'SET_SESSION_ID', payload: data.session_id });
            }
            
            switch (data.state) {
              case 'tool_executing':
                dispatch({ type: 'SET_CONVERSATION_STATE', payload: 'tool_executing' });
                break;

              case 'generating':
                dispatch({ type: 'SET_CONVERSATION_STATE', payload: 'generating' });
                // Handle incremental content during generation after tool execution
                if (data.content) {
                  const messages = [...state.messages];
                  const lastAssistantIndex = messages.map(m => m.role).lastIndexOf('assistant');
                  if (lastAssistantIndex !== -1) {
                    // Append streaming content to existing message
                    messages[lastAssistantIndex] = {
                      ...messages[lastAssistantIndex],
                      content: messages[lastAssistantIndex].content + data.content,
                    };
                    dispatch({ type: 'SET_MESSAGES', payload: messages });
                  }
                }
                break;

              case 'tool_approval':
                // More tools requested - update the last assistant message
                if (data.content) {
                  // Find and update the last assistant message
                  const messages = [...state.messages];
                  const lastAssistantIndex = messages.map(m => m.role).lastIndexOf('assistant');
                  if (lastAssistantIndex !== -1) {
                    // Append new content to existing message
                    messages[lastAssistantIndex] = {
                      ...messages[lastAssistantIndex],
                      content: messages[lastAssistantIndex].content + '\n\n' + data.content,
                      tool_calls: data.tool_calls,
                    };
                    dispatch({ type: 'SET_MESSAGES', payload: messages });
                  }
                }
                dispatch({ type: 'SET_PENDING_TOOL_CALLS', payload: { content: data.content || '', toolCalls: data.tool_calls || [], sessionId: data.session_id || '' } });
                break;

              case 'completed':
                if (data.content) {
                  // Find and update the last assistant message with final content
                  const messages = [...state.messages];
                  const lastAssistantIndex = messages.map(m => m.role).lastIndexOf('assistant');
                  if (lastAssistantIndex !== -1) {
                    // Append final content to existing message
                    messages[lastAssistantIndex] = {
                      ...messages[lastAssistantIndex],
                      content: messages[lastAssistantIndex].content + '\n\n' + data.content,
                      tool_calls: undefined, // Clear tool calls when completed
                    };
                    dispatch({ type: 'SET_MESSAGES', payload: messages });
                  }
                }
                dispatch({ type: 'SET_CONVERSATION_STATE', payload: 'idle' });
                dispatch({ type: 'SET_SESSION_ID', payload: null }); // Clear session when complete
                break;
            }
          },
          (error) => {
            dispatch({ type: 'SET_ERROR', payload: 'Tool approval failed: ' + error.message });
            dispatch({ type: 'SET_CONVERSATION_STATE', payload: 'idle' });
          },
          () => {
            dispatch({ type: 'SET_CONVERSATION_STATE', payload: 'idle' });
          }
        );
      } catch (error) {
        dispatch({ type: 'SET_ERROR', payload: 'Tool approval failed: ' + (error as Error).message });
        dispatch({ type: 'SET_CONVERSATION_STATE', payload: 'idle' });
      }
    }
  };

  const handleCancel = () => {
    dispatch({ type: 'SET_PENDING_TOOL_CALLS', payload: null });
    dispatch({ type: 'SET_CONVERSATION_STATE', payload: 'idle' });
  };

  const getStatusIcon = (status: boolean | null): string => {
    if (status === true) return '✅';
    if (status === false) return '❌';
    return '⏳';
  };

  const getStatusText = (status: boolean | null): string => {
    if (status === true) return 'Approved';
    if (status === false) return 'Denied';
    return 'Pending';
  };

  const hasDecisions = Object.values(approvals).some(status => status !== null);
  const approvedCount = Object.values(approvals).filter(s => s === true).length;
  const deniedCount = Object.values(approvals).filter(s => s === false).length;

  return (
    <div className="tool-approval-overlay">
      <div className="tool-approval-modal">
        {/* AI Response Content */}
        {content && (
          <div className="tool-approval-content">
            <div className="tool-approval-header">
              <h3>🤖 AI Assistant Response</h3>
            </div>
            <div className="tool-approval-response">
              <pre>{content}</pre>
            </div>
          </div>
        )}

        {/* Tool Approval Section */}
        <div className="tool-approval-section">
          <div className="tool-approval-header">
            <h3>⚠️ Tool Approval Required</h3>
            <p>The AI wants to execute the following tools. Review and approve/deny each one:</p>
          </div>

          {/* Tool List */}
          <div className="tool-approval-list">
            {toolCalls.map((tool) => {
              const approval = approvals[tool.id];
              
              return (
                <div key={tool.id} className="tool-approval-item">
                  <div className="tool-approval-item-header">
                    <div className="tool-approval-status">
                      <span className="tool-status-icon">{getStatusIcon(approval)}</span>
                      <span className={`tool-status-text ${approval === true ? 'approved' : approval === false ? 'denied' : 'pending'}`}>
                        {getStatusText(approval)}
                      </span>
                    </div>
                    <button 
                      className="tool-name-button"
                      onClick={() => handleToggleApproval(tool.id)}
                    >
                      {tool.name}
                    </button>
                  </div>
                  
                  <div className="tool-approval-details">
                    {tool.name === 'run_command' ? (
                      <div>
                        <strong>Command:</strong>
                        <code className="tool-command">{tool.arguments.command}</code>
                        {tool.arguments.timeout && (
                          <div className="tool-timeout">
                            <strong>Timeout:</strong> {tool.arguments.timeout}s
                          </div>
                        )}
                      </div>
                    ) : tool.name === 'read_file' ? (
                      <div className="file-tool-preview">
                        <div className="file-tool-action">
                          <span className="file-tool-icon">📖</span>
                          <span>Read file: <code>{tool.arguments.file_path}</code></span>
                        </div>
                        {tool.arguments.start_line && tool.arguments.end_line ? (
                          <div className="file-tool-range">
                            Lines {tool.arguments.start_line} - {tool.arguments.end_line}
                          </div>
                        ) : tool.arguments.start_line ? (
                          <div className="file-tool-range">
                            From line {tool.arguments.start_line}
                          </div>
                        ) : tool.arguments.end_line ? (
                          <div className="file-tool-range">
                            Up to line {tool.arguments.end_line}
                          </div>
                        ) : (
                          <div className="file-tool-range">Entire file</div>
                        )}
                      </div>
                    ) : tool.name === 'write_file' ? (
                      <div className="file-tool-preview">
                        <div className="file-tool-action">
                          <span className="file-tool-icon">📝</span>
                          <span>Write to: <code>{tool.arguments.file_path}</code></span>
                        </div>
                        <div className="file-tool-content-preview">
                          <div className="file-content-summary">
                            Content: {tool.arguments.content ? 
                              `${tool.arguments.content.split('\n').length} lines, ${tool.arguments.content.length} characters` : 
                              'Empty'
                            }
                          </div>
                          {tool.arguments.content && tool.arguments.content.length > 200 && (
                            <details className="file-content-expandable">
                              <summary>Preview content</summary>
                              <pre className="file-content-preview">{tool.arguments.content.substring(0, 500)}{tool.arguments.content.length > 500 ? '...' : ''}</pre>
                            </details>
                          )}
                          {tool.arguments.content && tool.arguments.content.length <= 200 && (
                            <pre className="file-content-preview">{tool.arguments.content}</pre>
                          )}
                        </div>
                      </div>
                    ) : tool.name === 'edit_file' ? (
                      // Debug: log tool details
                      (() => { console.log('Edit file tool detected:', tool.name, tool.arguments); return true; })() && (
                      <div className="file-tool-preview">
                        <div className="file-tool-action">
                          <span className="file-tool-icon">🔧</span>
                          <span>Edit file: <code>{tool.arguments.file_path}</code></span>
                        </div>
                        <div className="edit-tool-details">
                          {tool.arguments.old_text && tool.arguments.new_text ? (
                            <div className="tool-approval-diff">
                              <div className="diff-header-small">
                                <strong>Changes to be made:</strong>
                              </div>
                              <div className="github-style-diff">
                                {generateSimpleDiff(tool.arguments.old_text, tool.arguments.new_text).map((line, index) => (
                                  <div key={index} className={`diff-line ${line.type}`}>
                                    <span className="line-number">{line.lineNum}</span>
                                    <span className="line-prefix">
                                      {line.type === 'add' ? '+' : line.type === 'remove' ? '-' : ' '}
                                    </span>
                                    <span className="line-content">{line.content}</span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          ) : (
                            <div className="edit-search-replace">
                              <div className="edit-old-text">
                                <strong>Find:</strong>
                                <pre className="edit-text-block old">{tool.arguments.old_text}</pre>
                              </div>
                              <div className="edit-new-text">
                                <strong>Replace with:</strong>
                                <pre className="edit-text-block new">{tool.arguments.new_text}</pre>
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                      )
                    ) : (
                      <div>
                        <strong>Tool: {tool.name}</strong>
                        {tool.name === 'edit_file' ? (
                          <div style={{color: 'red'}}>EDIT FILE SHOULD BE CAUGHT ABOVE!</div>
                        ) : null}
                        <strong>Arguments:</strong>
                        <pre className="tool-arguments">
                          {JSON.stringify(tool.arguments, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Controls */}
          <div className="tool-approval-controls">
            <div className="tool-approval-buttons">
              <button className="btn btn-success" onClick={handleApproveAll}>
                Approve All
              </button>
              <button className="btn btn-danger" onClick={handleDenyAll}>
                Deny All
              </button>
              <button className="btn" onClick={handleClearAll}>
                Clear All
              </button>
            </div>
            
            <div className="tool-approval-actions">
              <button 
                className="btn btn-primary" 
                onClick={handleExecute}
                disabled={!hasDecisions}
              >
                Execute {hasDecisions ? `(${approvedCount} approved, ${deniedCount} denied)` : ''}
              </button>
              <button className="btn" onClick={handleCancel}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}