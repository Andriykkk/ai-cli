import React, { useState } from 'react';
import { ToolResult } from '../types';

interface FileOperationDisplayProps {
  result: ToolResult;
}

interface FileOperationMetadata {
  file_path?: string;
  action?: 'created' | 'overwritten';
  bytes_written?: number;
  lines_written?: number;
  old_size?: number;
  backup_created?: string;
  old_length?: number;
  new_length?: number;
  line_difference?: number;
  occurrences_replaced?: number;
  total_lines?: number;
  lines_read?: number;
  line_range?: {
    start: number;
    end: number;
  };
}

// File extension to language mapping for syntax highlighting classes
const getLanguageFromPath = (filePath: string): string => {
  const ext = filePath.split('.').pop()?.toLowerCase() || '';
  const languageMap: Record<string, string> = {
    'js': 'javascript',
    'jsx': 'javascript',
    'ts': 'typescript',
    'tsx': 'typescript',
    'py': 'python',
    'java': 'java',
    'cpp': 'cpp',
    'c': 'c',
    'h': 'c',
    'hpp': 'cpp',
    'css': 'css',
    'html': 'html',
    'xml': 'xml',
    'json': 'json',
    'yaml': 'yaml',
    'yml': 'yaml',
    'md': 'markdown',
    'sh': 'bash',
    'bash': 'bash',
    'sql': 'sql',
    'php': 'php',
    'rb': 'ruby',
    'go': 'go',
    'rs': 'rust',
    'kt': 'kotlin',
    'swift': 'swift',
  };
  return languageMap[ext] || 'text';
};

// Generate a simple diff display for edit operations
const generateSimpleDiff = (oldContent: string, newContent: string) => {
  const oldLines = oldContent.split('\n');
  const newLines = newContent.split('\n');
  
  // Simple line-based diff - in a real implementation you'd want a proper diff library
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

export function FileOperationDisplay({ result }: FileOperationDisplayProps) {
  const [showContent, setShowContent] = useState(false);
  
  // Parse metadata from result (assuming it's in metadata field or parseable from content)
  let metadata: FileOperationMetadata = {};
  try {
    // Check if metadata exists in the result
    if ((result as any).metadata) {
      metadata = (result as any).metadata;
    }
  } catch (e) {
    // Fallback - metadata might be embedded in content
  }

  const isFileOperation = result.name === 'read_file' || result.name === 'write_file' || result.name === 'edit_file';
  
  if (!isFileOperation) {
    // Fall back to default display for non-file operations
    return null;
  }

  const getOperationIcon = (toolName: string, success: boolean) => {
    if (!success) return '❌';
    
    switch (toolName) {
      case 'read_file': return '📖';
      case 'write_file': return metadata.action === 'created' ? '📝' : '✏️';
      case 'edit_file': return '🔧';
      default: return '📄';
    }
  };

  const getOperationTitle = (toolName: string, success: boolean) => {
    if (!success) return `Failed: ${toolName}`;
    
    switch (toolName) {
      case 'read_file': 
        return metadata.line_range 
          ? `Read ${metadata.file_path} (lines ${metadata.line_range.start}-${metadata.line_range.end})`
          : `Read ${metadata.file_path || 'file'}`;
      case 'write_file': 
        return `${metadata.action === 'created' ? 'Created' : 'Updated'} ${metadata.file_path || 'file'}`;
      case 'edit_file': 
        return `Updated ${metadata.file_path || 'file'}`;
      default: 
        return toolName;
    }
  };

  const getOperationSummary = (toolName: string) => {
    switch (toolName) {
      case 'read_file':
        if (metadata.lines_read !== undefined && metadata.total_lines !== undefined) {
          return `Read ${metadata.lines_read} of ${metadata.total_lines} lines`;
        }
        return `Read ${metadata.lines_read || 0} lines`;
        
      case 'write_file':
        const action = metadata.action === 'created' ? 'Created' : 'Updated';
        const size = metadata.bytes_written ? `${metadata.bytes_written} bytes` : '';
        const lines = metadata.lines_written ? `${metadata.lines_written} lines` : '';
        return `${action} ${metadata.file_path || 'file'} with ${[size, lines].filter(Boolean).join(', ')}`;
        
      case 'edit_file':
        const changes = [];
        if (metadata.line_difference !== undefined && metadata.line_difference !== 0) {
          const diff = metadata.line_difference;
          changes.push(`${diff > 0 ? '+' : ''}${diff} lines`);
        }
        if (metadata.old_length !== undefined && metadata.new_length !== undefined) {
          const charDiff = metadata.new_length - metadata.old_length;
          changes.push(`${charDiff > 0 ? '+' : ''}${charDiff} characters`);
        }
        return `Updated ${metadata.file_path || 'file'} with ${changes.join(' and ')}`;
        
      default:
        return '';
    }
  };

  const language = metadata.file_path ? getLanguageFromPath(metadata.file_path) : 'text';
  const hasContent = result.content && result.content.trim().length > 0;

  return (
    <div className="file-operation-result">
      <div className="file-operation-header">
        <div className="file-operation-status">
          <span className="file-operation-icon">
            {getOperationIcon(result.name, result.success)}
          </span>
          <div className="file-operation-info">
            <div className="file-operation-title">
              {getOperationTitle(result.name, result.success)}
            </div>
            {result.success && (
              <div className="file-operation-summary">
                {getOperationSummary(result.name)}
              </div>
            )}
          </div>
        </div>
        
        {hasContent && result.success && (
          <button 
            className="file-operation-toggle"
            onClick={() => setShowContent(!showContent)}
          >
            {showContent ? '▼' : '▶'} {showContent ? 'Hide' : 'Show'} Content
          </button>
        )}
      </div>
      
      {!result.success && (
        <div className="file-operation-error">
          <pre>{result.content}</pre>
        </div>
      )}
      
      {hasContent && showContent && result.success && (
        <div className="file-operation-content">
          {result.name === 'edit_file' && metadata.backup_created ? (
            <div className="file-operation-diff">
              <div className="diff-header">
                <span className="diff-file">● {metadata.file_path || 'file'}</span>
                <span className="diff-stats">
                  {metadata.occurrences_replaced || 0} occurrence(s) replaced
                  {(metadata.line_difference !== undefined && metadata.line_difference !== 0) && 
                    ` • ${metadata.line_difference > 0 ? '+' : ''}${metadata.line_difference} lines`}
                </span>
              </div>
              {/* For now, show the result content. In future, implement proper diff */}
              <pre className={`file-content language-${language}`}>{result.content}</pre>
            </div>
          ) : (
            <div className="file-content-display">
              <div className="file-content-header">
                <span className="file-content-path">{metadata.file_path || 'file'}</span>
                <span className="file-content-language">{language}</span>
              </div>
              <pre className={`file-content language-${language}`}>{result.content}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}