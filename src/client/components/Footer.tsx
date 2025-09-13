import React from 'react';
import { Box, Text } from 'ink';

interface FooterProps {
  shortcuts: string[];
}

export const Footer: React.FC<FooterProps> = ({ shortcuts }) => {
  const shortcutsText = shortcuts.join(' | ');
  
  return (
    <Box flexDirection="column" paddingX={1} paddingBottom={1}>
      <Box>
        <Text>{'─'.repeat(process.stdout.columns || 80)}</Text>
      </Box>
      <Box justifyContent="center" paddingTop={1}>
        <Text dimColor>{shortcutsText}</Text>
      </Box>
    </Box>
  );
};