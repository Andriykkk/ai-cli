import React from 'react';
import { Box, Text } from 'ink';

export interface MessageSection {
  type: 'text' | 'bullet' | 'code' | 'update' | 'todo';
  content: string;
  title?: string;
  language?: string;
  items?: string[];
  updates?: Array<{
    file: string;
    description: string;
    additions: number;
    removals: number;
    lines: Array<{
      number: number;
      content: string;
      type: 'add' | 'remove' | 'context';
    }>;
  }>;
  todos?: Array<{
    status: 'pending' | 'completed' | 'in_progress';
    content: string;
  }>;
}

interface MessageFormatterProps {
  sections: MessageSection[];
}

export const MessageFormatter: React.FC<MessageFormatterProps> = ({ sections }) => {
  return (
    <Box flexDirection="column">
      {sections.map((section, index) => {
        const isLastSection = index === sections.length - 1;
        const nextSection = sections[index + 1];
        
        // Add spacing after this section if:
        // 1. It's not the last section
        // 2. Next section is a different type (different bullet block)
        const needsSpacing = !isLastSection && (
          section.type !== nextSection?.type ||
          section.type === 'bullet' ||
          section.type === 'text' ||
          section.type === 'update' ||
          section.type === 'todo'
        );
        
        return (
          <Box key={index} flexDirection="column" paddingBottom={needsSpacing ? 1 : 0}>
            {renderSection(section)}
          </Box>
        );
      })}
    </Box>
  );
};

const renderSection = (section: MessageSection) => {
  switch (section.type) {
    case 'bullet':
      return <BulletSection content={section.content} />;
    
    case 'code':
      return <CodeSection content={section.content} language={section.language} />;
    
    case 'update':
      return <UpdateSection updates={section.updates || []} />;
    
    case 'todo':
      return <TodoSection title={section.title} todos={section.todos || []} />;
    
    case 'text':
    default:
      return <TextSection content={section.content} title={section.title} />;
  }
};

// Helper function to parse and render text with bold formatting
const parseTextContent = (content: string) => {
  const parts = content.split(/(\*\*[^*]+\*\*)/g);
  
  return parts.map((part, index) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      const boldText = part.slice(2, -2);
      return <Text key={index} bold>{boldText}</Text>;
    }
    return <Text key={index}>{part}</Text>;
  });
};

const BulletSection: React.FC<{ content: string }> = ({ content }) => {
  return (
    <Box paddingLeft={0}>
      <Text color="cyan">●</Text>
      <Text> </Text>
      {parseTextContent(content)}
    </Box>
  );
};

const TextSection: React.FC<{ content: string; title?: string }> = ({ content, title }) => {
  const lines = content.split('\n').filter(line => line.trim());
  
  return (
    <Box flexDirection="column">
      {title && (
        <Box>
          {parseTextContent(title)}
        </Box>
      )}
      {lines.map((line, index) => (
        <Box key={index} paddingLeft={title ? 2 : 0}>
          {line.startsWith('  -') || line.startsWith('  •') ? (
            <>
              <Text dimColor>  </Text>
              {parseTextContent(line.substring(3))}
            </>
          ) : line.startsWith('- ') || line.startsWith('• ') ? (
            <>
              <Text dimColor>  </Text>
              {parseTextContent(line.substring(2))}
            </>
          ) : (
            parseTextContent(line)
          )}
        </Box>
      ))}
    </Box>
  );
};

const CodeSection: React.FC<{ content: string; language?: string }> = ({ content, language }) => {
  return (
    <Box flexDirection="column" paddingLeft={2}>
      {language && (
        <Box paddingBottom={0}>
          <Text dimColor>```{language}</Text>
        </Box>
      )}
      <Box backgroundColor="gray" padding={1}>
        <Text>{content}</Text>
      </Box>
      <Box>
        <Text dimColor>```</Text>
      </Box>
    </Box>
  );
};

interface UpdateSectionProps {
  updates: Array<{
    file: string;
    description: string;
    additions: number;
    removals: number;
    lines: Array<{
      number: number;
      content: string;
      type: 'add' | 'remove' | 'context';
    }>;
  }>;
}

const UpdateSection: React.FC<UpdateSectionProps> = ({ updates }) => {
  return (
    <Box flexDirection="column">
      <Box>
        <Text color="cyan">●</Text>
        <Text> </Text>
        <Text bold>Update</Text>
        <Text>(</Text>
        <Text color="blue">{updates[0]?.file || 'file'}</Text>
        <Text>)</Text>
      </Box>
      <Box paddingLeft={2}>
        <Text color="green">⎿</Text>
        <Text>  Updated {updates[0]?.file || 'file'} with </Text>
        <Text color="green">{updates[0]?.additions || 0} additions</Text>
        {updates[0]?.removals && updates[0].removals > 0 && (
          <>
            <Text> and </Text>
            <Text color="red">{updates[0].removals} removals</Text>
          </>
        )}
      </Box>
      
      {updates[0]?.lines && (
        <Box flexDirection="column" paddingLeft={4}>
          {updates[0].lines.slice(0, 10).map((line, idx) => (
            <Box key={idx}>
              <Text dimColor>{line.number.toString().padStart(7)}</Text>
              <Text> </Text>
              <Text 
                color={
                  line.type === 'add' ? 'green' :
                  line.type === 'remove' ? 'red' : 'dimColor'
                }
              >
                {line.type === 'add' ? '+' : line.type === 'remove' ? '-' : ' '}
              </Text>
              <Text 
                color={
                  line.type === 'add' ? 'green' :
                  line.type === 'remove' ? 'red' : undefined
                }
              >
                {line.content}
              </Text>
            </Box>
          ))}
        </Box>
      )}
    </Box>
  );
};

interface TodoSectionProps {
  title?: string;
  todos: Array<{
    status: 'pending' | 'completed' | 'in_progress';
    content: string;
  }>;
}

const TodoSection: React.FC<TodoSectionProps> = ({ title, todos }) => {
  return (
    <Box flexDirection="column">
      <Box>
        <Text color="cyan">●</Text>
        <Text> </Text>
        <Text bold>{title || 'Update Todos'}</Text>
      </Box>
      <Box paddingLeft={2}>
        <Text color="green">⎿</Text>
        <Box flexDirection="column" paddingLeft={2}>
          {todos.map((todo, index) => (
            <Box key={index}>
              <Text>
                {todo.status === 'completed' ? '☒' : 
                 todo.status === 'in_progress' ? '◐' : '☐'}
              </Text>
              <Text> </Text>
              {parseTextContent(todo.content)}
            </Box>
          ))}
        </Box>
      </Box>
    </Box>
  );
};