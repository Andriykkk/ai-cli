import React from 'react';
import { Box, Text } from 'ink';

interface HeaderProps {
  title: string;
  subtitle?: string;
}

export const Header: React.FC<HeaderProps> = ({ title, subtitle }) => {
  return (
    <Box flexDirection="column" paddingX={1} paddingTop={1}>
      <Box justifyContent="center">
        <Text backgroundColor="blue" color="white" bold>
          {` ${title} `}
        </Text>
      </Box>
      {subtitle && (
        <Box justifyContent="center" paddingTop={0}>
          <Text dimColor>{subtitle}</Text>
        </Box>
      )}
      <Box paddingTop={1}>
        <Text>{'─'.repeat(process.stdout.columns || 80)}</Text>
      </Box>
    </Box>
  );
};