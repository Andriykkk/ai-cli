import React from 'react';
import { Header } from './components/Header';
import { ProjectSelection } from './components/ProjectSelection';
import { ChatInterface } from './components/ChatInterface';
import { Settings } from './components/Settings';
import { LoadingOverlay } from './components/LoadingOverlay';
import { ErrorToast } from './components/ErrorToast';
import { ContextMenu } from './components/ContextMenu';
import { SettingEditor } from './components/SettingEditor';
import { AppProvider } from './context/AppContext';
import './App.css';

export type Screen = 'projects' | 'chat' | 'settings';

function App() {
  return (
    <AppProvider>
      <div className="app">
        <Header />
        <main className="main">
          <ProjectSelection />
          <ChatInterface />
          <Settings />
        </main>
        
        {/* Global Components */}
        <LoadingOverlay />
        <ErrorToast />
        <ContextMenu />
        <SettingEditor />
      </div>
    </AppProvider>
  );
}

export default App;
