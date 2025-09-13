import React, { useState, useEffect } from 'react';
import { Box, Text, useInput } from 'ink';
import { Header } from './Header';
import { Footer } from './Footer';
import { LoadingSpinner } from './LoadingSpinner';
import { ApiService } from '../api';
import type { Project, ChatResponse } from '../types';

interface ChatInterfaceProps {
  project: Project;
  onBack: () => void;
}

interface ChatMessage {
  type: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({ project, onBack }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [currentInput, setCurrentInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    // Add welcome message
    setMessages([
      {
        type: 'system',
        content: `Welcome to AI CLI! 🤖\nProject: ${project.name}\nStart typing your message and press Enter to send.`,
        timestamp: new Date().toISOString(),
      },
    ]);
  }, [project]);

  useInput((input, key) => {
    if (key.escape) {
      onBack();
    } else if (key.return) {
      if (currentInput.trim() && !isLoading) {
        handleSendMessage(currentInput.trim());
        setCurrentInput('');
      }
    } else if (key.backspace || key.delete) {
      setCurrentInput((prev) => prev.slice(0, -1));
    } else if (input && !key.ctrl && !key.meta) {
      setCurrentInput((prev) => prev + input);
    }
  });

  const handleSendMessage = async (message: string) => {
    // Add user message
    const userMessage: ChatMessage = {
      type: 'user',
      content: message,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);

    setIsLoading(true);
    setError('');

    try {
      // Send to API
      const response = await ApiService.sendMessage({
        message,
        project_id: project.id,
      });

      // Add assistant response
      const assistantMessage: ChatMessage = {
        type: 'assistant',
        content: response.response,
        timestamp: response.timestamp,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send message');
      
      // Add error message
      const errorMessage: ChatMessage = {
        type: 'system',
        content: `Error: ${err instanceof Error ? err.message : 'Failed to send message'}`,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    }

    setIsLoading(false);
  };

  const formatTime = (timestamp: string) => {
    try {
      return new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '';
    }
  };

  return (
    <Box flexDirection="column" width="100%" height="100%">
      <Header 
        title={`Chat - ${project.name}`} 
        subtitle={`${project.model_provider}/${project.model_name}`}
      />

      {/* Chat Messages */}
      <Box flexGrow={1} flexDirection="column" padding={1}>
        {messages.map((msg, index) => (
          <Box key={index} flexDirection="column" paddingBottom={1}>
            <Box>
              {msg.type === 'user' && (
                <Text color="green" bold>💭 You ({formatTime(msg.timestamp)}): </Text>
              )}
              {msg.type === 'assistant' && (
                <Text color="cyan" bold>🤖 AI ({formatTime(msg.timestamp)}): </Text>
              )}
              {msg.type === 'system' && (
                <Text color="yellow" bold>ℹ️  System: </Text>
              )}
            </Box>
            <Box paddingLeft={2} textWrap="wrap">
              <Text>{msg.content}</Text>
            </Box>
          </Box>
        ))}

        {isLoading && (
          <Box paddingY={1}>
            <LoadingSpinner text="AI is thinking..." />
          </Box>
        )}
      </Box>

      {/* Input Area */}
      <Box flexDirection="column" padding={1}>
        <Box>
          <Text>Message: </Text>
          <Text backgroundColor="blue" color="white">
            {currentInput}█
          </Text>
        </Box>
      </Box>

      <Footer 
        shortcuts={['Type message and press Enter', 'Esc Back to projects']}
      />
    </Box>
  );
};