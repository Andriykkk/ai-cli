import React from 'react';
import { Box, Text, useInput } from 'ink';
import { LoadingSpinner } from './LoadingSpinner';

interface ConfirmDialogProps {
  title: string;
  message: string;
  detail?: string;
  onConfirm: () => Promise<void> | void;
  onCancel: () => void;
  isLoading?: boolean;
}

export const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  title,
  message,
  detail,
  onConfirm,
  onCancel,
  isLoading = false,
}) => {
  useInput((input, key) => {
    if (isLoading) return;

    if (input === 'y' || input === 'Y') {
      onConfirm();
    } else if (input === 'n' || input === 'N' || key.escape) {
      onCancel();
    }
  });

  if (isLoading) {
    return (
      <Box justifyContent="center" padding={2}>
        <LoadingSpinner text="Processing..." />
      </Box>
    );
  }

  return (
    <Box flexDirection="column" alignItems="center" justifyContent="center" padding={4}>
      <Box paddingBottom={2}>
        <Text backgroundColor="red" color="white" bold>
          {` ${title} `}
        </Text>
      </Box>

      <Box paddingBottom={1} textWrap="wrap">
        <Text>{message}</Text>
      </Box>

      {detail && (
        <Box paddingBottom={2} textWrap="wrap">
          <Text dimColor>{detail}</Text>
        </Box>
      )}

      <Box paddingTop={1}>
        <Text dimColor>Press 'y' to confirm, 'n' to cancel</Text>
      </Box>
    </Box>
  );
};