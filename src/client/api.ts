import axios from 'axios';
import type { Project, ProjectCreate, ProjectUpdate, ChatMessage, ChatResponse, GlobalSettings, ProjectSettings } from './types';
import type { ConversationStep, ToolApprovalRequest } from './tool-types';

interface ChatHistoryMessage {
  id: number;
  project_id: number;
  message: string;
  response: string;
  timestamp: string;
}

interface ChatHistoryResponse {
  messages: ChatHistoryMessage[];
  total_count: number;
  project_id: number;
}

const API_BASE_URL = process.env.AI_CLI_SERVER_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

export class ApiService {
  // Health check
  static async health(): Promise<{ status: string; timestamp: string }> {
    const response = await api.get('/health');
    return response.data;
  }

  // Project management
  static async getProjects(): Promise<Project[]> {
    const response = await api.get('/projects');
    return response.data;
  }

  static async createProject(project: ProjectCreate): Promise<Project> {
    const response = await api.post('/projects', project);
    return response.data;
  }

  static async updateProject(projectId: number, update: ProjectUpdate): Promise<Project> {
    const response = await api.put(`/projects/${projectId}`, update);
    return response.data;
  }

  static async deleteProject(projectId: number): Promise<void> {
    await api.delete(`/projects/${projectId}`);
  }

  static async useProject(projectId: number): Promise<void> {
    await api.post(`/projects/${projectId}/use`);
  }

  // Chat
  static async sendMessage(message: ChatMessage, signal?: AbortSignal): Promise<ChatResponse> {
    const response = await api.post('/chat', message, { signal });
    return response.data;
  }

  // Global Settings
  static async getGlobalSettings(): Promise<any> {
    const response = await api.get('/settings/global');
    return response.data;
  }

  static async updateGlobalSettings(settings: GlobalSettings): Promise<void> {
    await api.put('/settings/global', settings);
  }

  static async getDefaultGlobalSettings(): Promise<any> {
    const response = await api.get('/settings/global/defaults');
    return response.data;
  }

  static async resetGlobalSettings(): Promise<void> {
    await api.post('/settings/global/reset');
  }

  // Project Settings
  static async getProjectSettings(projectId: number): Promise<any> {
    const response = await api.get(`/settings/projects/${projectId}`);
    return response.data;
  }

  static async updateProjectSettings(projectId: number, settings: ProjectSettings): Promise<void> {
    await api.put(`/settings/projects/${projectId}`, settings);
  }

  static async getDefaultProjectSettings(projectId: number): Promise<any> {
    const response = await api.get(`/settings/projects/${projectId}/defaults`);
    return response.data;
  }

  static async resetProjectSettings(projectId: number): Promise<void> {
    await api.post(`/settings/projects/${projectId}/reset`);
  }

  // Chat Memory
  static async getChatHistory(projectId: number, limit?: number): Promise<ChatHistoryResponse> {
    const params = limit ? `?limit=${limit}` : '';
    const response = await api.get(`/projects/${projectId}/chat/history${params}`);
    return response.data;
  }

  static async getRecentChatHistory(projectId: number, limit: number = 50): Promise<ChatHistoryResponse> {
    const response = await api.get(`/projects/${projectId}/chat/history/recent?limit=${limit}`);
    return response.data;
  }

  static async clearChatHistory(projectId: number): Promise<{ message: string; deleted_count: number }> {
    const response = await api.delete(`/projects/${projectId}/chat/history`);
    return response.data;
  }

  static async getChatMessageCount(projectId: number): Promise<{ count: number }> {
    const response = await api.get(`/projects/${projectId}/chat/history/count`);
    return response.data;
  }

  static async searchChatHistory(projectId: number, query: string, limit: number = 20): Promise<{ messages: ChatHistoryMessage[] }> {
    const response = await api.post(`/projects/${projectId}/chat/history/search`, {
      query,
      limit
    });
    return response.data;
  }

  // Server connection test
  static async testConnection(): Promise<boolean> {
    try {
      await this.health();
      return true;
    } catch {
      return false;
    }
  }
}