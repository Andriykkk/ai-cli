// Tool calling types for streaming chat with AI
export interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, any>;
}

export interface ConversationStep {
  type: 'conversation_step' | 'error';
  state?: 'generating' | 'tool_approval' | 'tool_executing' | 'completed';
  content?: string;
  tool_calls?: ToolCall[];
  tool_results?: Array<{
    tool_call_id: string;
    name: string;
    content: string;
    success: boolean;
  }>;
  error?: string;
  timestamp: string;
}

export interface ToolApprovalRequest {
  project_id: number;
  approved_tools: string[];
  denied_tools: string[];
}