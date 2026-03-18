// TechCorp FTE — API Client
import type {
  AgentTestResponse,
  ChannelStats,
  DailyStats,
  Escalation,
  HealthStatus,
  SentimentDataPoint,
  SupportFormData,
  SupportFormResponse,
  Ticket,
  TicketDetail,
} from './types';

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  (typeof window !== 'undefined' ? '' : 'http://localhost:8000');

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function fetchApi<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const url = `${API_URL}${path}`;
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => 'Unknown error');
    throw new ApiError(res.status, text);
  }

  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------
export async function getHealth(): Promise<HealthStatus> {
  return fetchApi<HealthStatus>('/health');
}

// ---------------------------------------------------------------------------
// Support
// ---------------------------------------------------------------------------
export async function submitSupportForm(
  data: SupportFormData,
): Promise<SupportFormResponse> {
  return fetchApi<SupportFormResponse>('/support/submit', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function getTicketStatus(ticketId: string): Promise<TicketDetail> {
  return fetchApi<TicketDetail>(`/support/ticket/${ticketId}`);
}

export async function listTickets(params?: {
  status?: string;
  channel?: string;
  limit?: number;
  offset?: number;
}): Promise<{ tickets: Ticket[]; total: number; mode: string }> {
  const query = new URLSearchParams();
  if (params?.status) query.set('status', params.status);
  if (params?.channel) query.set('channel', params.channel);
  if (params?.limit) query.set('limit', String(params.limit));
  if (params?.offset) query.set('offset', String(params.offset));
  const qs = query.toString() ? `?${query.toString()}` : '';
  return fetchApi(`/support/tickets${qs}`);
}

// ---------------------------------------------------------------------------
// Metrics
// ---------------------------------------------------------------------------
export async function getChannelMetrics(
  days = 7,
): Promise<{ channels: ChannelStats[]; days: number; mode: string }> {
  return fetchApi(`/metrics/channels?days=${days}`);
}

export async function getDailyStats(): Promise<DailyStats> {
  return fetchApi<DailyStats>('/metrics/daily');
}

export async function getSentimentTrends(
  days = 7,
): Promise<{ data: SentimentDataPoint[]; days: number; mode: string }> {
  return fetchApi(`/metrics/sentiment?days=${days}`);
}

// ---------------------------------------------------------------------------
// Admin
// ---------------------------------------------------------------------------
export async function switchMode(
  dryRun: boolean,
): Promise<{ current_mode: string; message: string }> {
  return fetchApi('/admin/mode', {
    method: 'POST',
    body: JSON.stringify({ dry_run: dryRun }),
  });
}

export async function seedDemoData(): Promise<{
  status: string;
  message: string;
}> {
  return fetchApi('/admin/seed', { method: 'POST' });
}

export async function getEscalations(): Promise<{
  escalations: Escalation[];
  total: number;
  mode: string;
}> {
  return fetchApi('/admin/escalations');
}

// ---------------------------------------------------------------------------
// Agent Test
// ---------------------------------------------------------------------------
export async function testAgent(
  message: string,
  channel = 'web_form',
): Promise<AgentTestResponse> {
  return fetchApi<AgentTestResponse>('/agent/test', {
    method: 'POST',
    body: JSON.stringify({ message, channel }),
  });
}
