import React from 'react';
import { useApp } from '../context/AppContext';

export function Header() {
  const { state, dispatch } = useApp();

  const handleHomeClick = () => {
    dispatch({ type: 'SET_SCREEN', payload: 'projects' });
  };

  const handleSettingsClick = () => {
    dispatch({ type: 'SET_SCREEN', payload: 'settings' });
  };

  return (
    <header className="header" style={{ display: 'flex', justifyContent: 'space-between' }}>
      <div className="header-left" style={{
        flexGrow: 1
      }}>
        <h1>AI CLI Web</h1>
        <button
          className="header-nav-btn"
          onClick={handleHomeClick}
          title="Back to Projects (Ctrl+H)"
        >
          🏠 Projects
        </button>
      </div>
      <div className="project-info">
        <span className="project-name">
          {state.currentProject ? state.currentProject.name : 'No Project Selected'}
        </span>
        <button
          className="settings-btn"
          onClick={handleSettingsClick}
          title="Settings (Ctrl+S)"
        >
          ⚙️ Settings
        </button>
      </div>
    </header>
  );
}