import React from 'react';
import { useApp } from '../context/AppContext';

export function ErrorToast() {
  const { state, dispatch } = useApp();

  const handleClose = () => {
    dispatch({ type: 'SET_ERROR', payload: null });
  };

  if (!state.error) {
    return null;
  }

  return (
    <div className="error-toast">
      <span className="error-message">{state.error}</span>
      <button className="error-close" onClick={handleClose}>
        ×
      </button>
    </div>
  );
}