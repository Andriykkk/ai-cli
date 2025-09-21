import React from 'react';
import { useApp } from '../context/AppContext';

export function SettingEditor() {
  const { state } = useApp();

  // This is a placeholder - setting editor would be properly implemented
  // with forms for different setting types
  if (!state.currentEditSetting) {
    return null;
  }

  return (
    <div className="setting-editor">
      <div className="setting-editor-content">
        <h3>Edit Setting</h3>
        <div className="setting-editor-fields">
          {/* Dynamic fields would be rendered here */}
        </div>
        <div className="setting-editor-actions">
          <button className="btn btn-primary">Save</button>
          <button className="btn">Cancel</button>
        </div>
      </div>
    </div>
  );
}