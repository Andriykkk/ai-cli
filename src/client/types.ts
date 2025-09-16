export interface Project {
  id: number;
  name: string;
  path: string;
  description: string;
  model_provider: string;
  model_name: string;
  created_at: string;
  last_used?: string;
  memory_enabled: boolean;
  tools_enabled: boolean;
}

export interface ProjectCreate {
  name: string;
  path: string;
  description?: string;
}

export interface ProjectUpdate {
  name?: string;
  path?: string;
  description?: string;
}

export interface ChatMessage {
  message: string;
  project_id: number;
}

export interface ChatResponse {
  response: string;
  timestamp: string;
}

export type AppState = 'project-selection' | 'chat' | 'settings' | 'project-settings' | 'loading' | 'error';

export interface AppContext {
  projects: Project[];
  selectedProject?: Project;
  appState: AppState;
  error?: string;
}

export interface GlobalSettings {
  config_name: string;
  config_data: any;
}

export interface ProjectSettings {
  project_id: number;
  config_data: any;
}