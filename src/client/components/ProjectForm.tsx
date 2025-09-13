import React, { useState, useEffect } from 'react';
import { Box, Text, useInput } from 'ink';
import { LoadingSpinner } from './LoadingSpinner';
import type { Project } from '../types';

interface ProjectFormProps {
  mode: 'create' | 'edit';
  project?: Project;
  onSubmit: (data: { name?: string; path?: string; description?: string }) => Promise<void>;
  onCancel: () => void;
  isLoading?: boolean;
}

export const ProjectForm: React.FC<ProjectFormProps> = ({
  mode,
  project,
  onSubmit,
  onCancel,
  isLoading = false,
}) => {
  const [currentField, setCurrentField] = useState(0);
  const [formData, setFormData] = useState({
    name: project?.name || '',
    path: project?.path || process.cwd(),
    description: project?.description || '',
  });

  const fields = ['name', 'path', 'description'] as const;
  const fieldLabels = {
    name: 'Project Name',
    path: 'Project Path',
    description: 'Description (optional)',
  };

  useInput((input, key) => {
    if (isLoading) return;

    if (key.escape) {
      onCancel();
    } else if (key.tab || key.downArrow) {
      setCurrentField((current) => (current + 1) % fields.length);
    } else if (key.upArrow) {
      setCurrentField((current) => (current - 1 + fields.length) % fields.length);
    } else if (key.return) {
      if (currentField === fields.length - 1) {
        // Submit form
        handleSubmit();
      } else {
        // Move to next field
        setCurrentField(currentField + 1);
      }
    } else if (key.backspace || key.delete) {
      const field = fields[currentField];
      setFormData((prev) => ({
        ...prev,
        [field]: prev[field].slice(0, -1),
      }));
    } else if (input && !key.ctrl && !key.meta) {
      const field = fields[currentField];
      setFormData((prev) => ({
        ...prev,
        [field]: prev[field] + input,
      }));
    }
  });

  const handleSubmit = async () => {
    if (mode === 'create') {
      if (!formData.name.trim() || !formData.path.trim()) {
        return; // Don't submit if required fields are empty
      }
      await onSubmit(formData);
    } else {
      // For edit mode, only send changed fields
      const changes: { name?: string; path?: string; description?: string } = {};
      if (formData.name !== project?.name) changes.name = formData.name;
      if (formData.path !== project?.path) changes.path = formData.path;
      if (formData.description !== project?.description) changes.description = formData.description;
      
      if (Object.keys(changes).length > 0) {
        await onSubmit(changes);
      } else {
        onCancel(); // No changes made
      }
    }
  };

  if (isLoading) {
    return (
      <Box justifyContent="center" padding={2}>
        <LoadingSpinner text={mode === 'create' ? 'Creating project...' : 'Updating project...'} />
      </Box>
    );
  }

  return (
    <Box flexDirection="column" padding={2}>
      <Box paddingBottom={2}>
        <Text backgroundColor="cyan" color="black" bold>
          {` ${mode === 'create' ? 'Create New Project' : 'Edit Project'} `}
        </Text>
      </Box>

      {fields.map((field, index) => {
        const isActive = index === currentField;
        const isRequired = field === 'name' || field === 'path';
        
        return (
          <Box key={field} flexDirection="column" paddingBottom={1}>
            <Text>
              {fieldLabels[field]}{isRequired ? ' *' : ''}:
            </Text>
            <Box>
              <Text
                backgroundColor={isActive ? 'blue' : undefined}
                color={isActive ? 'white' : 'gray'}
              >
                {formData[field] || (isActive ? '█' : '')}
              </Text>
              {isActive && formData[field] && <Text backgroundColor="blue" color="white">█</Text>}
            </Box>
          </Box>
        );
      })}

      <Box paddingTop={2} flexDirection="column">
        <Text dimColor>↑↓ Navigate fields | Tab Next field | Enter Submit | Esc Cancel</Text>
        {mode === 'create' && (
          <Text dimColor>* Required fields</Text>
        )}
      </Box>
    </Box>
  );
};