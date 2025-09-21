import React, { createContext, useContext, useReducer, useEffect, ReactNode } from 'react';
import { AppState, Screen, Project, Message, ConversationState, SettingsType } from '../types';
import { APIClient } from '../services/api';

interface AppContextType {
  state: AppState;
  dispatch: React.Dispatch<AppAction>;
  api: APIClient;
}

type AppAction =
  | { type: 'SET_SCREEN'; payload: Screen }
  | { type: 'SET_PROJECTS'; payload: Project[] }
  | { type: 'SET_CURRENT_PROJECT'; payload: Project | null }
  | { type: 'SET_MESSAGES'; payload: Message[] }
  | { type: 'ADD_MESSAGE'; payload: Message }
  | { type: 'SET_CONVERSATION_STATE'; payload: ConversationState }
  | { type: 'SET_CURRENT_INPUT'; payload: string }
  | { type: 'SET_COMMAND_HISTORY'; payload: string[] }
  | { type: 'SET_HISTORY_INDEX'; payload: number }
  | { type: 'SET_GLOBAL_SETTINGS'; payload: Record<string, any> }
  | { type: 'SET_PROJECT_SETTINGS'; payload: Record<string, any> }
  | { type: 'SET_SETTINGS_TYPE'; payload: SettingsType }
  | { type: 'SET_SETTINGS_PATH'; payload: string[] }
  | { type: 'SET_CURRENT_EDIT_SETTING'; payload: { key: string; value: any } | null }
  | { type: 'SET_LOADING'; payload: { loading: boolean; message?: string } }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'SET_CONTEXT_MENU_PROJECT'; payload: Project | null }
  | { type: 'SET_EDITING_PROJECT'; payload: Project | null }
  | { type: 'SET_SERVER_URL'; payload: string }
  | { type: 'SET_SESSION_ID'; payload: string | null }
  | { type: 'SET_PENDING_TOOL_CALLS'; payload: { content: string; toolCalls: any[]; sessionId: string } | null };

const initialState: AppState = {
  currentScreen: 'projects',
  projects: [],
  currentProject: null,
  messages: [],
  conversationState: 'idle',
  currentInput: '',
  commandHistory: JSON.parse(localStorage.getItem('commandHistory') || '[]'),
  historyIndex: -1,
  sessionId: null,
  globalSettings: {},
  projectSettings: {},
  settingsType: 'global',
  settingsPath: [],
  currentEditSetting: null,
  loading: false,
  loadingMessage: '',
  error: null,
  contextMenuProject: null,
  editingProject: null,
  serverUrl: localStorage.getItem('serverUrl') || 'http://localhost:8000',
  pendingToolCalls: null,
};

function appReducer(state: AppState, action: AppAction): AppState {
  switch (action.type) {
    case 'SET_SCREEN':
      return { ...state, currentScreen: action.payload };
    case 'SET_PROJECTS':
      return { ...state, projects: action.payload };
    case 'SET_CURRENT_PROJECT':
      return { ...state, currentProject: action.payload };
    case 'SET_MESSAGES':
      return { ...state, messages: action.payload };
    case 'ADD_MESSAGE':
      return { ...state, messages: [...state.messages, action.payload] };
    case 'SET_CONVERSATION_STATE':
      return { ...state, conversationState: action.payload };
    case 'SET_CURRENT_INPUT':
      return { ...state, currentInput: action.payload };
    case 'SET_COMMAND_HISTORY':
      localStorage.setItem('commandHistory', JSON.stringify(action.payload));
      return { ...state, commandHistory: action.payload };
    case 'SET_HISTORY_INDEX':
      return { ...state, historyIndex: action.payload };
    case 'SET_GLOBAL_SETTINGS':
      return { ...state, globalSettings: action.payload };
    case 'SET_PROJECT_SETTINGS':
      return { ...state, projectSettings: action.payload };
    case 'SET_SETTINGS_TYPE':
      return { ...state, settingsType: action.payload };
    case 'SET_SETTINGS_PATH':
      return { ...state, settingsPath: action.payload };
    case 'SET_CURRENT_EDIT_SETTING':
      return { ...state, currentEditSetting: action.payload };
    case 'SET_LOADING':
      return { 
        ...state, 
        loading: action.payload.loading,
        loadingMessage: action.payload.message || ''
      };
    case 'SET_ERROR':
      return { ...state, error: action.payload };
    case 'SET_CONTEXT_MENU_PROJECT':
      return { ...state, contextMenuProject: action.payload };
    case 'SET_EDITING_PROJECT':
      return { ...state, editingProject: action.payload };
    case 'SET_SERVER_URL':
      localStorage.setItem('serverUrl', action.payload);
      return { ...state, serverUrl: action.payload };
    case 'SET_SESSION_ID':
      return { ...state, sessionId: action.payload };
    case 'SET_PENDING_TOOL_CALLS':
      return { ...state, pendingToolCalls: action.payload };
    default:
      return state;
  }
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export function AppProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(appReducer, initialState);
  const api = React.useMemo(() => new APIClient(state.serverUrl), [state.serverUrl]);

  // Load initial data
  useEffect(() => {
    const loadInitialData = async () => {
      try {
        dispatch({ type: 'SET_LOADING', payload: { loading: true, message: 'Loading projects...' } });
        const projects = await api.getProjects();
        dispatch({ type: 'SET_PROJECTS', payload: projects });
      } catch (error) {
        dispatch({ type: 'SET_ERROR', payload: 'Failed to load projects: ' + (error as Error).message });
      } finally {
        dispatch({ type: 'SET_LOADING', payload: { loading: false } });
      }
    };

    loadInitialData();
  }, [api]);

  return (
    <AppContext.Provider value={{ state, dispatch, api }}>
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const context = useContext(AppContext);
  if (context === undefined) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
}