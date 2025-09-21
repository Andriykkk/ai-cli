import React, { useState, useEffect } from 'react';
import { ToolCall } from '../types';
import { useApp } from '../context/AppContext';

interface InlineToolApprovalProps {
  messageId: string;
  toolCalls: ToolCall[];
  sessionId: string;
  onApprovalComplete?: () => void;
}

export function InlineToolApproval({ messageId, toolCalls, sessionId, onApprovalComplete }: InlineToolApprovalProps) {
  const { state, dispatch, api } = useApp();
  const [approvals, setApprovals] = useState<Record<string, boolean | null>>({});
  const [isExecuting, setIsExecuting] = useState(false);

  // Initialize approvals when component mounts
  useEffect(() => {
    setApprovals(Object.fromEntries(toolCalls.map(tc => [tc.id, null])));
  }, [toolCalls]);

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

  const handleExecute = async () => {
    if (!state.currentProject || isExecuting) return;
    
    const approved = Object.entries(approvals)
      .filter(([_, status]) => status === true)
      .map(([id, _]) => id);
    const denied = Object.entries(approvals)
      .filter(([_, status]) => status === false)
      .map(([id, _]) => id);
    
    if (approved.length === 0 && denied.length === 0) return;

    setIsExecuting(true);
    dispatch({ type: 'SET_CONVERSATION_STATE', payload: 'tool_executing' });

    try {
      const stream = await api.approveTools({
        approved_tools: approved,
        denied_tools: denied,
        project_id: state.currentProject.id,
        session_id: sessionId,
      });

      await api.parseStreamingResponse(
        stream,
        (data) => {
          if (data.session_id && data.session_id !== state.sessionId) {
            dispatch({ type: 'SET_SESSION_ID', payload: data.session_id });
          }
          
          switch (data.state) {
            case 'tool_executing':
              dispatch({ type: 'SET_CONVERSATION_STATE', payload: 'tool_executing' });
              break;

            case 'generating':
              dispatch({ type: 'SET_CONVERSATION_STATE', payload: 'generating' });
              break;

            case 'tool_approval':
              // More tools requested - add new message with approval needed
              if (data.content) {
                const newMessage = {
                  id: Date.now().toString(),
                  role: 'assistant' as const,
                  content: data.content,
                  timestamp: new Date(),
                  tool_calls: data.tool_calls,
                  needsApproval: true,
                  sessionId: data.session_id
                };
                dispatch({ type: 'ADD_MESSAGE', payload: newMessage });
              }
              break;

            case 'completed':
              if (data.content) {
                const finalMessage = {
                  id: Date.now().toString(),
                  role: 'assistant' as const,
                  content: data.content,
                  timestamp: new Date(),
                };
                dispatch({ type: 'ADD_MESSAGE', payload: finalMessage });
              }
              dispatch({ type: 'SET_CONVERSATION_STATE', payload: 'idle' });
              dispatch({ type: 'SET_SESSION_ID', payload: null });
              break;
          }

          // Handle tool results
          if (data.tool_results) {
            // Update the current message to show tool results
            const messages = [...state.messages];
            const messageIndex = messages.findIndex(m => m.id === messageId);
            if (messageIndex !== -1) {
              // Convert tool results to the expected format
              const convertedResults = data.tool_results.map((result: any) => ({
                tool_call_id: result.tool_call_id,
                name: result.name,
                content: result.content,
                success: result.success,
                command: result.name === 'run_command' ? 
                  toolCalls.find(tc => tc.id === result.tool_call_id)?.arguments?.command : undefined
              }));
              
              messages[messageIndex] = {
                ...messages[messageIndex],
                tool_results: convertedResults,
                needsApproval: false
              };
              dispatch({ type: 'SET_MESSAGES', payload: messages });
            }
          }
        },
        (error) => {
          dispatch({ type: 'SET_ERROR', payload: 'Tool execution failed: ' + error.message });
          dispatch({ type: 'SET_CONVERSATION_STATE', payload: 'idle' });
          setIsExecuting(false);
        },
        () => {
          dispatch({ type: 'SET_CONVERSATION_STATE', payload: 'idle' });
          setIsExecuting(false);
          if (onApprovalComplete) onApprovalComplete();
        }
      );
    } catch (error) {
      dispatch({ type: 'SET_ERROR', payload: 'Tool execution failed: ' + (error as Error).message });
      dispatch({ type: 'SET_CONVERSATION_STATE', payload: 'idle' });
      setIsExecuting(false);
    }
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
    <div className="inline-tool-approval">
      <div className="tool-approval-header">
        <span className="tool-approval-icon">⚠️</span>
        <span className="tool-approval-title">Tool Approval Required</span>
      </div>
      
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
                  disabled={isExecuting}
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
                ) : (
                  <div>
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

      <div className="tool-approval-controls">
        <div className="tool-approval-buttons">
          <button 
            className="btn btn-sm btn-success" 
            onClick={handleApproveAll}
            disabled={isExecuting}
          >
            Approve All
          </button>
          <button 
            className="btn btn-sm btn-danger" 
            onClick={handleDenyAll}
            disabled={isExecuting}
          >
            Deny All
          </button>
        </div>
        
        <button 
          className="btn btn-sm btn-primary" 
          onClick={handleExecute}
          disabled={!hasDecisions || isExecuting}
        >
          {isExecuting ? 'Executing...' : `Execute ${hasDecisions ? `(${approvedCount} approved, ${deniedCount} denied)` : ''}`}
        </button>
      </div>
    </div>
  );
}