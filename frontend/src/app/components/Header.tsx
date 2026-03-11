import React from 'react';
import { RefreshCw, Github } from 'lucide-react';

export function Header() {
  return (
    <header className="h-16 border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 flex items-center justify-between px-6 flex-shrink-0">
      <div className="flex items-center gap-4">
        <h1 className="text-sm font-medium text-zinc-900 dark:text-zinc-50">
          Overview
        </h1>
        <div className="h-4 w-px bg-zinc-200 dark:bg-zinc-800" />
        <div className="flex items-center gap-2 text-xs text-zinc-500 dark:text-zinc-400">
          <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
          Last synced: 2 hours ago
        </div>
      </div>

      <div className="flex items-center gap-3">
        <button className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-zinc-700 dark:text-zinc-300 bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-md hover:bg-zinc-200 dark:hover:bg-zinc-800 transition-colors">
          <RefreshCw className="w-3.5 h-3.5" />
          Sync Now
        </button>
        <button className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-white bg-zinc-900 dark:bg-zinc-50 dark:text-zinc-900 rounded-md hover:bg-zinc-800 dark:hover:bg-zinc-200 transition-colors shadow-sm">
          <Github className="w-3.5 h-3.5" />
          Connect GitHub
        </button>
      </div>
    </header>
  );
}
