import React from 'react';
import { Box, Text } from 'ink';

interface ErrorDisplayProps {
  error: string;
  onRetry?: () => void;
  onExit?: () => void;
}

export const ErrorDisplay: React.FC<ErrorDisplayProps> = ({ error, onRetry, onExit }) => {
  return (
    <Box flexDirection="column" alignItems="center" justifyContent="center" padding={2}>
      <Box paddingBottom={1}>
        <Text backgroundColor="red" color="white" bold>
          {' ERROR '}
        </Text>
      </Box>
      
      <Box paddingBottom={2} textWrap="wrap">
        <Text color="red">{error}</Text>
      </Box>
      
      <Box flexDirection="column" alignItems="center">
        {onRetry && (
          <Text dimColor>Press 'r' to retry</Text>
        )}
        {onExit && (
          <Text dimColor>Press 'q' to exit</Text>
        )}
        <Text dimColor>Press Ctrl+C to exit</Text>
      </Box>
    </Box>
  );
};