import React from 'react';
import { Box, Text } from 'ink';
import { LoadingSpinner } from './LoadingSpinner';
import type { Project } from '../types';
import fs from 'fs';

interface ProjectListProps {
  projects: Project[];
  selectedIndex: number;
  isLoading?: boolean;
}

export const ProjectList: React.FC<ProjectListProps> = ({
  projects,
  selectedIndex,
  isLoading = false,
}) => {
  if (isLoading && projects.length === 0) {
    return (
      <Box justifyContent="center" padding={2}>
        <LoadingSpinner text="Loading projects..." />
      </Box>
    );
  }

  if (projects.length === 0) {
    return (
      <Box flexDirection="column" alignItems="center" justifyContent="center" padding={4}>
        <Text dimColor>No projects found</Text>
        <Text dimColor>Press 'n' to create your first project</Text>
      </Box>
    );
  }

  const formatDate = (dateString: string | undefined) => {
    if (!dateString) return 'Never';
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return 'Unknown';
    }
  };

  const checkPathExists = (path: string): boolean => {
    try {
      return fs.existsSync(path);
    } catch {
      return false;
    }
  };

  const truncateText = (text: string, maxLength: number): string => {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength - 3) + '...';
  };

  return (
    <Box flexDirection="column" padding={1}>
      {/* Header */}
      <Box paddingBottom={1}>
        <Text dimColor>
          {'S'} {'Name'.padEnd(20)} {'Path'.padEnd(30)} {'Last Used'.padEnd(20)} {'Description'}
        </Text>
      </Box>
      
      {/* Legend */}
      <Box paddingBottom={1}>
        <Text dimColor>
          <Text color="green">✓</Text> Path exists | <Text color="red">✗</Text> Path missing
        </Text>
      </Box>

      {/* Project list */}
      {projects.map((project, index) => {
        const isSelected = index === selectedIndex;
        const pathExists = checkPathExists(project.path);
        const status = pathExists ? '✓' : '✗';
        const statusColor = pathExists ? 'green' : 'red';
        
        return (
          <Box key={project.id} paddingY={0}>
            <Text 
              backgroundColor={isSelected ? 'blue' : undefined}
              color={isSelected ? 'white' : undefined}
            >
              <Text color={statusColor}>{status}</Text>
              {' '}
              <Text>{truncateText(project.name, 20).padEnd(20)}</Text>
              {' '}
              <Text dimColor>{truncateText(project.path, 30).padEnd(30)}</Text>
              {' '}
              <Text dimColor>{formatDate(project.last_used).padEnd(20)}</Text>
              {' '}
              <Text dimColor>{truncateText(project.description || '', 25)}</Text>
            </Text>
          </Box>
        );
      })}

      {isLoading && (
        <Box paddingTop={1}>
          <LoadingSpinner text="Updating..." />
        </Box>
      )}
    </Box>
  );
};