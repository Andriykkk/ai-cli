import React, { useState, useEffect } from 'react';
import { Box, Text } from 'ink';
import { ProjectSelector } from './ProjectSelector';
import { ClaudeChatInterface } from './ClaudeChatInterface';
import { SettingsInterface } from './SettingsInterface';
import { LoadingSpinner } from './LoadingSpinner';
import { ErrorDisplay } from './ErrorDisplay';
import { ApiService } from '../api';
import type { Project, AppState } from '../types';

export const App = () => {
  const [appState, setAppState] = useState<AppState>('loading');
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<Project | undefined>();
  const [error, setError] = useState<string>('');

  // Initialize app
  useEffect(() => {
    initializeApp();
  }, []);

  const initializeApp = async () => {
    try {
      setAppState('loading');

      // Test server connection
      const isConnected = await ApiService.testConnection();
      if (!isConnected) {
        throw new Error('Cannot connect to AI CLI server. Please start the server with: python server/main.py');
      }

      // Load projects
      await loadProjects();
      setAppState('project-selection');

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error occurred');
      setAppState('error');
    }
  };

  const loadProjects = async () => {
    try {
      const projectList = await ApiService.getProjects();
      setProjects(projectList);
    } catch (err) {
      throw new Error('Failed to load projects from server');
    }
  };

  const handleProjectSelect = async (project: Project) => {
    try {
      // Mark project as used
      await ApiService.useProject(project.id);
      setSelectedProject(project);
      setAppState('chat');
    } catch (err) {
      setError('Failed to select project');
      setAppState('error');
    }
  };

  const handleBackToProjects = () => {
    setSelectedProject(undefined);
    setAppState('project-selection');
    // Reload projects to get updated last_used times
    loadProjects();
  };

  const handleOpenSettings = () => {
    setAppState('settings');
  };

  const handleBackFromSettings = () => {
    if (selectedProject) {
      setAppState('chat');
    } else {
      setAppState('project-selection');
    }
  };

  const handleBackFromProjectSettings = () => {
    // After project settings, go to chat with the project
    if (selectedProject) {
      setAppState('chat');
    } else {
      setAppState('project-selection');
    }
  };

  const handleProjectCreate = async (projectData: { name: string; path: string; description: string }) => {
    try {
      const newProject = await ApiService.createProject(projectData);
      await loadProjects();

      // Set the new project as selected and go to settings
      setSelectedProject(newProject);
      setAppState('project-settings');
    } catch (err) {
      throw new Error(err instanceof Error ? err.message : 'Failed to create project');
    }
  };

  const handleProjectEdit = async (projectId: number, updates: { name?: string; path?: string; description?: string }) => {
    try {
      await ApiService.updateProject(projectId, updates);
      await loadProjects();
    } catch (err) {
      throw new Error(err instanceof Error ? err.message : 'Failed to update project');
    }
  };

  const handleProjectDelete = async (projectId: number) => {
    try {
      await ApiService.deleteProject(projectId);
      await loadProjects();
    } catch (err) {
      throw new Error(err instanceof Error ? err.message : 'Failed to delete project');
    }
  };

  // Render based on app state
  switch (appState) {
    case 'loading':
      return (
        <Box flexDirection="column" alignItems="center" justifyContent="center" height={10}>
          <LoadingSpinner text="Initializing AI CLI..." />
        </Box>
      );

    case 'error':
      return (
        <ErrorDisplay
          error={error}
          onRetry={initializeApp}
          onExit={() => process.exit(1)}
        />
      );

    case 'project-selection':
      return (
        <ProjectSelector
          projects={projects}
          onProjectSelect={handleProjectSelect}
          onProjectCreate={handleProjectCreate}
          onProjectEdit={handleProjectEdit}
          onProjectDelete={handleProjectDelete}
          onRefresh={loadProjects}
          onOpenSettings={handleOpenSettings}
        />
      );

    case 'chat':
      return selectedProject ? (
        <ClaudeChatInterface
          project={selectedProject}
          onBack={handleBackToProjects}
          onOpenSettings={handleOpenSettings}
        />
      ) : (
        <Box>
          <Text color="red">Error: No project selected</Text>
        </Box>
      );

    case 'settings':
      return (
        <SettingsInterface
          onBack={handleBackFromSettings}
          selectedProject={selectedProject}
        />
      );

    case 'project-settings':
      return selectedProject ? (
        <SettingsInterface
          onBack={handleBackFromProjectSettings}
          selectedProject={selectedProject}
        />
      ) : (
        <Box>
          <Text color="red">Error: No project selected for settings</Text>
        </Box>
      );

    default:
      return (
        <Box>
          <Text color="red">Unknown app state: {appState}</Text>
        </Box>
      );
  }
};