import axios from 'axios';
import type { Project, ProjectCreate, ProjectUpdate, ChatMessage, ChatResponse, GlobalSettings, ProjectSettings } from './types';

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
    const response = await api.get(`/projects/${projectId}/settings`);
    return response.data;
  }

  static async updateProjectSettings(projectId: number, settings: ProjectSettings): Promise<void> {
    await api.put(`/projects/${projectId}/settings`, settings);
  }

  static async getDefaultProjectSettings(projectId: number): Promise<any> {
    const response = await api.get(`/projects/${projectId}/settings/defaults`);
    return response.data;
  }

  static async resetProjectSettings(projectId: number): Promise<void> {
    await api.post(`/projects/${projectId}/settings/reset`);
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