'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  LineChart,
  Line,
  ResponsiveContainer,
} from 'recharts';
import {
  getChannelMetrics,
  getDailyStats,
  getSentimentTrends,
  listTickets,
  getEscalations,
  seedDemoData,
} from '@/lib/api';
import ModeToggle from '@/components/ModeToggle';
import ChannelBadge from '@/components/ChannelBadge';
import TicketStatusBadge from '@/components/TicketStatus';
import type {
  ChannelStats,
  DailyStats,
  Escalation,
  Ticket,
  SentimentDataPoint,
} from '@/lib/types';

export default function DashboardPage() {
  const [dailyStats, setDailyStats] = useState<DailyStats | null>(null);
  const [channelStats, setChannelStats] = useState<ChannelStats[]>([]);
  const [sentimentData, setSentimentData] = useState<SentimentDataPoint[]>([]);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [escalations, setEscalations] = useState<Escalation[]>([]);
  const [mode, setMode] = useState<'DEMO' | 'LIVE'>('DEMO');
  const [loading, setLoading] = useState(true);
  const [seeding, setSeeding] = useState(false);
  const [seedMsg, setSeedMsg] = useState('');
  const [lastRefresh, setLastRefresh] = useState(new Date());

  const loadData = useCallback(async () => {
    try {
      const [daily, channels, sentiment, ticketList, escList] = await Promise.all([
        getDailyStats(),
        getChannelMetrics(7),
        getSentimentTrends(7),
        listTickets({ limit: 15 }),
        getEscalations(),
      ]);

      setDailyStats(daily);
      setChannelStats(channels.channels || []);
      setSentimentData(sentiment.data || []);
      setTickets(ticketList.tickets || []);
      setEscalations(escList.escalations || []);
      setMode((daily.mode as 'DEMO' | 'LIVE') || 'DEMO');
      setLastRefresh(new Date());
    } catch (err) {
      console.error('Dashboard load error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, [loadData]);

  async function handleSeed() {
    setSeeding(true);
    setSeedMsg('');
    try {
      const result = await seedDemoData();
      setSeedMsg(result.message || 'Data seeded successfully');
      await loadData();
    } catch {
      setSeedMsg('Seed failed — check backend logs');
    } finally {
      setSeeding(false);
      setTimeout(() => setSeedMsg(''), 4000);
    }
  }

  // Prepare chart data
  const channelChartData = channelStats.map((c) => ({
    name: c.channel === 'web_form' ? 'Web Form' : c.channel.charAt(0).toUpperCase() + c.channel.slice(1),
    Total: c.total_tickets,
    Resolved: c.resolved,
    Escalated: c.escalated,
    Open: c.open,
  }));

  // Aggregate sentiment by date
  const sentimentByDate: Record<string, { date: string; avg: number; count: number }> = {};
  sentimentData.forEach((d) => {
    if (!sentimentByDate[d.date]) {
      sentimentByDate[d.date] = { date: d.date, avg: 0, count: 0 };
    }
    sentimentByDate[d.date].avg += d.avg_sentiment;
    sentimentByDate[d.date].count += 1;
  });
  const sentimentChartData = Object.values(sentimentByDate)
    .map((d) => ({
      date: d.date.slice(5), // MM-DD
      Sentiment: Math.round((d.avg / d.count) * 100) / 100,
    }))
    .sort((a, b) => a.date.localeCompare(b.date));

  const isDemo = mode === 'DEMO';

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full mx-auto mb-3" />
          <p className="text-gray-500">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/" className="flex items-center gap-2">
              <div className="w-7 h-7 bg-blue-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-xs">T</span>
              </div>
              <span className="font-semibold text-gray-900">TechCorp</span>
            </Link>
            <span className="text-gray-300">/</span>
            <span className="text-sm text-gray-600">Admin Dashboard</span>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-xs text-gray-400 hidden sm:block">
              Updated {lastRefresh.toLocaleTimeString()}
            </span>
            <ModeToggle currentMode={mode} onModeChange={setMode} />
            <button
              onClick={handleSeed}
              disabled={seeding}
              className="text-xs bg-gray-100 hover:bg-gray-200 text-gray-600 px-3 py-1.5 rounded-lg transition-colors disabled:opacity-60"
            >
              {seeding ? 'Seeding...' : 'Seed Demo Data'}
            </button>
            <Link
              href="/support"
              className="text-xs bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded-lg transition-colors"
            >
              + New Ticket
            </Link>
          </div>
        </div>
        {seedMsg && (
          <div className="bg-green-50 border-t border-green-100 px-4 py-2 text-xs text-green-700 text-center">
            {seedMsg}
          </div>
        )}
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Mode Banner */}
        <div
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium mb-6 ${
            isDemo
              ? 'bg-yellow-50 border border-yellow-200 text-yellow-800'
              : 'bg-green-50 border border-green-200 text-green-800'
          }`}
        >
          <span className={`w-2.5 h-2.5 rounded-full ${isDemo ? 'bg-yellow-500' : 'bg-green-500'} animate-pulse-dot`} />
          {isDemo
            ? 'Running in DEMO mode — data is simulated, no external APIs called'
            : 'Running in LIVE mode — real data, real integrations'}
        </div>

        {/* Stats Cards */}
        {dailyStats && (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            {[
              {
                label: 'Total Tickets',
                value: dailyStats.total_tickets,
                icon: '🎫',
                color: 'text-blue-600',
                bg: 'bg-blue-50',
              },
              {
                label: 'Resolved',
                value: dailyStats.resolved_tickets,
                icon: '✅',
                color: 'text-green-600',
                bg: 'bg-green-50',
                sub: dailyStats.total_tickets
                  ? `${Math.round((dailyStats.resolved_tickets / dailyStats.total_tickets) * 100)}%`
                  : '0%',
              },
              {
                label: 'Escalated',
                value: dailyStats.escalated_tickets,
                icon: '🚨',
                color: 'text-red-600',
                bg: 'bg-red-50',
              },
              {
                label: 'Avg Response',
                value: dailyStats.avg_resolution_minutes
                  ? `${dailyStats.avg_resolution_minutes.toFixed(1)}m`
                  : 'N/A',
                icon: '⚡',
                color: 'text-purple-600',
                bg: 'bg-purple-50',
              },
            ].map((stat) => (
              <div
                key={stat.label}
                className="bg-white rounded-xl border border-gray-200 p-4"
              >
                <div className={`w-9 h-9 ${stat.bg} rounded-lg flex items-center justify-center text-lg mb-3`}>
                  {stat.icon}
                </div>
                <div className={`text-2xl font-bold ${stat.color}`}>{stat.value}</div>
                <div className="text-xs text-gray-500 mt-0.5">{stat.label}</div>
                {stat.sub && (
                  <div className="text-xs text-gray-400 mt-0.5">({stat.sub} resolution rate)</div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
          {/* Channel Breakdown */}
          <div className="bg-white border border-gray-200 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-gray-800 mb-4">
              Channel Breakdown (Last 7 Days)
            </h3>
            {channelChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={channelChartData} margin={{ top: 0, right: 0, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Bar dataKey="Total" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="Resolved" fill="#22c55e" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="Escalated" fill="#ef4444" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-48 flex items-center justify-center text-gray-400 text-sm">
                No data yet — seed demo data to populate
              </div>
            )}
          </div>

          {/* Sentiment Trend */}
          <div className="bg-white border border-gray-200 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-gray-800 mb-4">
              Sentiment Trend (Last 7 Days)
            </h3>
            {sentimentChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={sentimentChartData} margin={{ top: 0, right: 0, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                  <YAxis domain={[0, 1]} tick={{ fontSize: 12 }} />
                  <Tooltip formatter={(v: number) => [`${(v * 100).toFixed(0)}%`, 'Satisfaction']} />
                  <Line
                    type="monotone"
                    dataKey="Sentiment"
                    stroke="#8b5cf6"
                    strokeWidth={2}
                    dot={{ r: 4, fill: '#8b5cf6' }}
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-48 flex items-center justify-center text-gray-400 text-sm">
                No sentiment data available
              </div>
            )}
          </div>
        </div>

        {/* Bottom Row: Tickets + Escalations */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Recent Tickets */}
          <div className="lg:col-span-2 bg-white border border-gray-200 rounded-xl overflow-hidden">
            <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-gray-800">Recent Tickets</h3>
              <span className="text-xs text-gray-400">{tickets.length} shown</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50">
                    {['Ticket', 'Subject', 'Channel', 'Status', 'Priority', 'Created'].map(
                      (h) => (
                        <th
                          key={h}
                          className="px-4 py-2.5 text-left text-xs font-medium text-gray-500 uppercase tracking-wide"
                        >
                          {h}
                        </th>
                      ),
                    )}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {tickets.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-4 py-8 text-center text-gray-400 text-sm">
                        No tickets yet — click &quot;Seed Demo Data&quot; to populate
                      </td>
                    </tr>
                  ) : (
                    tickets.map((ticket) => (
                      <tr key={ticket.ticket_id} className="hover:bg-gray-50 transition-colors">
                        <td className="px-4 py-3">
                          <Link
                            href={`/ticket/${ticket.ticket_id}`}
                            className="font-mono text-xs text-blue-600 hover:underline"
                          >
                            #{ticket.ticket_id.slice(0, 8)}
                          </Link>
                        </td>
                        <td className="px-4 py-3 max-w-32 truncate text-gray-700 text-xs">
                          {ticket.subject || 'Support Request'}
                        </td>
                        <td className="px-4 py-3">
                          <ChannelBadge channel={ticket.channel} size="sm" />
                        </td>
                        <td className="px-4 py-3">
                          <TicketStatusBadge status={ticket.status} />
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={`text-xs font-medium ${
                              ticket.priority === 'urgent'
                                ? 'text-red-600'
                                : ticket.priority === 'high'
                                ? 'text-orange-500'
                                : ticket.priority === 'medium'
                                ? 'text-yellow-600'
                                : 'text-gray-500'
                            }`}
                          >
                            {ticket.priority.charAt(0).toUpperCase() + ticket.priority.slice(1)}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-xs text-gray-400">
                          {new Date(ticket.created_at).toLocaleDateString('en-PK')}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Escalations */}
          <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
            <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-gray-800">Escalations</h3>
              {escalations.length > 0 && (
                <span className="bg-red-100 text-red-700 text-xs font-bold px-2 py-0.5 rounded-full">
                  {escalations.length}
                </span>
              )}
            </div>
            <div className="divide-y divide-gray-50 max-h-96 overflow-y-auto">
              {escalations.length === 0 ? (
                <div className="px-5 py-8 text-center text-gray-400 text-sm">
                  No pending escalations
                </div>
              ) : (
                escalations.map((esc) => (
                  <div key={esc.ticket_id} className="px-4 py-3">
                    <div className="flex items-start justify-between gap-2 mb-1">
                      <Link
                        href={`/ticket/${esc.ticket_id}`}
                        className="font-mono text-xs text-blue-600 hover:underline"
                      >
                        #{esc.ticket_id.slice(0, 8)}
                      </Link>
                      <ChannelBadge channel={esc.channel} size="sm" />
                    </div>
                    <p className="text-xs text-gray-700 truncate">
                      {esc.subject || 'Escalated request'}
                    </p>
                    <p className="text-xs text-gray-400 mt-0.5">
                      {esc.customer_name || 'Unknown customer'}
                    </p>
                    {esc.reason && (
                      <p className="text-xs text-red-600 mt-1">↑ {esc.reason}</p>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
