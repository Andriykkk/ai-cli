import React from 'react';
import { useApp } from '../context/AppContext';

export function LoadingOverlay() {
  const { state } = useApp();

  if (!state.loading) {
    return null;
  }

  return (
    <div className="loading-overlay">
      <div className="spinner"></div>
      <div className="loading-text">
        {state.loadingMessage || 'Loading...'}
      </div>
    </div>
  );
}