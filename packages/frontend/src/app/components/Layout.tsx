import React, { useState, useEffect } from 'react';
import { Outlet } from 'react-router';
import { RefreshCw, Github, ExternalLink, Clock, LogOut } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { fetchSettings, getSyncStatus } from '../api';
import type { SettingsData } from '../api';
import { useAuth } from '../auth/context';
import { Sidebar } from './Sidebar';

const GITHUB_PAT_URL = 'https://github.com/settings/personal-access-tokens';

export function Layout() {
    const { t } = useTranslation();
    const [lastSyncAt, setLastSyncAt] = useState<string | null>(null);
    const { user, logout } = useAuth();

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

    const handleLogout = () => {
        logout();
    };

    const formatTimeAgo = (isoString: string | null): string => {
        if (!isoString) return t('time.never');

        const date = new Date(isoString);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();

        const minutes = Math.floor(diffMs / 60000);
        const hours = Math.floor(diffMs / 3600000);
        const days = Math.floor(diffMs / 86400000);

        if (minutes < 1) return t('time.justNow');
        if (minutes < 60) return t('time.minAgo', { count: minutes });
        if (hours < 24) return t('time.hourAgo', { count: hours });
        if (days < 7) return t('time.dayAgo', { count: days });
        return date.toLocaleDateString();
    };

    const displayName = user?.display_name || user?.email?.split('@')[0] || 'User';
    const avatarUrl = user?.avatar_url;
    const initials = displayName?.charAt(0)?.toUpperCase() || '?';

    return (
        <div className="flex h-screen w-full bg-white dark:bg-zinc-950 overflow-hidden font-sans selection:bg-blue-100 dark:selection:bg-blue-900/30">
            <Sidebar />
            <div className="flex-1 flex flex-col min-w-0 bg-white dark:bg-zinc-950">
                {/* Header */}
                <header className="h-16 border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 flex items-center justify-between px-6 flex-shrink-0">
                    <div className="flex items-center gap-4">
                        <h1 className="text-sm font-medium text-zinc-900 dark:text-zinc-50">
                            {t('header.overview')}
                        </h1>
                        <div className="h-4 w-px bg-zinc-200 dark:bg-zinc-800" />
                        <div className="flex items-center gap-2 text-xs text-zinc-500 dark:text-zinc-400">
                            <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                            <Clock className="w-3 h-3" />
                            <span>{t('header.lastSynced', { time: formatTimeAgo(lastSyncAt) })}</span>
                        </div>
                    </div>

                    <div className="flex items-center gap-3">
                        <button className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-zinc-700 dark:text-zinc-300 bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-md hover:bg-zinc-200 dark:hover:bg-zinc-800 transition-colors">
                            <RefreshCw className="w-3.5 h-3.5" />
                            {t('header.syncNow')}
                        </button>
                        <button
                            onClick={handleConnectGitHub}
                            className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium text-white bg-zinc-900 dark:bg-zinc-50 dark:text-zinc-900 rounded-md hover:bg-zinc-800 dark:hover:bg-zinc-200 transition-colors shadow-sm"
                        >
                            <Github className="w-3.5 h-3.5" />
                            {t('header.connectGithub')}
                            <ExternalLink className="w-3 h-3 opacity-60" />
                        </button>

                        {/* User info section */}
                        <div className="flex items-center gap-2 ml-2 pl-2 border-l border-zinc-200 dark:border-zinc-800">
                            {avatarUrl ? (
                                <img src={avatarUrl} alt={displayName} className="w-7 h-7 rounded-full object-cover" />
                            ) : (
                                <div className="w-7 h-7 rounded-full bg-blue-600 flex items-center justify-center text-white text-xs font-medium">
                                    {initials}
                                </div>
                            )}
                            <span className="text-xs font-medium text-zinc-700 dark:text-zinc-300 max-w-[120px] truncate">
                                {displayName}
                            </span>
                            <button
                                onClick={handleLogout}
                                className="p-1.5 text-zinc-500 hover:text-zinc-700 dark:text-zinc-400 dark:hover:text-zinc-200 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-md transition-colors"
                                title={t('header.logout')}
                            >
                                <LogOut className="w-4 h-4" />
                            </button>
                        </div>
                    </div>
                </header>

                {/* Main content */}
                <main className="flex-1 overflow-auto bg-white dark:bg-zinc-950 relative z-0">
                    <Outlet />
                </main>
            </div>
        </div>
    );
}
