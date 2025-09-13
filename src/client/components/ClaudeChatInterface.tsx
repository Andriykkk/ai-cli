import React, { useState, useEffect } from 'react';
import { Box, Text, useInput } from 'ink';
import { Header } from './Header';
import { LoadingSpinner } from './LoadingSpinner';
import { MessageFormatter, MessageSection } from './MessageFormatters';
import { ApiService } from '../api';
import type { Project } from '../types';

interface ClaudeChatInterfaceProps {
  project: Project;
  onBack: () => void;
}

interface ChatMessage {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  sections?: MessageSection[];
  timestamp: string;
}

export const ClaudeChatInterface: React.FC<ClaudeChatInterfaceProps> = ({ 
  project, 
  onBack 
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [currentInput, setCurrentInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [scrollPosition, setScrollPosition] = useState(0);
  const [abortController, setAbortController] = useState<AbortController | null>(null);

  useEffect(() => {
    // Add welcome message
    const welcomeMessage: ChatMessage = {
      id: 'welcome',
      type: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
      sections: [
        {
          type: 'bullet',
          content: `Connected to AI CLI project: **${project.name}**`
        },
        {
          type: 'text',
          title: '🤖 AI Assistant Ready',
          content: `I'm ready to help with your ${project.model_provider}/${project.model_name} project.\n\nProject details:\n- Path: ${project.path}\n- Memory: ${project.memory_enabled ? 'Enabled' : 'Disabled'}\n- Tools: ${project.tools_enabled ? 'Enabled' : 'Disabled'}`
        },
        {
          type: 'text',
          title: '💡 Getting Started',
          content: 'You can ask me to:\n- Analyze your code\n- Help with debugging\n- Generate new features\n- Review and refactor existing code\n- Answer questions about your project'
        }
      ]
    };
    
    setMessages([welcomeMessage]);
  }, [project]);

  useInput((input, key) => {
    if (key.escape) {
      if (isLoading && abortController) {
        // Cancel current request
        abortController.abort();
        setAbortController(null);
        setIsLoading(false);
      } else {
        // Go back to projects
        onBack();
      }
    } else if (key.return) {
      if (currentInput.trim() && !isLoading) {
        handleSendMessage(currentInput.trim());
        setCurrentInput('');
      }
    } else if (!isLoading) {
      // Only allow input modification when not loading
      if (key.backspace || key.delete) {
        setCurrentInput((prev) => prev.slice(0, -1));
      } else if (key.upArrow) {
        setScrollPosition(Math.max(0, scrollPosition - 1));
      } else if (key.downArrow) {
        setScrollPosition(scrollPosition + 1);
      } else if (input && !key.ctrl && !key.meta) {
        setCurrentInput((prev) => prev + input);
      }
    }
  });

  const handleSendMessage = async (message: string) => {
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: message,
      timestamp: new Date().toISOString(),
    };
    
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);
    setError('');

    // Create abort controller for cancellation
    const controller = new AbortController();
    setAbortController(controller);

    try {
      const response = await ApiService.sendMessage({
        message,
        project_id: project.id,
      }, controller.signal);

      // Parse response into Claude-style sections
      const assistantMessage: ChatMessage = {
        id: Date.now().toString() + '_assistant',
        type: 'assistant',
        content: response.response,
        timestamp: response.timestamp,
        sections: parseResponseToSections(response.response)
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      // Don't show error if request was aborted
      if (err instanceof Error && (err.name === 'AbortError' || err.name === 'CanceledError' || err.message.includes('canceled'))) {
        const cancelMessage: ChatMessage = {
          id: Date.now().toString() + '_cancel',
          type: 'assistant',
          content: 'Canceled by user',
          timestamp: new Date().toISOString()
        };
        setMessages((prev) => [...prev, cancelMessage]);
      } else {
        setError(err instanceof Error ? err.message : 'Failed to send message');
        
        const errorMessage: ChatMessage = {
          id: Date.now().toString() + '_error',
          type: 'assistant',
          content: '',
          timestamp: new Date().toISOString(),
          sections: [
            {
              type: 'bullet',
              content: `❌ Error: ${err instanceof Error ? err.message : 'Failed to send message'}`
            }
          ]
        };
        
        setMessages((prev) => [...prev, errorMessage]);
      }
    } finally {
      setIsLoading(false);
      setAbortController(null);
    }
  };

  const parseResponseToSections = (response: string): MessageSection[] => {
    const lines = response.split('\n');
    const sections: MessageSection[] = [];
    
    let currentSection: MessageSection | null = null;
    let currentTextContent: string[] = [];
    
    const flushTextContent = () => {
      if (currentTextContent.length > 0) {
        sections.push({
          type: 'text',
          content: currentTextContent.join('\n')
        });
        currentTextContent = [];
      }
    };
    
    for (const line of lines) {
      const trimmed = line.trim();
      
      if (trimmed.startsWith('●') || trimmed.startsWith('•')) {
        // Flush any accumulated text content before bullet
        flushTextContent();
        
        // Bullet point
        sections.push({
          type: 'bullet',
          content: trimmed.substring(1).trim()
        });
      } else if (trimmed.startsWith('```')) {
        // Flush text before code block
        flushTextContent();
        
        // Code block
        const language = trimmed.substring(3);
        currentSection = {
          type: 'code',
          content: '',
          language: language || undefined
        };
      } else if (currentSection?.type === 'code' && trimmed === '```') {
        // End code block
        sections.push(currentSection);
        currentSection = null;
      } else if (currentSection?.type === 'code') {
        // Inside code block
        currentSection.content += line + '\n';
      } else if (trimmed.length > 0) {
        // Accumulate regular text lines
        currentTextContent.push(trimmed);
      } else if (currentTextContent.length > 0) {
        // Empty line - flush current text content
        flushTextContent();
      }
    }
    
    // Flush any remaining text content
    flushTextContent();
    
    if (currentSection) {
      sections.push(currentSection);
    }
    
    return sections.length > 0 ? sections : [{ type: 'text', content: response }];
  };

  const formatTime = (timestamp: string) => {
    try {
      return new Date(timestamp).toLocaleTimeString([], { 
        hour: '2-digit', 
        minute: '2-digit' 
      });
    } catch {
      return '';
    }
  };

  return (
    <Box flexDirection="column" width="100%" height="100%">
      <Header 
        title={`Chat - ${project.name}`} 
        subtitle={`${project.model_provider}/${project.model_name} • ${formatTime(new Date().toISOString())}`}
      />

      {/* Chat Messages */}
      <Box flexGrow={1} flexDirection="column" padding={1} overflowY="auto">
        {messages.map((msg, index) => (
          <Box key={msg.id} flexDirection="column" paddingBottom={1}>
            {/* Message Header */}
            <Box>
              {msg.type === 'user' ? (
                <Box>
                  <Text backgroundColor="green" color="white" bold> You </Text>
                  <Text dimColor> {formatTime(msg.timestamp)}</Text>
                </Box>
              ) : (
                <Box>
                  <Text backgroundColor="cyan" color="black" bold> AI Assistant </Text>
                  <Text dimColor> {formatTime(msg.timestamp)}</Text>
                </Box>
              )}
            </Box>

            {/* Message Content */}
            <Box paddingLeft={0}>
              {msg.sections ? (
                <MessageFormatter sections={msg.sections} />
              ) : (
                <Text>{msg.content}</Text>
              )}
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
      <Box flexDirection="column" paddingX={1} paddingBottom={1}>
        {/* Loading indicator above input */}
        {isLoading && (
          <Box justifyContent="center" paddingBottom={1}>
            <LoadingSpinner text="AI is thinking..." />
          </Box>
        )}
        
        {/* Input Box */}
        <Box 
          borderStyle="round" 
          paddingX={1} 
          paddingY={0}
          minHeight={3}
          flexDirection="column"
          borderColor={isLoading ? 'yellow' : undefined}
        >
          <Text>
            {currentInput}
            {!isLoading && <Text backgroundColor="white" color="black">█</Text>}
          </Text>
        </Box>
        
        <Box justifyContent="center" paddingTop={1}>
          <Text dimColor>
            {isLoading 
              ? 'Press Esc to cancel • AI is processing your request...'
              : 'Type your message and press Enter • ↑↓ Scroll • Esc Back to projects'
            }
          </Text>
        </Box>
      </Box>
    </Box>
  );
};