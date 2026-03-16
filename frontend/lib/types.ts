// TechCorp FTE — TypeScript Types

export type Channel = 'email' | 'whatsapp' | 'web_form';
export type TicketStatus = 'open' | 'processing' | 'resolved' | 'escalated';
export type TicketPriority = 'low' | 'medium' | 'high' | 'urgent';
export type TicketCategory = 'general' | 'technical' | 'billing' | 'bug_report' | 'feedback';
export type MessageRole = 'customer' | 'agent' | 'system';
export type AppMode = 'DEMO' | 'LIVE';

export interface Ticket {
  ticket_id: string;
  subject?: string;
  status: TicketStatus;
  priority: TicketPriority;
  category: TicketCategory;
  channel: Channel;
  customer_name?: string;
  customer_email?: string;
  created_at: string;
  updated_at?: string;
  mode: AppMode;
}

export interface Message {
  id: string;
  role: MessageRole;
  direction: 'inbound' | 'outbound';
  content: string;
  channel: Channel;
  created_at: string;
  delivery_status: 'pending' | 'sent' | 'delivered' | 'failed';
}

export interface TicketDetail extends Ticket {
  messages: Message[];
}

export interface SupportFormData {
  name: string;
  email: string;
  subject: string;
  category: TicketCategory;
  priority: TicketPriority;
  message: string;
}

export interface SupportFormResponse {
  ticket_id: string;
  conversation_id: string;
  status: string;
  channel: string;
  estimated_response: string;
  message: string;
  mode: AppMode;
}

export interface ChannelStats {
  channel: Channel;
  total_tickets: number;
  resolved: number;
  escalated: number;
  open: number;
  avg_resolution_minutes: number;
}

export interface DailyStats {
  total_tickets: number;
  resolved_tickets: number;
  escalated_tickets: number;
  open_tickets: number;
  avg_resolution_minutes: number;
  avg_sentiment: number;
  date: string;
  mode: AppMode;
}

export interface SentimentDataPoint {
  date: string;
  channel: Channel;
  avg_sentiment: number;
  conversation_count: number;
}

export interface Escalation {
  ticket_id: string;
  subject?: string;
  customer_name?: string;
  customer_email?: string;
  channel: Channel;
  priority: TicketPriority;
  reason?: string;
  escalated_at: string;
}

export interface HealthStatus {
  status: string;
  mode: AppMode;
  dry_run: boolean;
  version: string;
  timestamp: string;
  services: {
    database: string;
    kafka: string;
    anthropic: string;
  };
}

export interface AgentTestResponse {
  response: string;
  ticket_id: string;
  channel: Channel;
  escalated: boolean;
  sentiment_score?: number;
  tokens_used: number;
  latency_ms: number;
  tool_calls_count: number;
  mode: AppMode;
}
