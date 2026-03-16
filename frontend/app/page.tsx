'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { getHealth, getDailyStats } from '@/lib/api';
import type { DailyStats, HealthStatus } from '@/lib/types';

export default function LandingPage() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [stats, setStats] = useState<DailyStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [h, s] = await Promise.all([getHealth(), getDailyStats()]);
        setHealth(h);
        setStats(s);
      } catch {
        // API not available — show demo data
        setHealth({
          status: 'healthy',
          mode: 'DEMO',
          dry_run: true,
          version: '1.0.0',
          timestamp: new Date().toISOString(),
          services: { database: 'demo', kafka: 'demo', anthropic: 'configured' },
        });
        setStats({
          total_tickets: 133,
          resolved_tickets: 112,
          escalated_tickets: 9,
          open_tickets: 12,
          avg_resolution_minutes: 5.8,
          avg_sentiment: 0.74,
          date: new Date().toISOString().split('T')[0],
          mode: 'DEMO',
        });
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const isDemo = health?.mode === 'DEMO' || health?.dry_run;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-950 to-slate-900">
      {/* Header */}
      <header className="border-b border-white/10 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-blue-500 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-sm">T</span>
            </div>
            <span className="text-white font-semibold text-lg">TechCorp</span>
          </div>

          <div className="flex items-center gap-3">
            {/* Mode Badge */}
            <span
              className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold ${
                isDemo
                  ? 'bg-yellow-500/20 text-yellow-300 border border-yellow-500/30'
                  : 'bg-green-500/20 text-green-300 border border-green-500/30'
              }`}
            >
              <span
                className={`w-2 h-2 rounded-full animate-pulse-dot ${
                  isDemo ? 'bg-yellow-400' : 'bg-green-400'
                }`}
              />
              {isDemo ? 'DEMO MODE' : 'LIVE MODE'}
            </span>

            <Link
              href="/dashboard"
              className="text-sm text-white/70 hover:text-white transition-colors"
            >
              Dashboard
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16 sm:py-24">
        <div className="text-center animate-fade-in">
          <div className="inline-flex items-center gap-2 bg-blue-500/10 border border-blue-500/20 rounded-full px-4 py-2 text-blue-300 text-sm font-medium mb-8">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
            Powered by Claude AI — Available 24/7
          </div>

          <h1 className="text-4xl sm:text-6xl font-extrabold text-white mb-6 leading-tight">
            TechCorp AI Support
            <br />
            <span className="bg-gradient-to-r from-blue-400 to-cyan-300 bg-clip-text text-transparent">
              Never Wait for Help Again
            </span>
          </h1>

          <p className="text-xl text-white/60 max-w-2xl mx-auto mb-10">
            Instant AI-powered support for TaskFlow Pro. Email, WhatsApp, or web —
            get expert help in seconds, not hours.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              href="/support"
              className="inline-flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-500 text-white font-semibold px-8 py-4 rounded-xl transition-all hover:scale-105 shadow-lg shadow-blue-500/25"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
              Get Support Now
            </Link>

            <Link
              href="/dashboard"
              className="inline-flex items-center justify-center gap-2 bg-white/10 hover:bg-white/20 text-white font-semibold px-8 py-4 rounded-xl transition-all border border-white/20"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              Admin Dashboard
            </Link>
          </div>
        </div>

        {/* Channel Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-20">
          {[
            {
              icon: '✉️',
              title: 'Email Support',
              desc: 'Send us an email and get a detailed response in your inbox.',
              badge: 'support@techcorp.pk',
              color: 'from-purple-500/10 to-purple-600/5',
              border: 'border-purple-500/20',
            },
            {
              icon: '💬',
              title: 'WhatsApp',
              desc: 'Chat with our AI on WhatsApp for quick, casual support.',
              badge: '+92-300-TECHCORP',
              color: 'from-green-500/10 to-green-600/5',
              border: 'border-green-500/20',
            },
            {
              icon: '🌐',
              title: 'Web Form',
              desc: 'Fill out our support form and track your ticket status online.',
              badge: 'Available Now',
              color: 'from-blue-500/10 to-blue-600/5',
              border: 'border-blue-500/20',
            },
          ].map((channel) => (
            <div
              key={channel.title}
              className={`bg-gradient-to-br ${channel.color} border ${channel.border} rounded-2xl p-6 backdrop-blur-sm hover:scale-105 transition-transform cursor-pointer`}
            >
              <div className="text-4xl mb-4">{channel.icon}</div>
              <h3 className="text-white font-semibold text-lg mb-2">{channel.title}</h3>
              <p className="text-white/60 text-sm mb-4">{channel.desc}</p>
              <span className="inline-block bg-white/10 text-white/80 text-xs px-3 py-1 rounded-full font-mono">
                {channel.badge}
              </span>
            </div>
          ))}
        </div>

        {/* Stats Bar */}
        {!loading && stats && (
          <div className="mt-16 bg-white/5 border border-white/10 rounded-2xl p-6 animate-fade-in">
            <p className="text-white/40 text-sm text-center mb-6 uppercase tracking-wider">
              Today&apos;s Performance
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-6">
              {[
                { label: 'Tickets Today', value: stats.total_tickets, suffix: '' },
                {
                  label: 'Resolved',
                  value: `${stats.resolved_tickets}/${stats.total_tickets}`,
                  suffix: '',
                },
                {
                  label: 'Avg Response',
                  value: stats.avg_resolution_minutes?.toFixed(1) ?? 'N/A',
                  suffix: 'min',
                },
                {
                  label: 'Satisfaction',
                  value: stats.avg_sentiment
                    ? `${Math.round(stats.avg_sentiment * 100)}%`
                    : 'N/A',
                  suffix: '',
                },
              ].map((stat) => (
                <div key={stat.label} className="text-center">
                  <div className="text-3xl font-bold text-white">
                    {stat.value}
                    {stat.suffix && (
                      <span className="text-base font-normal text-white/50 ml-1">
                        {stat.suffix}
                      </span>
                    )}
                  </div>
                  <div className="text-white/50 text-sm mt-1">{stat.label}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* AI Features */}
        <div className="mt-16 text-center">
          <h2 className="text-2xl font-bold text-white mb-8">What our AI can help with</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 max-w-3xl mx-auto">
            {[
              'Password Reset',
              'Team Management',
              'API Integration',
              'Mobile App Issues',
              'Data Export',
              'Account Setup',
              'Task Configuration',
              'Notification Settings',
              'Billing Inquiries*',
            ].map((feature) => (
              <div
                key={feature}
                className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white/70 text-sm"
              >
                {feature}
              </div>
            ))}
          </div>
          <p className="text-white/30 text-xs mt-4">* Billing inquiries redirected to billing team</p>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-white/10 mt-20 py-8">
        <div className="max-w-7xl mx-auto px-4 text-center text-white/30 text-sm">
          © 2025 TechCorp. AI Support powered by Anthropic Claude.
          {' '}
          <span className={isDemo ? 'text-yellow-500/60' : 'text-green-500/60'}>
            Running in {isDemo ? 'DEMO' : 'LIVE'} mode.
          </span>
        </div>
      </footer>
    </div>
  );
}
