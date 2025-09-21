import React from 'react';
import { useApp } from '../context/AppContext';

export function ContextMenu() {
  const { state, dispatch } = useApp();

  // This is a placeholder - context menu visibility would be managed differently
  // in a real implementation with proper positioning
  if (!state.contextMenuProject) {
    return null;
  }

  return (
    <div className="context-menu">
      <div className="context-menu-item">
        <span>✏️ Edit Project</span>
      </div>
      <div className="context-menu-item">
        <span>📋 Duplicate Project</span>
      </div>
      <div className="context-menu-separator"></div>
      <div className="context-menu-item danger">
        <span>🗑️ Delete Project</span>
      </div>
    </div>
  );
}