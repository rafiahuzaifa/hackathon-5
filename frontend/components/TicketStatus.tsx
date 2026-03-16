'use client';

import type { TicketStatus } from '@/lib/types';

interface TicketStatusBadgeProps {
  status: TicketStatus;
}

const STATUS_CONFIG: Record<TicketStatus, { label: string; color: string; dot: string }> = {
  open: {
    label: 'Open',
    color: 'bg-blue-100 text-blue-700 border border-blue-200',
    dot: 'bg-blue-500',
  },
  processing: {
    label: 'Processing',
    color: 'bg-yellow-100 text-yellow-700 border border-yellow-200',
    dot: 'bg-yellow-500',
  },
  resolved: {
    label: 'Resolved',
    color: 'bg-green-100 text-green-700 border border-green-200',
    dot: 'bg-green-500',
  },
  escalated: {
    label: 'Escalated',
    color: 'bg-red-100 text-red-700 border border-red-200',
    dot: 'bg-red-500',
  },
};

export default function TicketStatusBadge({ status }: TicketStatusBadgeProps) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.open;
  const isAnimated = status === 'processing';

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${config.color}`}
    >
      <span
        className={`w-1.5 h-1.5 rounded-full ${config.dot} ${isAnimated ? 'animate-pulse' : ''}`}
      />
      {config.label}
    </span>
  );
}
