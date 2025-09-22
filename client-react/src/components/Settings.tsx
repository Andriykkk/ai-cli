import React, { useEffect, useState } from 'react';
import { useApp } from '../context/AppContext';

export function Settings() {
  const { state, dispatch, api } = useApp();

  const isVisible = state.currentScreen === 'settings';

  useEffect(() => {
    if (isVisible) {
      loadAllSettings();
    }
  }, [isVisible, state.settingsType]);

  const loadAllSettings = async () => {
    try {
      dispatch({ type: 'SET_LOADING', payload: { loading: true, message: 'Loading settings...' } });

      // Load global settings
      const globalSettings = await api.getGlobalSettings();
      dispatch({ type: 'SET_GLOBAL_SETTINGS', payload: globalSettings });

      // Load project settings if project is selected
      if (state.currentProject) {
        const projectSettings = await api.getProjectSettings(state.currentProject.id);
        dispatch({ type: 'SET_PROJECT_SETTINGS', payload: projectSettings });
      }

    } catch (error) {
      dispatch({ type: 'SET_ERROR', payload: 'Failed to load settings: ' + (error as Error).message });
    } finally {
      dispatch({ type: 'SET_LOADING', payload: { loading: false } });
    }
  };

  const handleSwitchToGlobal = () => {
    dispatch({ type: 'SET_SETTINGS_TYPE', payload: 'global' });
    dispatch({ type: 'SET_SETTINGS_PATH', payload: [] });
  };

  const handleSwitchToProject = () => {
    if (!state.currentProject) {
      dispatch({ type: 'SET_ERROR', payload: 'No project selected. Please select a project first.' });
      return;
    }
    dispatch({ type: 'SET_SETTINGS_TYPE', payload: 'project' });
    dispatch({ type: 'SET_SETTINGS_PATH', payload: [] });
  };

  const handleBack = () => {
    if (state.settingsPath.length > 0) {
      // Navigate up one level in settings hierarchy
      const newPath = state.settingsPath.slice(0, -1);
      dispatch({ type: 'SET_SETTINGS_PATH', payload: newPath });
    } else {
      // Exit settings back to main screen
      const hasCurrentProject = !!state.currentProject;
      const targetScreen = hasCurrentProject ? 'chat' : 'projects';
      dispatch({ type: 'SET_SCREEN', payload: targetScreen });
    }
  };

  const handleReset = async () => {
    const settingsType = state.settingsType;
    const typeName = settingsType === 'global' ? 'global' : 'project';

    if (!window.confirm(`Are you sure you want to reset all ${typeName} settings to their default values?\n\nThis action cannot be undone.`)) {
      return;
    }

    try {
      dispatch({ type: 'SET_LOADING', payload: { loading: true, message: 'Resetting settings...' } });

      if (settingsType === 'global') {
        await api.resetGlobalSettings();
      } else if (state.currentProject) {
        await api.resetProjectSettings(state.currentProject.id);
      }

      // Reload settings
      await loadAllSettings();
    } catch (error) {
      dispatch({ type: 'SET_ERROR', payload: 'Failed to reset settings: ' + (error as Error).message });
    } finally {
      dispatch({ type: 'SET_LOADING', payload: { loading: false } });
    }
  };

  const handleSettingClick = (key: string, value: any) => {
    const isSettingValue = typeof value === 'object' && value.type;

    if (isSettingValue) {
      if (value.type === 'action') {
        // Handle action types
        handleActionClick(key, value);
      } else {
        // Edit this setting based on type
        if (value.type === 'selector' && value.options) {
          handleSelectorEdit(key, value);
        } else {
          // Use prompt for simple types
          const newValue = prompt(`Edit ${key} (${value.type}):`, value.value);
          if (newValue !== null) {
            updateSetting(key, newValue, value.type);
          }
        }
      }
    } else {
      // Navigate to category
      const newPath = [...state.settingsPath, key];
      dispatch({ type: 'SET_SETTINGS_PATH', payload: newPath });
    }
  };

  const handleSelectorEdit = (key: string, setting: any) => {
    const options = setting.options;
    const currentValue = setting.value;

    // Create a selection dialog
    const optionsText = options.map((opt: string, index: number) =>
      `${index + 1}. ${opt}${opt === currentValue ? ' (current)' : ''}`
    ).join('\n');

    const prompt_text = `Select ${key.replace('_', ' ')}:\n\n${optionsText}\n\nEnter number (1-${options.length}) or option name:`;
    const userInput = prompt(prompt_text, currentValue);

    if (userInput !== null && userInput.trim() !== '') {
      let selectedValue = userInput.trim();

      // Check if user entered a number
      const numberChoice = parseInt(selectedValue);
      if (!isNaN(numberChoice) && numberChoice >= 1 && numberChoice <= options.length) {
        selectedValue = options[numberChoice - 1];
      }

      // Validate the selection
      if (options.includes(selectedValue)) {
        updateSetting(key, selectedValue, setting.type);
      } else {
        alert(`Invalid selection. Please choose from: ${options.join(', ')}`);
      }
    }
  };

  const handleActionClick = async (key: string, action: any) => {
    if (key === 'clear_history' && state.settingsType === 'project' && state.currentProject) {
      if (!window.confirm(`Are you sure you want to clear all chat history for this project?\n\nThis action cannot be undone.`)) {
        return;
      }

      try {
        dispatch({ type: 'SET_LOADING', payload: { loading: true, message: 'Clearing chat history...' } });
        const result = await api.clearProjectChatHistory(state.currentProject.id);

        // Clear messages from the current state if we're in the same project
        dispatch({ type: 'SET_MESSAGES', payload: [] });

        // Show success message
        alert(`Success: ${result.message}`);
      } catch (error) {
        dispatch({ type: 'SET_ERROR', payload: 'Failed to clear chat history: ' + (error as Error).message });
      } finally {
        dispatch({ type: 'SET_LOADING', payload: { loading: false } });
      }
    }
  };

  const updateSetting = async (key: string, value: string, type: string) => {
    try {
      dispatch({ type: 'SET_LOADING', payload: { loading: true, message: 'Updating setting...' } });

      // Convert value to proper type
      let convertedValue: any = value;
      if (type === 'boolean') {
        convertedValue = value === 'true' || value.toLowerCase() === 'yes';
      } else if (type === 'number') {
        convertedValue = parseFloat(value);
      } else if (type === 'array' || type === 'object') {
        convertedValue = JSON.parse(value);
      }

      const settingsType = state.settingsType;
      const settingsPath = state.settingsPath;

      // Get existing settings to merge with
      const existingSettings = settingsType === 'global' 
        ? state.globalSettings 
        : state.projectSettings;

      // Deep clone existing settings
      const updatedSettings = JSON.parse(JSON.stringify(existingSettings || {}));

      // Navigate to the correct nested location and update the value
      const updatePath = [...settingsPath, key];
      let current = updatedSettings;

      for (let i = 0; i < updatePath.length - 1; i++) {
        if (!current[updatePath[i]]) {
          current[updatePath[i]] = {};
        }
        current = current[updatePath[i]];
      }
      current[updatePath[updatePath.length - 1]] = { value: convertedValue, type };

      // Send update to server
      if (settingsType === 'global') {
        await api.updateGlobalSettings(updatedSettings);
      } else if (state.currentProject) {
        await api.updateProjectSettings(state.currentProject.id, updatedSettings);
      }

      // Reload settings
      await loadAllSettings();
    } catch (error) {
      dispatch({ type: 'SET_ERROR', payload: 'Failed to update setting: ' + (error as Error).message });
    } finally {
      dispatch({ type: 'SET_LOADING', payload: { loading: false } });
    }
  };

  const renderSettingsContent = () => {
    // Get the base settings based on type
    const baseSettings = state.settingsType === 'global'
      ? state.globalSettings
      : state.projectSettings;

    if (!baseSettings || Object.keys(baseSettings).length === 0) {
      return (
        <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
          <p>No settings available</p>
          <p>Unable to load {state.settingsType} settings from server</p>
        </div>
      );
    }

    // Get current section based on path
    let currentSection = baseSettings;
    for (const path of state.settingsPath) {
      if (currentSection && typeof currentSection === 'object' && currentSection[path]) {
        currentSection = currentSection[path];
      } else {
        return (
          <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-secondary)' }}>
            <p>Settings section not found</p>
            <p>Path: {state.settingsPath.join(' > ')}</p>
          </div>
        );
      }
    }

    return (
      <div className="settings-list">
        {/* Back button if not at root */}
        {state.settingsPath.length > 0 && (
          <div
            className="setting-item category"
            onClick={() => {
              const newPath = state.settingsPath.slice(0, -1);
              dispatch({ type: 'SET_SETTINGS_PATH', payload: newPath });
            }}
          >
            <div className="setting-info">
              <span className="setting-label">← Back</span>
            </div>
            <div className="setting-value"></div>
          </div>
        )}

        {Object.entries(currentSection).map(([key, value]) => {
          const isSettingValue = typeof value === 'object' && value.type;

          return (
            <div
              key={key}
              className={`setting-item ${isSettingValue && value.type === 'action' ? 'setting-action' : ''}`}
              onClick={() => handleSettingClick(key, value)}
            >
              <div className="setting-info">
                <span className="setting-label">{key.replace('_', ' ')}</span>
                {isSettingValue && (
                  <span className="setting-type">({value.type})</span>
                )}
                {isSettingValue && value.type === 'selector' && value.options && (
                  <span className="setting-options">
                    Options: {value.options.join(', ')}
                  </span>
                )}
              </div>
              <div className="setting-value">
                {isSettingValue ? formatSettingValue(value) : '→'}
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  const formatSettingValue = (item: any) => {
    if (item.type === 'action') {
      return item.label || 'Execute';
    } else if (item.type === 'boolean') {
      return item.value ? 'Yes' : 'No';
    } else if (item.type === 'array' || item.type === 'object') {
      return JSON.stringify(item.value);
    } else {
      return String(item.value || '');
    }
  };

  const getBreadcrumb = () => {
    let breadcrumbText = state.settingsType === 'global' ? 'Global Settings' :
      `Project Settings (${state.currentProject?.name || 'none'})`;
    if (state.settingsPath.length > 0) {
      breadcrumbText += ' > ' + state.settingsPath.map(p => p.replace('_', ' ')).join(' > ');
    }
    return breadcrumbText;
  };

  if (!isVisible) {
    return null;
  }

  return (
    <div className="screen" id="settings-screen">
      <div className="settings-container">
        <div className="settings-header">
          <h2>Settings</h2>
          <div className="settings-breadcrumb">{getBreadcrumb()}</div>
          <div className="settings-type-switcher">
            <button
              className={`btn settings-type-btn ${state.settingsType === 'global' ? 'active' : ''}`}
              onClick={handleSwitchToGlobal}
            >
              Global Settings
            </button>
            <button
              className={`btn settings-type-btn ${state.settingsType === 'project' ? 'active' : ''}`}
              onClick={handleSwitchToProject}
              disabled={!state.currentProject}
            >
              {state.currentProject ?
                `Project Settings (${state.currentProject.name})` :
                'Project Settings (no project selected)'}
            </button>
          </div>
        </div>

        <div className="settings-content">
          <div className="settings-navigation">
            {renderSettingsContent()}
          </div>
        </div>

        <div className="settings-actions">
          <button className="btn btn-warning" onClick={handleReset}>
            Reset to Defaults
          </button>
          <button className="btn" onClick={handleBack}>
            {state.settingsPath.length > 0 ? 'Back to Settings' : 'Back'}
          </button>
        </div>
      </div>
    </div>
  );
}