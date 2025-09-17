import React from 'react';
import { Box, Text } from 'ink';

interface ToolResult {
  tool_call_id: string;
  name: string;
  content: string;
  success: boolean;
}

interface ToolResultDisplayProps {
  toolResults: ToolResult[];
  isVisible: boolean;
}

export const ToolResultDisplay: React.FC<ToolResultDisplayProps> = ({
  toolResults,
  isVisible
}) => {
  if (!isVisible || toolResults.length === 0) {
    return null;
  }

  const truncateContent = (content: string, maxLength: number = 500): string => {
    if (content.length <= maxLength) return content;
    return content.substring(0, maxLength) + '...';
  };

  return (
    <Box flexDirection="column" paddingX={1} paddingTop={1}>
      <Box paddingBottom={1}>
        <Text backgroundColor="magenta" color="white" bold> Tool Results </Text>
        <Text dimColor> (Ctrl+R to toggle)</Text>
      </Box>

      {toolResults.map((result, index) => (
        <Box key={`${result.tool_call_id}_${index}`} flexDirection="column" paddingBottom={1}>
          <Box>
            <Text color={result.success ? 'green' : 'red'}>
              {result.success ? '✅' : '❌'}
            </Text>
            <Text> </Text>
            <Text bold color="cyan">{result.name}</Text>
            <Text dimColor> → </Text>
            <Text color={result.success ? 'green' : 'red'}>
              {result.success ? 'Success' : 'Failed'}
            </Text>
          </Box>

          <Box paddingLeft={4} flexDirection="column">
            {result.content.includes('\n') ? (
              // Multi-line content
              <Box flexDirection="column" backgroundColor="gray" padding={1}>
                {truncateContent(result.content).split('\n').map((line, lineIndex) => (
                  <Text key={lineIndex}>{line}</Text>
                ))}
              </Box>
            ) : (
              // Single line content
              <Box backgroundColor="gray" paddingX={1}>
                <Text>{truncateContent(result.content)}</Text>
              </Box>
            )}
          </Box>
        </Box>
      ))}

      <Box paddingTop={1}>
        <Text dimColor>
          {toolResults.length} tool{toolResults.length !== 1 ? 's' : ''} executed • 
          {toolResults.filter(r => r.success).length} successful • 
          {toolResults.filter(r => !r.success).length} failed
        </Text>
      </Box>
    </Box>
  );
};