import axios from 'axios';
import type { Project, ProjectCreate, ProjectUpdate, ChatMessage, ChatResponse } from './types';

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