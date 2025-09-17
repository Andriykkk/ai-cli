import React, { useState, useEffect } from 'react';
import { Box, Text, useInput } from 'ink';
import { Header } from './Header';
import { LoadingSpinner } from './LoadingSpinner';
import { MessageFormatter, MessageSection } from './MessageFormatters';
import { ToolApprovalComponent } from './ToolApprovalComponent';
import { ToolResultDisplay } from './ToolResultDisplay';
import { ApiService } from '../api';
import type { Project } from '../types';
import type { ConversationStep, ToolCall } from '../tool-types';

interface ClaudeChatInterfaceProps {
  project: Project;
  onBack: () => void;
  onOpenSettings: () => void;
}

interface ChatMessage {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  sections?: MessageSection[];
  timestamp: string;
  toolCalls?: ToolCall[];
  toolResults?: Array<{
    tool_call_id: string;
    name: string;
    content: string;
    success: boolean;
  }>;
}

type ConversationState = 'idle' | 'generating' | 'tool_approval' | 'tool_executing' | 'completed';

export const ClaudeChatInterface: React.FC<ClaudeChatInterfaceProps> = ({
  project,
  onBack,
  onOpenSettings
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [currentInput, setCurrentInput] = useState('');
  const [conversationState, setConversationState] = useState<ConversationState>('idle');
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  const [error, setError] = useState('');
  const [scrollPosition, setScrollPosition] = useState(0);
  const [abortController, setAbortController] = useState<AbortController | null>(null);
  const [pendingToolCalls, setPendingToolCalls] = useState<ToolCall[]>([]);
  const [pendingContent, setPendingContent] = useState<string>('');
  const [toolResultsVisible, setToolResultsVisible] = useState<boolean>(true);
  const [currentStream, setCurrentStream] = useState<ReadableStream<ConversationStep> | null>(null);

  useEffect(() => {
    loadChatHistory();
  }, [project]);

  const loadChatHistory = async () => {
    try {
      setIsLoadingHistory(true);

      // Load recent chat history (up to ~2MB worth of messages)
      const historyResponse = await ApiService.getRecentChatHistory(project.id, 100);
      const historicalMessages: ChatMessage[] = [];

      // Convert historical messages to ChatMessage format
      historyResponse.messages.forEach((histMsg) => {
        // Add user message
        historicalMessages.push({
          id: `${histMsg.id}_user`,
          type: 'user',
          content: histMsg.message,
          timestamp: histMsg.timestamp
        });

        // Add assistant response
        historicalMessages.push({
          id: `${histMsg.id}_assistant`,
          type: 'assistant',
          content: histMsg.response,
          timestamp: histMsg.timestamp,
          sections: parseResponseToSections(histMsg.response)
        });
      });

      // Add welcome message if no history exists
      if (historicalMessages.length === 0) {
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
      } else {
        // Show loaded history with a separator
        const historySeparator: ChatMessage = {
          id: 'history_separator',
          type: 'assistant',
          content: '',
          timestamp: new Date().toISOString(),
          sections: [
            {
              type: 'bullet',
              content: `📜 **Chat History Loaded** - ${historyResponse.messages.length} previous conversations restored`
            }
          ]
        };
        setMessages([historySeparator, ...historicalMessages]);
      }

    } catch (err) {
      console.error('Failed to load chat history:', err);

      // Fall back to welcome message
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
            title: '⚠️ Chat History',
            content: 'Could not load previous conversations, but you can start a new chat.'
          }
        ]
      };
      setMessages([welcomeMessage]);
    } finally {
      setIsLoadingHistory(false);
    }
  };

  useInput((input, key) => {
    // Handle tool approval state separately
    if (conversationState === 'tool_approval') {
      return; // Let ToolApprovalComponent handle input
    }

    if (key.escape) {
      if (conversationState !== 'idle' && abortController) {
        // Cancel current request
        abortController.abort();
        setAbortController(null);
        setConversationState('idle');
        setPendingToolCalls([]);
        setPendingContent('');
      } else {
        // Go back to projects
        onBack();
      }
    } else if (key.return) {
      if (currentInput.trim() && conversationState === 'idle') {
        handleSendMessage(currentInput.trim());
        setCurrentInput('');
      }
    } else if (conversationState === 'idle') {
      // Only allow input modification when idle
      if (key.backspace || key.delete) {
        setCurrentInput((prev) => prev.slice(0, -1));
      } else if (key.upArrow) {
        setScrollPosition(Math.max(0, scrollPosition - 1));
      } else if (key.downArrow) {
        setScrollPosition(scrollPosition + 1);
      } else if ((input === 's' || input === 'S') && key.ctrl) {
        // Ctrl+S opens settings
        onOpenSettings();
      } else if ((input === 'r' || input === 'R') && key.ctrl) {
        // Ctrl+R toggles tool results visibility
        setToolResultsVisible(prev => !prev);
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
    setConversationState('generating');
    setError('');

    // Create abort controller for cancellation
    const controller = new AbortController();
    setAbortController(controller);

    try {
      const stream = await ApiService.sendMessageStream({
        message,
        project_id: project.id,
      }, controller.signal);

      setCurrentStream(stream);
      await processConversationStream(stream);

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
      setConversationState('idle');
      setAbortController(null);
      setCurrentStream(null);
    }
  };

  const processConversationStream = async (stream: ReadableStream<ConversationStep>) => {
    const reader = stream.getReader();
    
    try {
      while (true) {
        const { done, value } = await reader.read();
        
        if (done) break;
        
        await handleConversationStep(value);
      }
    } finally {
      reader.releaseLock();
    }
  };

  const handleConversationStep = async (step: ConversationStep) => {
    switch (step.state) {
      case 'generating':
        setConversationState('generating');
        break;
        
      case 'tool_approval':
        setConversationState('tool_approval');
        setPendingContent(step.content || '');
        setPendingToolCalls(step.tool_calls || []);
        break;
        
      case 'tool_executing':
        setConversationState('tool_executing');
        break;
        
      case 'completed':
        if (step.error) {
          setError(step.error);
          const errorMessage: ChatMessage = {
            id: Date.now().toString() + '_error',
            type: 'assistant',
            content: '',
            timestamp: new Date().toISOString(),
            sections: [
              {
                type: 'bullet',
                content: `❌ Error: ${step.error}`
              }
            ]
          };
          setMessages((prev) => [...prev, errorMessage]);
        } else if (step.content) {
          const assistantMessage: ChatMessage = {
            id: Date.now().toString() + '_assistant',
            type: 'assistant',
            content: step.content,
            timestamp: new Date().toISOString(),
            sections: parseResponseToSections(step.content),
            toolResults: step.tool_results
          };
          setMessages((prev) => [...prev, assistantMessage]);
        }
        
        setConversationState('idle');
        setPendingToolCalls([]);
        setPendingContent('');
        break;
    }
  };

  const handleToolApproval = async (approvedTools: string[], deniedTools: string[]) => {
    setConversationState('tool_executing');
    
    try {
      const stream = await ApiService.sendToolApproval({
        project_id: project.id,
        approved_tools: approvedTools,
        denied_tools: deniedTools
      });

      await processConversationStream(stream);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to process tool approval');
      setConversationState('idle');
    }
  };

  const handleToolApprovalCancel = () => {
    setConversationState('idle');
    setPendingToolCalls([]);
    setPendingContent('');
    
    if (abortController) {
      abortController.abort();
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
        {isLoadingHistory ? (
          <Box flexGrow={1} justifyContent="center" alignItems="center">
            <LoadingSpinner text="Loading chat history..." />
          </Box>
        ) : (
          <>
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

                {/* Tool Results Display */}
                {msg.toolResults && msg.toolResults.length > 0 && (
                  <ToolResultDisplay 
                    toolResults={msg.toolResults} 
                    isVisible={toolResultsVisible} 
                  />
                )}
              </Box>
            ))}

            {/* Loading States */}
            {conversationState === 'generating' && (
              <Box paddingY={1}>
                <LoadingSpinner text="AI is thinking..." />
              </Box>
            )}

            {conversationState === 'tool_executing' && (
              <Box paddingY={1}>
                <LoadingSpinner text="Executing tools..." />
              </Box>
            )}
          </>
        )}
      </Box>

      {/* Tool Approval Component */}
      {conversationState === 'tool_approval' && (
        <ToolApprovalComponent
          content={pendingContent}
          toolCalls={pendingToolCalls}
          onApproval={handleToolApproval}
          onCancel={handleToolApprovalCancel}
        />
      )}

      {/* Input Area - Hidden during tool approval */}
      {conversationState !== 'tool_approval' && (
        <Box flexDirection="column" paddingX={1} paddingBottom={1}>
          {/* Input Box */}
          <Box
            borderStyle="round"
            paddingX={1}
            paddingY={0}
            minHeight={3}
            flexDirection="column"
            borderColor={conversationState !== 'idle' ? 'yellow' : undefined}
          >
            <Text>
              {currentInput}
              {conversationState === 'idle' && <Text backgroundColor="white" color="black">█</Text>}
            </Text>
          </Box>

          <Box justifyContent="center" paddingTop={1}>
            <Text dimColor>
              {conversationState === 'generating' && 'Press Esc to cancel • AI is generating response...'}
              {conversationState === 'tool_executing' && 'Press Esc to cancel • Executing approved tools...'}
              {conversationState === 'idle' && 'Type your message and press Enter • ↑↓ Scroll • Ctrl+S Settings • Ctrl+R Toggle tool results • Esc Back to projects'}
            </Text>
          </Box>
        </Box>
      )}
    </Box>
  );
};