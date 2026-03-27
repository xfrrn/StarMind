import React, { useState, useEffect, useRef } from 'react';
import { NavLink } from 'react-router';
import { Sparkles, Library, RefreshCw, Settings, Github, ChevronUp, ExternalLink, Moon, Sun, CheckCircle, XCircle, FolderOpen, BarChart3, Languages } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { cn } from '../utils';
import { useTheme, type Theme } from '../hooks/useTheme';
import { fetchSettings, type SettingsData } from '../api';

export function Sidebar() {
  const { t, i18n } = useTranslation();
  const [showMenu, setShowMenu] = useState(false);
  const [settings, setSettings] = useState<SettingsData | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const { theme, setTheme, resolvedTheme } = useTheme();

  useEffect(() => {
    fetchSettings().then(setSettings).catch(console.error);
  }, []);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setShowMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const navItems = [
    { to: "/", icon: Sparkles, label: t('nav.aiSearch'), end: true },
    { to: "/dashboard", icon: BarChart3, label: t('nav.dashboard'), end: true },
    { to: "/repositories", icon: Library, label: t('nav.repositories'), end: false },
    { to: "/collections", icon: FolderOpen, label: t('nav.collections'), end: true },
    { to: "/sync", icon: RefreshCw, label: t('nav.syncCenter'), end: true },
    { to: "/settings", icon: Settings, label: t('nav.settings'), end: true },
  ];

  const firstName = settings?.first_name || '';
  const lastName = settings?.last_name || '';
  const githubUsername = settings?.github_username || '';
  const initials = (firstName && lastName) ? `${firstName[0]}${lastName[0]}`.toUpperCase() : 'SM';
  const displayName = (firstName || lastName) ? `${firstName} ${lastName}`.trim() : (githubUsername || 'User');

  const toggleTheme = () => {
    const next: Theme = theme === 'system' ? 'light' : theme === 'light' ? 'dark' : 'system';
    setTheme(next);
  };

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
          {t('nav.workspace')}
        </div>
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) => cn(
              "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
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

      <div className="p-4 border-t border-zinc-200 dark:border-zinc-800 relative" ref={menuRef}>
        <button
          onClick={() => setShowMenu(!showMenu)}
          className="w-full flex items-center gap-3 px-2 py-2 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800/50 transition-colors"
        >
          <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-blue-500 to-indigo-500 flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
            {initials}
          </div>
          <div className="flex-1 text-left min-w-0">
            <div className="text-sm font-medium text-zinc-900 dark:text-zinc-50 truncate">{displayName}</div>
            <div className="text-xs text-zinc-500 dark:text-zinc-400 flex items-center gap-1.5">
              {githubUsername && <span className="truncate">@{githubUsername}</span>}
              {!githubUsername && <span className="text-zinc-400 dark:text-zinc-500">{t('common.notConfigured')}</span>}
            </div>
          </div>
          <ChevronUp className={cn("w-4 h-4 text-zinc-400 transition-transform", showMenu && "rotate-180")} />
        </button>

        {showMenu && (
          <div className="absolute bottom-full left-4 right-4 mb-2 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl shadow-lg overflow-hidden z-50">
            {/* Connection Status */}
            <div className="p-3 border-b border-zinc-200 dark:border-zinc-800 space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="text-zinc-500 dark:text-zinc-400">{t('settings.githubToken')}</span>
                {settings?.github_token_set ? (
                  <span className="flex items-center gap-1 text-emerald-500">
                    <CheckCircle className="w-3 h-3" /> {t('common.connected')}
                  </span>
                ) : (
                  <span className="flex items-center gap-1 text-zinc-400">
                    <XCircle className="w-3 h-3" /> {t('common.notSet')}
                  </span>
                )}
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-zinc-500 dark:text-zinc-400">{t('settings.openaiKey')}</span>
                {settings?.openai_api_key_set ? (
                  <span className="flex items-center gap-1 text-emerald-500">
                    <CheckCircle className="w-3 h-3" /> {t('common.configured')}
                  </span>
                ) : (
                  <span className="flex items-center gap-1 text-zinc-400">
                    <XCircle className="w-3 h-3" /> {t('common.notSet')}
                  </span>
                )}
              </div>
            </div>

            {/* Menu Items */}
            <div className="p-1">
              <NavLink
                to="/settings"
                onClick={() => setShowMenu(false)}
                className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
              >
                <Settings className="w-4 h-4" />
                {t('nav.settings')}
              </NavLink>

              <button
                onClick={toggleTheme}
                className="w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
              >
                <div className="flex items-center gap-2">
                  {resolvedTheme === 'dark' ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4" />}
                  <span>{t('theme.mode', { mode: t(`theme.${resolvedTheme}`) })}</span>
                </div>
                <span className="text-xs text-zinc-400">{t(`theme.${theme}`)}</span>
              </button>

              {/* Language Switcher */}
              <div className="flex items-center justify-between px-3 py-2 rounded-lg text-sm text-zinc-700 dark:text-zinc-300">
                <div className="flex items-center gap-2">
                  <Languages className="w-4 h-4" />
                  <span>{t('language.switch')}</span>
                </div>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => i18n.changeLanguage('en')}
                    className={cn(
                      "px-2 py-0.5 text-xs rounded transition-colors",
                      i18n.language === 'en' ? "bg-zinc-200 dark:bg-zinc-700" : "hover:bg-zinc-100 dark:hover:bg-zinc-800"
                    )}
                  >
                    EN
                  </button>
                  <button
                    onClick={() => i18n.changeLanguage('zh')}
                    className={cn(
                      "px-2 py-0.5 text-xs rounded transition-colors",
                      i18n.language.startsWith('zh') ? "bg-zinc-200 dark:bg-zinc-700" : "hover:bg-zinc-100 dark:hover:bg-zinc-800"
                    )}
                  >
                    中
                  </button>
                </div>
              </div>

              {githubUsername && (
                <a
                  href={`https://github.com/${githubUsername}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={() => setShowMenu(false)}
                  className="flex items-center justify-between px-3 py-2 rounded-lg text-sm text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <Github className="w-4 h-4" />
                    {t('nav.githubProfile')}
                  </div>
                  <ExternalLink className="w-3 h-3 text-zinc-400" />
                </a>
              )}
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
