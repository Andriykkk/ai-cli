export interface Project {
  id: number;
  name: string;
  path: string;
  description?: string;
  memory_enabled: boolean;
  tools_enabled: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  thinking?: string;
  tool_calls?: ToolCall[];
  tool_results?: ToolResult[];
  needsApproval?: boolean; // Indicates this message needs tool approval
  sessionId?: string; // Session ID for tool approval
}

export interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, any>;
}

export interface ToolResult {
  tool_call_id: string;
  name: string;
  content: string;
  success: boolean;
  command?: string; // For run_command tools
}

export type ConversationState = 'idle' | 'generating' | 'tool_approval' | 'tool_executing';

export type Screen = 'projects' | 'chat' | 'settings';

export type SettingsType = 'global' | 'project';

export interface Setting {
  type: 'string' | 'number' | 'boolean' | 'array' | 'object';
  value: any;
  description?: string;
  options?: any[];
}

export interface AppState {
  // Navigation
  currentScreen: Screen;
  
  // Projects
  projects: Project[];
  currentProject: Project | null;
  
  // Chat
  messages: Message[];
  conversationState: ConversationState;
  currentInput: string;
  commandHistory: string[];
  historyIndex: number;
  sessionId: string | null;
  
  // Settings
  globalSettings: Record<string, any>;
  projectSettings: Record<string, any>;
  settingsType: SettingsType;
  settingsPath: string[];
  currentEditSetting: { key: string; value: Setting } | null;
  
  // UI State
  loading: boolean;
  loadingMessage: string;
  error: string | null;
  contextMenuProject: Project | null;
  editingProject: Project | null;
  
  // Server
  serverUrl: string;
  
  // Tool Approval
  pendingToolCalls: { content: string; toolCalls: ToolCall[]; sessionId: string } | null;
}

export interface APIClient {
  // Projects
  getProjects(): Promise<Project[]>;
  createProject(project: Omit<Project, 'id'>): Promise<Project>;
  updateProject(id: number, project: Partial<Project>): Promise<Project>;
  deleteProject(id: number): Promise<void>;
  
  // Chat
  getChatHistory(projectId: number, limit?: number): Promise<{ messages: Message[] }>;
  sendMessage(data: { message: string; project_id: number }, signal?: AbortSignal): Promise<ReadableStream>;
  approveTools(data: { approved: boolean; project_id: number }, signal?: AbortSignal): Promise<ReadableStream>;
  
  // Settings
  getGlobalSettings(): Promise<Record<string, any>>;
  updateGlobalSettings(settings: Record<string, any>): Promise<void>;
  resetGlobalSettings(): Promise<void>;
  getProjectSettings(projectId: number): Promise<Record<string, any>>;
  updateProjectSettings(projectId: number, settings: Record<string, any>): Promise<void>;
  resetProjectSettings(projectId: number): Promise<void>;
  
  // Health
  healthCheck(): Promise<boolean>;
}