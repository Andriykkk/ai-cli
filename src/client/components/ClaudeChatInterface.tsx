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
import * as fs from 'fs';
import * as path from 'path';

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

// Client logging function
const logToFile = (message: string, data?: any) => {
  try {
    const timestamp = new Date().toISOString();
    // const logEntry = `[${timestamp}] ${message}${data ? ` - ${JSON.stringify(data, null, 2)}` : ''}\n`;
    // const logPath = path.join(process.cwd(), 'client_debug.log');
    // fs.appendFileSync(logPath, logEntry);
  } catch (e) {
    // Ignore logging errors
  }
};

export const ClaudeChatInterface: React.FC<ClaudeChatInterfaceProps> = ({
  project,
  onBack,
  onOpenSettings
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [currentInput, setCurrentInput] = useState('');
  const [cursorPosition, setCursorPosition] = useState(0);
  const [desiredColumn, setDesiredColumn] = useState(0); // For smart line navigation
  const [commandHistory, setCommandHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
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

  // Keep cursor position within bounds
  useEffect(() => {
    setCursorPosition(pos => Math.min(pos, currentInput.length));
  }, [currentInput]);

  useEffect(() => {
    logToFile('🔄 ConversationState changed', {
      newState: conversationState,
      pendingToolCallsCount: pendingToolCalls.length,
      pendingContentExists: !!pendingContent
    });
  }, [conversationState, pendingToolCalls, pendingContent]);

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
        // Add to command history
        const newCommand = currentInput.trim();
        setCommandHistory(prev => {
          const filtered = prev.filter(cmd => cmd !== newCommand);
          return [newCommand, ...filtered].slice(0, 50); // Keep last 50 commands
        });
        setHistoryIndex(-1);

        handleSendMessage(newCommand);
        setCurrentInput('');
        setCursorPosition(0);
      }
    } else if (conversationState === 'idle') {
      // Only allow input modification when idle
      if (key.backspace) {
        if (cursorPosition > 0) {
          setCurrentInput((prev) =>
            prev.slice(0, cursorPosition - 1) + prev.slice(cursorPosition)
          );
          setCursorPosition(pos => pos - 1);
        }
      } else if (key.delete) {
        setCurrentInput((prev) =>
          prev.slice(0, cursorPosition) + prev.slice(cursorPosition + 1)
        );
      } else if (key.leftArrow) {
        setCursorPosition(pos => Math.max(0, pos - 1));
      } else if (key.rightArrow) {
        setCursorPosition(pos => Math.min(currentInput.length, pos + 1));
      } else if (key.upArrow) {
        // Navigate command history up (if at start of line) or scroll messages
        if (cursorPosition === 0 && currentInput.length === 0) {
          if (historyIndex < commandHistory.length - 1) {
            const newIndex = historyIndex + 1;
            setHistoryIndex(newIndex);
            const historicalCommand = commandHistory[newIndex];
            setCurrentInput(historicalCommand);
            setCursorPosition(historicalCommand.length);
          }
        } else {
          setScrollPosition(Math.max(0, scrollPosition - 1));
        }
      } else if (key.downArrow) {
        // Navigate command history down (if at start of line) or scroll messages
        if (cursorPosition === 0 && currentInput.length === 0) {
          if (historyIndex > 0) {
            const newIndex = historyIndex - 1;
            setHistoryIndex(newIndex);
            const historicalCommand = commandHistory[newIndex];
            setCurrentInput(historicalCommand);
            setCursorPosition(historicalCommand.length);
          } else if (historyIndex === 0) {
            setHistoryIndex(-1);
            setCurrentInput('');
            setCursorPosition(0);
          }
        } else {
          setScrollPosition(scrollPosition + 1);
        }
      } else if (key.home) {
        setCursorPosition(0);
      } else if (key.end) {
        setCursorPosition(currentInput.length);
      } else if ((input === 's' || input === 'S') && key.ctrl) {
        // Ctrl+S opens settings
        onOpenSettings();
      } else if ((input === 'r' || input === 'R') && key.ctrl) {
        // Ctrl+R toggles tool results visibility
        setToolResultsVisible(prev => !prev);
      } else if (input && !key.ctrl && !key.meta) {
        // Insert character at cursor position
        setCurrentInput((prev) =>
          prev.slice(0, cursorPosition) + input + prev.slice(cursorPosition)
        );
        setCursorPosition(pos => pos + 1);
        // Reset history navigation when typing
        if (historyIndex !== -1) {
          setHistoryIndex(-1);
        }
      }
    }
  });

  const handleSendMessage = async (message: string) => {
    logToFile('🚀 Starting to send message', { message, projectId: project.id });

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
      logToFile('📡 Calling ApiService.sendMessageStream');
      const stream = await ApiService.sendMessageStream({
        message,
        project_id: project.id,
      }, controller.signal);

      logToFile('📡 Stream received, starting to process');
      setCurrentStream(stream);
      await processConversationStream(stream);

      // Note: Don't set final state here, let the conversation steps handle it

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
        setConversationState('idle');
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
        setConversationState('idle');
      }
    } finally {
      // Only clean up resources, don't change conversation state
      // The conversation state should be determined by the last received step
      logToFile('🧹 Cleanup: cleaning up resources only');
      setAbortController(null);
      setCurrentStream(null);
    }
  };

  const processConversationStream = async (stream: ReadableStream<ConversationStep>) => {
    logToFile('📡 Starting to process conversation stream');
    const reader = stream.getReader();

    try {
      while (true) {
        const { done, value } = await reader.read();

        logToFile('📦 Stream chunk received', { done, value });

        if (done) {
          logToFile('✅ Stream completed');
          break;
        }

        await handleConversationStep(value);
      }
    } finally {
      reader.releaseLock();
    }
  };

  const handleConversationStep = async (step: ConversationStep) => {
    logToFile('🔄 Received conversation step', step);

    switch (step.state) {
      case 'generating':
        logToFile('⚡ Setting state to generating');
        setConversationState('generating');
        break;

      case 'tool_approval':
        logToFile('🛠️ Setting state to tool_approval', {
          toolCount: step.tool_calls?.length,
          content: step.content?.substring(0, 100)
        });
        setConversationState('tool_approval');
        setPendingContent(step.content || '');
        setPendingToolCalls(step.tool_calls || []);
        logToFile('🛠️ State and pending data set', {
          newState: 'tool_approval',
          pendingContent: step.content || '',
          pendingToolCallsCount: (step.tool_calls || []).length
        });
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
    logToFile('🛠️ Tool approval submitted', { approvedTools, deniedTools });
    setConversationState('tool_executing');

    try {
      logToFile('📡 Calling ApiService.sendToolApproval');
      const stream = await ApiService.sendToolApproval({
        project_id: project.id,
        approved_tools: approvedTools,
        denied_tools: deniedTools
      });

      logToFile('📡 Tool approval stream received, processing');
      await processConversationStream(stream);
      logToFile('✅ Tool approval stream completed');

    } catch (err) {
      logToFile('❌ Tool approval error', { error: err });
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
      {(() => {
        const shouldShow = conversationState === 'tool_approval';
        logToFile('🎨 Render check for ToolApprovalComponent', {
          conversationState,
          shouldShow,
          pendingToolCallsCount: pendingToolCalls.length,
          pendingContent: pendingContent?.substring(0, 50)
        });
        return shouldShow ? (
          <ToolApprovalComponent
            content={pendingContent}
            toolCalls={pendingToolCalls}
            onApproval={handleToolApproval}
            onCancel={handleToolApprovalCancel}
          />
        ) : null;
      })()}

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
              {conversationState === 'idle' ? (
                <>
                  {currentInput.slice(0, cursorPosition)}
                  <Text backgroundColor="white" color="black">█</Text>
                  {currentInput.slice(cursorPosition)}
                </>
              ) : (
                currentInput
              )}
            </Text>
          </Box>

          <Box justifyContent="center" paddingTop={1}>
            <Text dimColor>
              {conversationState === 'generating' && 'Press Esc to cancel • AI is generating response...'}
              {conversationState === 'tool_executing' && 'Press Esc to cancel • Executing approved tools...'}
              {conversationState === 'idle' && 'Type your message and press Enter • ←→ Move cursor • ↑↓ History/Scroll • Home/End • Ctrl+S Settings • Ctrl+R Toggle tool results • Esc Back to projects'}
            </Text>
          </Box>
        </Box>
      )}
    </Box>
  );
};