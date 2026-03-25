import React, { useState, useEffect } from 'react';
import { RefreshCw, Github, ExternalLink, Clock } from 'lucide-react';
import { fetchSettings, getSyncStatus, type SettingsData } from '../api';

const GITHUB_PAT_URL = 'https://github.com/settings/personal-access-tokens';

function formatTimeAgo(isoString: string | null): string {
  if (!isoString) return 'Never';

  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();

  const minutes = Math.floor(diffMs / 60000);
  const hours = Math.floor(diffMs / 3600000);
  const days = Math.floor(diffMs / 86400000);

  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes} min ago`;
  if (hours < 24) return `${hours} hour${hours > 1 ? 's' : ''} ago`;
  if (days < 7) return `${days} day${days > 1 ? 's' : ''} ago`;

  return date.toLocaleDateString();
}

export function Header() {
  const [lastSyncAt, setLastSyncAt] = useState<string | null>(null);

  useEffect(() => {
    // Fetch last sync time
    const fetchLastSync = async () => {
      try {
        const settings = await fetchSettings();
        setLastSyncAt(settings.last_sync_at);
      } catch (e) {
        console.error('Failed to fetch last sync time:', e);
      }
    };

    fetchLastSync();

    // Poll every 30 seconds for updates
    const interval = setInterval(fetchLastSync, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleConnectGitHub = () => {
    window.open(GITHUB_PAT_URL, '_blank', 'noopener,noreferrer');
  };

  return (
    <header className="h-16 border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 flex items-center justify-between px-6 flex-shrink-0">
      <div className="flex items-center gap-4">
        <h1 className="text-sm font-medium text-zinc-900 dark:text-zinc-50">
          Overview
        </h1>
        <div className="h-4 w-px bg-zinc-200 dark:bg-zinc-800" />
        <div className="flex items-center gap-2 text-xs text-zinc-500 dark:text-zinc-400">
          <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
          <Clock className="w-3 h-3" />
          <span>Last synced: {formatTimeAgo(lastSyncAt)}</span>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <button className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-zinc-700 dark:text-zinc-300 bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-md hover:bg-zinc-200 dark:hover:bg-zinc-800 transition-colors">
          <RefreshCw className="w-3.5 h-3.5" />
          Sync Now
        </button>
        <button
          onClick={handleConnectGitHub}
          className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-white bg-zinc-900 dark:bg-zinc-50 dark:text-zinc-900 rounded-md hover:bg-zinc-800 dark:hover:bg-zinc-200 transition-colors shadow-sm"
        >
          <Github className="w-3.5 h-3.5" />
          Connect GitHub
          <ExternalLink className="w-3 h-3 opacity-60" />
        </button>
      </div>
    </header>
  );
}
