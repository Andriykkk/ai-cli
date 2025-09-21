import React, { useState, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { Project } from '../types';

interface ProjectModalProps {
  isVisible: boolean;
  onClose: () => void;
  editingProject?: Project | null;
}

export function ProjectModal({ isVisible, onClose, editingProject }: ProjectModalProps) {
  const { state, dispatch, api } = useApp();
  const [formData, setFormData] = useState({
    name: '',
    path: '',
    description: '',
  });

  // Update form data when editing project changes
  useEffect(() => {
    if (editingProject) {
      setFormData({
        name: editingProject.name || '',
        path: editingProject.path || '',
        description: editingProject.description || '',
      });
    } else {
      setFormData({
        name: '',
        path: '',
        description: '',
      });
    }
  }, [editingProject]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.name || !formData.path) {
      dispatch({ type: 'SET_ERROR', payload: 'Name and path are required' });
      return;
    }

    try {
      const isEditing = editingProject && editingProject.id;
      const message = isEditing ? 'Updating project...' : 'Creating project...';
      dispatch({ type: 'SET_LOADING', payload: { loading: true, message } });
      
      let resultProject: Project;

      if (isEditing) {
        // Update existing project
        resultProject = await api.updateProject(editingProject.id, {
          name: formData.name,
          path: formData.path,
          description: formData.description || '',
          memory_enabled: editingProject.memory_enabled,
          tools_enabled: editingProject.tools_enabled,
        });

        // Update current project if it's the one being edited
        if (state.currentProject && state.currentProject.id === editingProject.id) {
          dispatch({ type: 'SET_CURRENT_PROJECT', payload: resultProject });
        }
      } else {
        // Create new project
        resultProject = await api.createProject({
          name: formData.name,
          path: formData.path,
          description: formData.description || '',
          memory_enabled: true,
          tools_enabled: true,
        });

        // Set as current project and go to settings
        dispatch({ type: 'SET_CURRENT_PROJECT', payload: resultProject });
        dispatch({ type: 'SET_SETTINGS_TYPE', payload: 'project' });
        dispatch({ type: 'SET_SETTINGS_PATH', payload: [] });
        dispatch({ type: 'SET_SCREEN', payload: 'settings' });
      }

      // Refresh projects list
      const projects = await api.getProjects();
      dispatch({ type: 'SET_PROJECTS', payload: projects });

      // Close modal
      onClose();
    } catch (error) {
      const action = isEditing ? 'update' : 'create';
      dispatch({ type: 'SET_ERROR', payload: `Failed to ${action} project: ` + (error as Error).message });
    } finally {
      dispatch({ type: 'SET_LOADING', payload: { loading: false } });
    }
  };

  const handleCancel = () => {
    onClose();
  };

  if (!isVisible) {
    return null;
  }

  const isEditing = editingProject && editingProject.id;

  return (
    <div className="modal">
      <div className="modal-content">
        <h3>{isEditing ? 'Edit Project' : 'Create New Project'}</h3>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="project-name">Project Name:</label>
            <input
              type="text"
              id="project-name"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="project-path">Project Path:</label>
            <input
              type="text"
              id="project-path"
              placeholder="/path/to/project"
              value={formData.path}
              onChange={(e) => setFormData({ ...formData, path: e.target.value })}
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="project-description">Description:</label>
            <textarea
              id="project-description"
              placeholder="Describe your project..."
              rows={3}
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            />
          </div>
          <div className="form-note">
            <p><strong>Note:</strong> Model provider and settings will be configured in project settings after creation.</p>
          </div>
          <div className="form-actions">
            <button type="submit" className="btn btn-primary">
              {isEditing ? 'Save Changes' : 'Create'}
            </button>
            <button type="button" className="btn" onClick={handleCancel}>Cancel</button>
          </div>
        </form>
      </div>
    </div>
  );
}