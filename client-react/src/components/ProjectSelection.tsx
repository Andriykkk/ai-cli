import React, { useState, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { Project } from '../types';
import { ProjectModal } from './ProjectModal';

export function ProjectSelection() {
  const { state, dispatch, api } = useApp();
  const [showModal, setShowModal] = useState(false);
  const [contextMenu, setContextMenu] = useState<{
    x: number;
    y: number;
    project: Project;
  } | null>(null);

  const isVisible = state.currentScreen === 'projects';

  const handleProjectOpen = (project: Project) => {
    dispatch({ type: 'SET_CURRENT_PROJECT', payload: project });
    dispatch({ type: 'SET_SCREEN', payload: 'chat' });
  };

  const handleProjectMenu = (e: React.MouseEvent, project: Project) => {
    e.stopPropagation();
    setContextMenu({
      x: e.pageX,
      y: e.pageY,
      project,
    });
  };

  const handleNewProject = () => {
    setShowModal(true);
  };

  const handleRefresh = async () => {
    try {
      dispatch({ type: 'SET_LOADING', payload: { loading: true, message: 'Refreshing projects...' } });
      const projects = await api.getProjects();
      dispatch({ type: 'SET_PROJECTS', payload: projects });
    } catch (error) {
      dispatch({ type: 'SET_ERROR', payload: 'Failed to refresh projects: ' + (error as Error).message });
    } finally {
      dispatch({ type: 'SET_LOADING', payload: { loading: false } });
    }
  };

  const handleEditProject = (project: Project) => {
    setContextMenu(null);
    dispatch({ type: 'SET_EDITING_PROJECT', payload: project });
    setShowModal(true);
  };

  const handleDuplicateProject = (project: Project) => {
    setContextMenu(null);
    // Create a copy with modified name
    const duplicatedProject = {
      ...project,
      name: `${project.name} (Copy)`,
      id: undefined as any // Remove ID so it creates new
    };
    dispatch({ type: 'SET_EDITING_PROJECT', payload: duplicatedProject });
    setShowModal(true);
  };

  const handleDeleteProject = async (project: Project) => {
    setContextMenu(null);
    
    if (!window.confirm(`Are you sure you want to delete the project "${project.name}"?\n\nThis action cannot be undone and will delete all chat history for this project.`)) {
      return;
    }

    try {
      dispatch({ type: 'SET_LOADING', payload: { loading: true, message: 'Deleting project...' } });
      await api.deleteProject(project.id);

      // Clear current project if it was the deleted one
      if (state.currentProject && state.currentProject.id === project.id) {
        dispatch({ type: 'SET_CURRENT_PROJECT', payload: null });
      }

      // Refresh projects list
      const projects = await api.getProjects();
      dispatch({ type: 'SET_PROJECTS', payload: projects });
    } catch (error) {
      dispatch({ type: 'SET_ERROR', payload: 'Failed to delete project: ' + (error as Error).message });
    } finally {
      dispatch({ type: 'SET_LOADING', payload: { loading: false } });
    }
  };

  // Close context menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (contextMenu && !(e.target as Element).closest('.context-menu')) {
        setContextMenu(null);
      }
    };

    if (contextMenu) {
      document.addEventListener('click', handleClickOutside);
      return () => document.removeEventListener('click', handleClickOutside);
    }
  }, [contextMenu]);

  if (!isVisible) {
    return null;
  }

  return (
    <div className="screen" id="project-selection">
      <div className="project-selector">
        <h2>Select or Create Project</h2>
        <div className="project-list">
          {state.projects.length === 0 ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
              <p>No projects found</p>
              <p>Click "New Project" to create your first project</p>
            </div>
          ) : (
            state.projects.map(project => (
              <div key={project.id} className="project-item">
                <div className="project-info">
                  <h3 className="project-name">{project.name}</h3>
                  <p className="project-path">{project.path}</p>
                  {project.description && (
                    <p className="project-description">{project.description}</p>
                  )}
                </div>
                <div className="project-actions">
                  <button 
                    className="btn btn-primary" 
                    onClick={() => handleProjectOpen(project)}
                  >
                    Open Chat
                  </button>
                  <button 
                    className="btn project-menu-btn" 
                    onClick={(e) => handleProjectMenu(e, project)}
                  >
                    ⋮
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
        <div className="project-actions">
          <button className="btn btn-primary" onClick={handleNewProject}>
            + New Project
          </button>
          <button className="btn" onClick={handleRefresh}>
            🔄 Refresh
          </button>
        </div>
      </div>

      {/* Context Menu */}
      {contextMenu && (
        <div 
          className="context-menu"
          style={{ 
            position: 'fixed',
            left: contextMenu.x,
            top: contextMenu.y,
            zIndex: 1000 
          }}
        >
          <div className="context-menu-item" onClick={() => handleEditProject(contextMenu.project)}>
            <span>✏️ Edit Project</span>
          </div>
          <div className="context-menu-item" onClick={() => handleDuplicateProject(contextMenu.project)}>
            <span>📋 Duplicate Project</span>
          </div>
          <div className="context-menu-separator"></div>
          <div className="context-menu-item danger" onClick={() => handleDeleteProject(contextMenu.project)}>
            <span>🗑️ Delete Project</span>
          </div>
        </div>
      )}

      {/* Project Modal */}
      {showModal && (
        <ProjectModal 
          isVisible={showModal}
          onClose={() => {
            setShowModal(false);
            dispatch({ type: 'SET_EDITING_PROJECT', payload: null });
          }}
          editingProject={state.editingProject}
        />
      )}
    </div>
  );
}