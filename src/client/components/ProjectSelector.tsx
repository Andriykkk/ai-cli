import React, { useState, useEffect } from 'react';
import { Box, Text, useInput, useApp } from 'ink';
import { Header } from './Header';
import { Footer } from './Footer';
import { ProjectList } from './ProjectList';
import { ProjectForm } from './ProjectForm';
import { ConfirmDialog } from './ConfirmDialog';
import type { Project } from '../types';

interface ProjectSelectorProps {
  projects: Project[];
  onProjectSelect: (project: Project) => Promise<void>;
  onProjectCreate: (project: { name: string; path: string; description: string }) => Promise<void>;
  onProjectEdit: (projectId: number, updates: { name?: string; path?: string; description?: string }) => Promise<void>;
  onProjectDelete: (projectId: number) => Promise<void>;
  onRefresh: () => Promise<void>;
  onOpenSettings: () => void;
}

type Mode = 'list' | 'create' | 'edit' | 'delete-confirm';

export const ProjectSelector: React.FC<ProjectSelectorProps> = ({
  projects,
  onProjectSelect,
  onProjectCreate,
  onProjectEdit,
  onProjectDelete,
  onRefresh,
  onOpenSettings,
}) => {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [mode, setMode] = useState<Mode>('list');
  const [editingProject, setEditingProject] = useState<Project | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const { exit } = useApp();

  // Reset selection when projects change
  useEffect(() => {
    if (selectedIndex >= projects.length) {
      setSelectedIndex(Math.max(0, projects.length - 1));
    }
  }, [projects, selectedIndex]);

  // Keyboard input handling
  useInput((input, key) => {
    if (isLoading) return;

    // Global shortcuts
    if (key.ctrl && input === 'c') {
      exit();
      return;
    }

    if (mode === 'list') {
      handleListInput(input, key);
    } else if (mode === 'delete-confirm') {
      handleDeleteConfirmInput(input, key);
    }
    // Forms handle their own input
  });

  const handleListInput = (input: string, key: any) => {
    if (key.upArrow || input === 'k') {
      setSelectedIndex(Math.max(0, selectedIndex - 1));
    } else if (key.downArrow || input === 'j') {
      setSelectedIndex(Math.min(projects.length - 1, selectedIndex + 1));
    } else if (key.return) {
      if (projects[selectedIndex]) {
        handleProjectSelect(projects[selectedIndex]);
      }
    } else if (input === 'n') {
      setMode('create');
    } else if (input === 'e') {
      if (projects[selectedIndex]) {
        setEditingProject(projects[selectedIndex]);
        setMode('edit');
      }
    } else if (input === 'd') {
      if (projects[selectedIndex]) {
        setEditingProject(projects[selectedIndex]);
        setMode('delete-confirm');
      }
    } else if (input === 'r') {
      handleRefresh();
    } else if (input === 's' || input === 'S') {
      onOpenSettings();
    } else if (input === 'q') {
      exit();
    }
  };

  const handleDeleteConfirmInput = (input: string, key: any) => {
    if (input === 'y' || input === 'Y') {
      if (editingProject) {
        handleProjectDelete(editingProject.id);
      }
    } else {
      setMode('list');
      setEditingProject(null);
    }
  };

  const handleProjectSelect = async (project: Project) => {
    setIsLoading(true);
    try {
      await onProjectSelect(project);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to select project');
    }
    setIsLoading(false);
  };

  const handleProjectCreate = async (projectData: { name: string; path: string; description: string }) => {
    setIsLoading(true);
    setError('');
    try {
      await onProjectCreate(projectData);
      setMode('list');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create project');
    }
    setIsLoading(false);
  };

  const handleProjectEdit = async (updates: { name?: string; path?: string; description?: string }) => {
    if (!editingProject) return;
    
    setIsLoading(true);
    setError('');
    try {
      await onProjectEdit(editingProject.id, updates);
      setMode('list');
      setEditingProject(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update project');
    }
    setIsLoading(false);
  };

  const handleProjectDelete = async (projectId: number) => {
    setIsLoading(true);
    setError('');
    try {
      await onProjectDelete(projectId);
      setMode('list');
      setEditingProject(null);
      // Adjust selection if needed
      if (selectedIndex >= projects.length - 1) {
        setSelectedIndex(Math.max(0, projects.length - 2));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete project');
      setMode('list');
      setEditingProject(null);
    }
    setIsLoading(false);
  };

  const handleRefresh = async () => {
    setIsLoading(true);
    try {
      await onRefresh();
    } catch (err) {
      setError('Failed to refresh projects');
    }
    setIsLoading(false);
  };

  const handleCancel = () => {
    setMode('list');
    setEditingProject(null);
    setError('');
  };

  return (
    <Box flexDirection="column" width="100%" height="100%">
      <Header title="AI CLI - Project Manager" subtitle={`${projects.length} projects available`} />
      
      {error && (
        <Box padding={1}>
          <Text color="red">Error: {error}</Text>
        </Box>
      )}

      <Box flexGrow={1}>
        {mode === 'list' && (
          <ProjectList
            projects={projects}
            selectedIndex={selectedIndex}
            isLoading={isLoading}
          />
        )}

        {mode === 'create' && (
          <ProjectForm
            mode="create"
            onSubmit={handleProjectCreate}
            onCancel={handleCancel}
            isLoading={isLoading}
          />
        )}

        {mode === 'edit' && editingProject && (
          <ProjectForm
            mode="edit"
            project={editingProject}
            onSubmit={handleProjectEdit}
            onCancel={handleCancel}
            isLoading={isLoading}
          />
        )}

        {mode === 'delete-confirm' && editingProject && (
          <ConfirmDialog
            title="Delete Project"
            message={`Are you sure you want to delete "${editingProject.name}"?`}
            detail={`Path: ${editingProject.path}`}
            onConfirm={() => handleProjectDelete(editingProject.id)}
            onCancel={handleCancel}
            isLoading={isLoading}
          />
        )}
      </Box>

      <Footer
        shortcuts={
          mode === 'list'
            ? [
                '↑↓ Navigate',
                'Enter Select',
                'n New',
                'e Edit',
                'd Delete',
                'r Refresh',
                's Settings',
                'q Quit',
              ]
            : ['Esc Cancel']
        }
      />
    </Box>
  );
};