import React, { useState } from 'react';
import { Box, Text, useInput } from 'ink';
import type { ToolCall } from '../tool-types';

interface ToolApprovalComponentProps {
  content?: string;
  toolCalls: ToolCall[];
  onApproval: (approvedTools: string[], deniedTools: string[]) => void;
  onCancel: () => void;
}

export const ToolApprovalComponent: React.FC<ToolApprovalComponentProps> = ({
  content,
  toolCalls,
  onApproval,
  onCancel
}) => {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [approvals, setApprovals] = useState<Record<string, boolean | null>>(
    Object.fromEntries(toolCalls.map(tc => [tc.id, null]))
  );

  useInput((input, key) => {
    if (key.escape) {
      onCancel();
      return;
    }

    if (key.upArrow) {
      setSelectedIndex(Math.max(0, selectedIndex - 1));
    } else if (key.downArrow) {
      setSelectedIndex(Math.min(toolCalls.length - 1, selectedIndex + 1));
    } else if (key.return || input === ' ') {
      const toolId = toolCalls[selectedIndex]?.id;
      if (toolId) {
        const currentApproval = approvals[toolId];
        const newApproval = currentApproval === true ? false : (currentApproval === false ? null : true);
        setApprovals(prev => ({ ...prev, [toolId]: newApproval }));
      }
    } else if (input === 'a' || input === 'A') {
      // Approve all
      const newApprovals = Object.fromEntries(toolCalls.map(tc => [tc.id, true]));
      setApprovals(newApprovals);
    } else if (input === 'd' || input === 'D') {
      // Deny all
      const newApprovals = Object.fromEntries(toolCalls.map(tc => [tc.id, false]));
      setApprovals(newApprovals);
    } else if (input === 'c' || input === 'C') {
      // Clear all
      const newApprovals = Object.fromEntries(toolCalls.map(tc => [tc.id, null]));
      setApprovals(newApprovals);
    } else if (input === 'e' || input === 'E') {
      // Execute approved tools
      const approved = Object.entries(approvals)
        .filter(([_, status]) => status === true)
        .map(([id, _]) => id);
      const denied = Object.entries(approvals)
        .filter(([_, status]) => status === false)
        .map(([id, _]) => id);
      
      if (approved.length > 0 || denied.length > 0) {
        onApproval(approved, denied);
      }
    }
  });

  const formatArguments = (args: Record<string, any>): string => {
    return Object.entries(args)
      .map(([key, value]) => `${key}: ${JSON.stringify(value)}`)
      .join(', ');
  };

  const getStatusIcon = (status: boolean | null): string => {
    if (status === true) return '✅';
    if (status === false) return '❌';
    return '⏳';
  };

  const getStatusColor = (status: boolean | null): string => {
    if (status === true) return 'green';
    if (status === false) return 'red';
    return 'yellow';
  };

  const hasDecisions = Object.values(approvals).some(status => status !== null);

  return (
    <Box flexDirection="column" paddingX={1} paddingY={1}>
      {/* AI Generated Content */}
      {content && (
        <Box flexDirection="column" paddingBottom={1}>
          <Text backgroundColor="cyan" color="black" bold> AI Assistant </Text>
          <Box paddingLeft={0} paddingTop={1}>
            <Text>{content}</Text>
          </Box>
        </Box>
      )}

      {/* Tool Approval Section */}
      <Box flexDirection="column" paddingTop={1}>
        <Box paddingBottom={1}>
          <Text backgroundColor="yellow" color="black" bold> Tool Approval Required </Text>
        </Box>

        <Text dimColor>The AI wants to execute the following tools. Review and approve/deny each one:</Text>

        {/* Tool List */}
        <Box flexDirection="column" paddingTop={1}>
          {toolCalls.map((tool, index) => {
            const isSelected = index === selectedIndex;
            const approval = approvals[tool.id];
            
            return (
              <Box key={tool.id} flexDirection="column" paddingBottom={1}>
                <Box>
                  <Text backgroundColor={isSelected ? 'blue' : undefined} color={isSelected ? 'white' : undefined}>
                    {isSelected ? '►' : ' '} 
                  </Text>
                  <Text color={getStatusColor(approval)}> {getStatusIcon(approval)} </Text>
                  <Text bold color="cyan">{tool.name}</Text>
                </Box>
                
                <Box paddingLeft={4}>
                  <Text dimColor>Arguments: </Text>
                  <Text>{formatArguments(tool.arguments)}</Text>
                </Box>
              </Box>
            );
          })}
        </Box>

        {/* Controls */}
        <Box flexDirection="column" paddingTop={1} borderStyle="round" borderColor="gray">
          <Box paddingX={1}>
            <Text bold>Controls:</Text>
          </Box>
          <Box paddingX={1}>
            <Text dimColor>↑↓ Navigate • Space/Enter Toggle approval • A Approve all • D Deny all • C Clear all</Text>
          </Box>
          <Box paddingX={1}>
            <Text dimColor>E Execute {hasDecisions ? `(${Object.values(approvals).filter(s => s === true).length} approved, ${Object.values(approvals).filter(s => s === false).length} denied)` : ''} • Esc Cancel</Text>
          </Box>
        </Box>
      </Box>
    </Box>
  );
};