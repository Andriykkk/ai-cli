import { Project, Message } from '../types';

export class APIClient {
  public baseUrl: string;
  
  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      ...options,
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  }

  // Projects
  async getProjects(): Promise<Project[]> {
    return this.request<Project[]>('/projects');
  }

  async createProject(project: Omit<Project, 'id'>): Promise<Project> {
    return this.request<Project>('/projects', {
      method: 'POST',
      body: JSON.stringify(project),
    });
  }

  async updateProject(id: number, project: Partial<Project>): Promise<Project> {
    return this.request<Project>(`/projects/${id}`, {
      method: 'PUT',
      body: JSON.stringify(project),
    });
  }

  async deleteProject(id: number): Promise<void> {
    await this.request<void>(`/projects/${id}`, {
      method: 'DELETE',
    });
  }

  // Chat
  async getChatHistory(projectId: number, limit: number = 50): Promise<{ messages: Message[] }> {
    return this.request<{ messages: Message[] }>(`/projects/${projectId}/chat/history?limit=${limit}`);
  }

  async sendMessage(data: { message: string; project_id: number }, signal?: AbortSignal): Promise<ReadableStream> {
    const response = await fetch(`${this.baseUrl}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
      signal,
    });

    if (!response.ok) {
      const errorText = await response.text().catch(() => 'Unknown error');
      throw new Error(`HTTP ${response.status}: ${response.statusText} - ${errorText}`);
    }

    return response.body!;
  }

  async approveTools(data: { approved_tools: string[]; denied_tools: string[]; project_id: number; session_id: string }, signal?: AbortSignal): Promise<ReadableStream> {
    const response = await fetch(`${this.baseUrl}/chat/tool-approval`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
      signal,
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return response.body!;
  }

  // Settings
  async getGlobalSettings(): Promise<Record<string, any>> {
    return this.request<Record<string, any>>('/settings/global');
  }

  async updateGlobalSettings(settings: Record<string, any>): Promise<void> {
    await this.request<void>('/settings/global', {
      method: 'PUT',
      body: JSON.stringify({ config_data: settings }),
    });
  }

  async resetGlobalSettings(): Promise<void> {
    await this.request<void>('/settings/global/reset', {
      method: 'POST',
      body: JSON.stringify({}),
    });
  }

  async getProjectSettings(projectId: number): Promise<Record<string, any>> {
    return this.request<Record<string, any>>(`/settings/projects/${projectId}`);
  }

  async updateProjectSettings(projectId: number, settings: Record<string, any>): Promise<void> {
    await this.request<void>(`/settings/projects/${projectId}`, {
      method: 'PUT',
      body: JSON.stringify({ config_data: settings }),
    });
  }

  async resetProjectSettings(projectId: number): Promise<void> {
    await this.request<void>(`/settings/projects/${projectId}/reset`, {
      method: 'POST',
      body: JSON.stringify({}),
    });
  }

  async clearProjectChatHistory(projectId: number): Promise<{ message: string; deleted_count: number }> {
    return this.request<{ message: string; deleted_count: number }>(`/settings/projects/${projectId}/actions/clear_history`, {
      method: 'POST',
      body: JSON.stringify({}),
    });
  }

  // Health
  async healthCheck(): Promise<boolean> {
    try {
      await this.request<void>('/health');
      return true;
    } catch {
      return false;
    }
  }

  // Utility for parsing streaming responses
  async parseStreamingResponse(
    stream: ReadableStream,
    onData: (data: any) => void,
    onError: (error: Error) => void,
    onComplete: () => void
  ) {
    const reader = stream.getReader();
    const decoder = new TextDecoder();

    try {
      while (true) {
        const { done, value } = await reader.read();
        
        if (done) {
          onComplete();
          break;
        }

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              onData(data);
            } catch (e) {
              console.warn('Failed to parse stream data:', line);
            }
          }
        }
      }
    } catch (error) {
      onError(error as Error);
    } finally {
      reader.releaseLock();
    }
  }
}