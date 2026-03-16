'use client';

import { useState } from 'react';
import { switchMode } from '@/lib/api';

interface ModeToggleProps {
  currentMode: 'DEMO' | 'LIVE';
  onModeChange?: (mode: 'DEMO' | 'LIVE') => void;
}

export default function ModeToggle({ currentMode, onModeChange }: ModeToggleProps) {
  const [mode, setMode] = useState(currentMode);
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState('');

  const isDemo = mode === 'DEMO';

  async function handleToggle() {
    if (loading) return;

    const newDryRun = !isDemo;
    setLoading(true);

    try {
      const result = await switchMode(newDryRun);
      const newMode = result.current_mode as 'DEMO' | 'LIVE';
      setMode(newMode);
      onModeChange?.(newMode);
      setToast(`Switched to ${newMode} mode`);
      setTimeout(() => setToast(''), 3000);
    } catch {
      setToast('Failed to switch mode');
      setTimeout(() => setToast(''), 3000);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="relative">
      {/* Toast */}
      {toast && (
        <div className="absolute bottom-full right-0 mb-2 bg-gray-800 text-white text-xs px-3 py-1.5 rounded-lg whitespace-nowrap shadow-lg animate-fade-in">
          {toast}
        </div>
      )}

      {/* Toggle Button */}
      <button
        onClick={handleToggle}
        disabled={loading}
        className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-semibold transition-all border ${
          isDemo
            ? 'bg-yellow-50 border-yellow-300 text-yellow-700 hover:bg-yellow-100'
            : 'bg-green-50 border-green-300 text-green-700 hover:bg-green-100'
        } ${loading ? 'opacity-60 cursor-not-allowed' : 'cursor-pointer'}`}
      >
        {loading ? (
          <span className="w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin" />
        ) : (
          <span className={`w-3 h-3 rounded-full ${isDemo ? 'bg-yellow-500' : 'bg-green-500'} animate-pulse-dot`} />
        )}

        <span>{isDemo ? 'DEMO' : 'LIVE'}</span>

        {/* Toggle track */}
        <div
          className={`relative w-10 h-5 rounded-full transition-colors ${
            isDemo ? 'bg-yellow-300' : 'bg-green-400'
          }`}
        >
          <div
            className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${
              isDemo ? 'translate-x-0.5' : 'translate-x-5'
            }`}
          />
        </div>
      </button>
    </div>
  );
}
