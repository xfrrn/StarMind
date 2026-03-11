import React from 'react';
import { NavLink } from 'react-router';
import { Sparkles, Library, RefreshCw, Settings, Github } from 'lucide-react';
import { cn } from '../utils';

export function Sidebar() {
  const navItems = [
    { to: "/", icon: Sparkles, label: "AI Search", end: true },
    { to: "/repositories", icon: Library, label: "Repositories", end: false },
    { to: "/sync", icon: RefreshCw, label: "Sync Center", end: true },
    { to: "/settings", icon: Settings, label: "Settings", end: true },
  ];

  return (
    <aside className="w-64 flex-shrink-0 border-r border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-950 flex flex-col h-full">
      <div className="h-16 flex items-center px-6 border-b border-zinc-200 dark:border-zinc-800">
        <div className="flex items-center gap-2 text-zinc-900 dark:text-zinc-50 font-semibold text-sm tracking-tight">
          <Github className="w-5 h-5" />
          <span>StarMind</span>
        </div>
      </div>

      <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
        <div className="text-xs font-medium text-zinc-500 dark:text-zinc-400 mb-3 px-2 uppercase tracking-wider">
          Workspace
        </div>
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) => cn(
              "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors",
              isActive
                ? "bg-zinc-200/50 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-50"
                : "text-zinc-600 dark:text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-50 hover:bg-zinc-100 dark:hover:bg-zinc-800/50"
            )}
          >
            <item.icon className="w-4 h-4" />
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="p-4 border-t border-zinc-200 dark:border-zinc-800">
        <div className="flex items-center gap-3 px-2 py-2">
          <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-blue-500 to-indigo-500 flex items-center justify-center text-white text-xs font-bold">
            JD
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-medium text-zinc-900 dark:text-zinc-50">John Doe</span>
            <span className="text-xs text-zinc-500 dark:text-zinc-400">Pro Plan</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
