import React, { useState } from 'react';
import { ToolResult } from '../types';
import { FileOperationDisplay } from './FileOperationDisplay';

interface ToolResultsProps {
  toolResults: ToolResult[];
}

export function ToolResults({ toolResults }: ToolResultsProps) {
  const [expandedResults, setExpandedResults] = useState<Set<string>>(new Set());

  const toggleExpanded = (toolCallId: string) => {
    const newExpanded = new Set(expandedResults);
    if (newExpanded.has(toolCallId)) {
      newExpanded.delete(toolCallId);
    } else {
      newExpanded.add(toolCallId);
    }
    setExpandedResults(newExpanded);
  };

  return (
    <div className="tool-results">
      <div className="tool-results-header">
        <span className="tool-results-icon">🔧</span>
        <span className="tool-results-title">Tool Execution Results</span>
      </div>
      
      <div className="tool-results-list">
        {toolResults.map((result) => {
          const isExpanded = expandedResults.has(result.tool_call_id);
          const hasContent = result.content && result.content.trim().length > 0;
          const isFileOperation = result.name === 'read_file' || result.name === 'write_file' || result.name === 'edit_file';
          
          // Use enhanced display for file operations
          if (isFileOperation) {
            return (
              <div key={result.tool_call_id} className="tool-result-item file-operation">
                <FileOperationDisplay result={result} />
              </div>
            );
          }
          
          // Default display for other tools
          return (
            <div key={result.tool_call_id} className="tool-result-item">
              <div className="tool-result-header">
                <div className="tool-result-status">
                  <span className={`tool-result-icon ${result.success ? 'success' : 'error'}`}>
                    {result.success ? '✅' : '❌'}
                  </span>
                  <span className="tool-result-name">{result.name}</span>
                  {result.command && (
                    <code className="tool-result-command">{result.command}</code>
                  )}
                </div>
                
                {hasContent && (
                  <button 
                    className="tool-result-toggle"
                    onClick={() => toggleExpanded(result.tool_call_id)}
                  >
                    {isExpanded ? '▼' : '▶'} {isExpanded ? 'Hide' : 'Show'} Output
                  </button>
                )}
              </div>
              
              {hasContent && isExpanded && (
                <div className="tool-result-content">
                  <pre>{result.content}</pre>
                </div>
              )}
              
              {!hasContent && (
                <div className="tool-result-no-output">
                  <span className="tool-result-no-output-text">No output</span>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}