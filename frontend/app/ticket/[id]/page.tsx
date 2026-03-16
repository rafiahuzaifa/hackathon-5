'use client';

import { useEffect, useState, useCallback } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { getTicketStatus } from '@/lib/api';
import type { TicketDetail, Message } from '@/lib/types';

const STATUS_CONFIG = {
  open: { label: 'Open', color: 'bg-blue-100 text-blue-700 border-blue-200' },
  processing: { label: 'Processing', color: 'bg-yellow-100 text-yellow-700 border-yellow-200' },
  resolved: { label: 'Resolved', color: 'bg-green-100 text-green-700 border-green-200' },
  escalated: { label: 'Escalated', color: 'bg-red-100 text-red-700 border-red-200' },
};

const CHANNEL_CONFIG = {
  email: { label: 'Email', icon: '✉️' },
  whatsapp: { label: 'WhatsApp', icon: '💬' },
  web_form: { label: 'Web Form', icon: '🌐' },
};

function MessageBubble({ message }: { message: Message }) {
  const isAgent = message.role === 'agent';
  const time = new Date(message.created_at).toLocaleTimeString('en-PK', {
    hour: '2-digit',
    minute: '2-digit',
  });

  return (
    <div className={`flex ${isAgent ? 'justify-start' : 'justify-end'} mb-4`}>
      <div className={`max-w-[80%] ${isAgent ? 'order-2' : 'order-1'}`}>
        <div className="flex items-center gap-2 mb-1">
          {isAgent && (
            <div className="w-6 h-6 bg-blue-600 rounded-full flex items-center justify-center flex-shrink-0">
              <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
          )}
          <span className="text-xs text-gray-400">
            {isAgent ? 'TechCorp AI Support' : 'You'} · {time}
          </span>
        </div>
        <div
          className={`rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap ${
            isAgent
              ? 'bg-white border border-gray-200 text-gray-800 shadow-sm rounded-tl-none'
              : 'bg-blue-600 text-white rounded-tr-none'
          }`}
        >
          {message.content}
        </div>
        <div className={`flex mt-1 ${isAgent ? 'justify-start' : 'justify-end'}`}>
          <span className="text-xs text-gray-400">
            {message.delivery_status === 'delivered' ? '✓✓' : '✓'}
          </span>
        </div>
      </div>
    </div>
  );
}

export default function TicketStatusPage() {
  const params = useParams();
  const ticketId = params.id as string;

  const [ticket, setTicket] = useState<TicketDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());

  const fetchTicket = useCallback(async () => {
    try {
      const data = await getTicketStatus(ticketId);
      setTicket(data);
      setLastUpdated(new Date());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ticket not found');
    } finally {
      setLoading(false);
    }
  }, [ticketId]);

  useEffect(() => {
    fetchTicket();

    // Auto-refresh every 10 seconds if not resolved
    const interval = setInterval(() => {
      if (ticket?.status !== 'resolved') {
        fetchTicket();
      }
    }, 10000);

    return () => clearInterval(interval);
  }, [fetchTicket, ticket?.status]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full mx-auto mb-3" />
          <p className="text-gray-500 text-sm">Loading ticket...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div className="bg-white border border-gray-200 rounded-2xl p-8 max-w-md w-full text-center">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <span className="text-2xl">❌</span>
          </div>
          <h2 className="text-xl font-bold text-gray-900 mb-2">Ticket Not Found</h2>
          <p className="text-gray-500 text-sm mb-6">{error}</p>
          <Link
            href="/support"
            className="bg-blue-600 text-white px-6 py-2.5 rounded-xl text-sm font-medium hover:bg-blue-700 transition-colors"
          >
            Submit New Request
          </Link>
        </div>
      </div>
    );
  }

  if (!ticket) return null;

  const statusCfg = STATUS_CONFIG[ticket.status] || STATUS_CONFIG.open;
  const channelCfg = CHANNEL_CONFIG[ticket.channel] || CHANNEL_CONFIG.web_form;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-7 h-7 bg-blue-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-xs">T</span>
            </div>
            <span className="font-semibold text-gray-900 text-sm">TechCorp Support</span>
          </Link>
          <span className="text-xs text-gray-400">
            Updated {lastUpdated.toLocaleTimeString()}
          </span>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 sm:px-6 py-6">
        {/* Ticket Info Card */}
        <div className="bg-white border border-gray-200 rounded-2xl p-5 mb-4">
          <div className="flex flex-wrap items-start justify-between gap-3 mb-3">
            <div>
              <h1 className="text-lg font-bold text-gray-900">
                {ticket.subject || 'Support Request'}
              </h1>
              <p className="text-xs text-gray-400 mt-0.5 font-mono">
                #{ticket.ticket_id.slice(0, 8)}
              </p>
            </div>

            <div className="flex items-center gap-2 flex-wrap">
              {/* Status badge */}
              <span
                className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-semibold border ${statusCfg.color}`}
              >
                {ticket.status === 'processing' && (
                  <span className="w-1.5 h-1.5 bg-yellow-500 rounded-full animate-pulse" />
                )}
                {statusCfg.label}
              </span>

              {/* Channel badge */}
              <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
                {channelCfg.icon} {channelCfg.label}
              </span>

              {/* Priority badge */}
              <span
                className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${
                  ticket.priority === 'urgent'
                    ? 'bg-red-100 text-red-700'
                    : ticket.priority === 'high'
                    ? 'bg-orange-100 text-orange-700'
                    : ticket.priority === 'medium'
                    ? 'bg-yellow-50 text-yellow-700'
                    : 'bg-gray-100 text-gray-600'
                }`}
              >
                {ticket.priority.charAt(0).toUpperCase() + ticket.priority.slice(1)} Priority
              </span>
            </div>
          </div>

          <div className="text-xs text-gray-500 flex gap-4">
            <span>Created: {new Date(ticket.created_at).toLocaleString('en-PK')}</span>
            {ticket.customer_name && <span>Customer: {ticket.customer_name}</span>}
          </div>
        </div>

        {/* AI Notice */}
        <div className="bg-blue-50 border border-blue-100 rounded-xl p-3 mb-4 flex items-center gap-2">
          <svg className="w-4 h-4 text-blue-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
          <p className="text-xs text-blue-700">
            This conversation is being handled by TechCorp AI Support. For human assistance,
            reply with &quot;human&quot; or visit during business hours (9am–6pm PKR).
          </p>
        </div>

        {/* Conversation */}
        <div className="bg-white border border-gray-200 rounded-2xl p-4 sm:p-6">
          {ticket.messages.length === 0 ? (
            <div className="text-center py-12">
              <div className="animate-spin w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full mx-auto mb-3" />
              <p className="text-gray-500 text-sm">AI is processing your request...</p>
            </div>
          ) : (
            <div>
              {ticket.messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
              ))}

              {ticket.status === 'processing' && (
                <div className="flex justify-start mb-4">
                  <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-none px-4 py-3 shadow-sm flex items-center gap-2">
                    <div className="flex gap-1">
                      {[0, 0.2, 0.4].map((delay) => (
                        <span
                          key={delay}
                          className="w-2 h-2 bg-gray-400 rounded-full animate-pulse-dot"
                          style={{ animationDelay: `${delay}s` }}
                        />
                      ))}
                    </div>
                    <span className="text-xs text-gray-500">AI is typing...</span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="mt-4 flex gap-3">
          <Link
            href="/support"
            className="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium py-2.5 px-4 rounded-xl text-sm text-center transition-colors"
          >
            New Request
          </Link>
          <button
            onClick={fetchTicket}
            className="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-medium py-2.5 px-4 rounded-xl text-sm transition-colors"
          >
            Refresh
          </button>
        </div>

        <p className="text-xs text-center text-gray-400 mt-3">
          Auto-refreshes every 10 seconds · {ticket.mode === 'demo' ? '🟡 DEMO mode' : '🟢 LIVE mode'}
        </p>
      </main>
    </div>
  );
}
