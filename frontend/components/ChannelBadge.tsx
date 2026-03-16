import type { Channel } from '@/lib/types';

interface ChannelBadgeProps {
  channel: Channel;
  size?: 'sm' | 'md';
}

const CHANNEL_CONFIG: Record<Channel, { label: string; icon: string; color: string }> = {
  email: {
    label: 'Email',
    icon: '✉️',
    color: 'bg-purple-100 text-purple-700',
  },
  whatsapp: {
    label: 'WhatsApp',
    icon: '💬',
    color: 'bg-green-100 text-green-700',
  },
  web_form: {
    label: 'Web Form',
    icon: '🌐',
    color: 'bg-blue-100 text-blue-700',
  },
};

export default function ChannelBadge({ channel, size = 'md' }: ChannelBadgeProps) {
  const config = CHANNEL_CONFIG[channel] || CHANNEL_CONFIG.web_form;
  const sizeClass = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-3 py-1 text-xs';

  return (
    <span className={`inline-flex items-center gap-1 rounded-full font-medium ${config.color} ${sizeClass}`}>
      <span>{config.icon}</span>
      <span>{config.label}</span>
    </span>
  );
}
