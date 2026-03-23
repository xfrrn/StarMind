import React, { useState, useEffect, useCallback, useRef } from 'react';
import { RefreshCw, Github, CheckCircle2, Clock, AlertCircle, Bot, Download } from 'lucide-react';
import { triggerSync, triggerAiAnalysis, getSyncStatus, type SyncStatusResponse } from '../api';

export function SyncCenterPage() {
  const [status, setStatus] = useState<SyncStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [message, setMessage] = useState('');
  const syncingRef = useRef(false);

  useEffect(() => {
    syncingRef.current = syncing;
  }, [syncing]);

  const loadStatus = useCallback(async () => {
    try {
      const data = await getSyncStatus();
      setStatus(data);
      setSyncing(data.is_syncing);
    } catch (err) {
      console.error('Failed to load sync status:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let stopped = false;
    let timer: ReturnType<typeof setTimeout> | null = null;

    const scheduleNext = () => {
      if (stopped) return;
      const nextDelayMs = syncingRef.current ? 3000 : 20000;
      timer = setTimeout(runOnce, nextDelayMs);
    };

    const runOnce = async () => {
      if (stopped) return;
      if (document.visibilityState !== 'visible') {
        timer = setTimeout(runOnce, 15000);
        return;
      }
      await loadStatus();
      scheduleNext();
    };

    const onVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        loadStatus();
      }
    };

    loadStatus();
    scheduleNext();
    document.addEventListener('visibilitychange', onVisibilityChange);

    return () => {
      stopped = true;
      if (timer) clearTimeout(timer);
      document.removeEventListener('visibilitychange', onVisibilityChange);
    };
  }, [loadStatus]);

  const handleSync = async (fullSync = false) => {
    try {
      setSyncing(true);
      setMessage('');
      const result = await triggerSync(fullSync);
      setMessage(result.message);
      setTimeout(loadStatus, 800);
    } catch (err: any) {
      setMessage(err.message || 'Sync failed');
      setSyncing(false);
    }
  };

  const handleAiAnalysis = async () => {
    try {
      setSyncing(true);
      setMessage('');
      const result = await triggerAiAnalysis();
      setMessage(result.message);
      setTimeout(loadStatus, 800);
    } catch (err: any) {
      setMessage(err.message || 'AI Analysis failed');
      setSyncing(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="w-8 h-8 border-2 border-zinc-300 border-t-zinc-900 dark:border-zinc-700 dark:border-t-zinc-50 rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto py-12 px-6">
      <div className="mb-10">
        <h1 className="text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
          Sync Center
        </h1>
        <p className="text-zinc-500 dark:text-zinc-400 mt-2 text-lg">
          Manage your GitHub connection and synchronization settings.
        </p>
      </div>

      <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl overflow-hidden shadow-sm mb-8">
        <div className="p-6 md:p-8 border-b border-zinc-200 dark:border-zinc-800 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="flex items-center gap-5">
            <div className="w-16 h-16 bg-zinc-100 dark:bg-zinc-800 rounded-full flex items-center justify-center border-4 border-white dark:border-zinc-950 shadow-sm">
              <Github className="w-8 h-8 text-zinc-900 dark:text-zinc-50" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50 flex items-center gap-2">
                GitHub Connected
                <CheckCircle2 className="w-5 h-5 text-emerald-500" />
              </h2>
              <p className="text-zinc-500 dark:text-zinc-400">
                Sync your starred repositories to search with AI.
              </p>
            </div>
          </div>
        </div>

        <div className="p-6 md:p-8 grid grid-cols-2 md:grid-cols-4 gap-6">
          <div className="bg-zinc-50 dark:bg-zinc-950 rounded-xl p-5 border border-zinc-100 dark:border-zinc-800/50">
            <div className="text-sm font-medium text-zinc-500 dark:text-zinc-400 mb-1">Total Stars</div>
            <div className="text-3xl font-bold text-zinc-900 dark:text-zinc-50">
              {status?.total_stars?.toLocaleString() || 0}
            </div>
          </div>
          <div className="bg-blue-50 dark:bg-blue-950/20 rounded-xl p-5 border border-blue-100 dark:border-blue-900/30">
            <div className="text-sm font-medium text-blue-600 dark:text-blue-400 mb-1">Indexed Repos</div>
            <div className="text-3xl font-bold text-blue-700 dark:text-blue-300">
              {status?.indexed_repos?.toLocaleString() || 0}
            </div>
          </div>
          <div className="bg-amber-50 dark:bg-amber-950/20 rounded-xl p-5 border border-amber-100 dark:border-amber-900/30">
            <div className="text-sm font-medium text-amber-600 dark:text-amber-400 mb-1">Pending Analysis</div>
            <div className="text-3xl font-bold text-amber-700 dark:text-amber-300">
              {status?.pending_repos?.toLocaleString() || 0}
            </div>
          </div>
          <div className="bg-emerald-50 dark:bg-emerald-950/20 rounded-xl p-5 border border-emerald-100 dark:border-emerald-900/30">
            <div className="text-sm font-medium text-emerald-600 dark:text-emerald-400 mb-1">Last Sync</div>
            <div className="text-2xl font-bold text-emerald-700 dark:text-emerald-300 mt-1">
              {status?.last_sync || 'Never'}
            </div>
          </div>
        </div>

        {/* Sync progress */}
        {syncing && status?.is_syncing && (
          <div className="px-6 md:px-8 pb-4">
            <div className="bg-blue-50 dark:bg-blue-950/20 border border-blue-100 dark:border-blue-900/50 rounded-xl p-4">
              <div className="flex items-center gap-3 mb-2">
                <RefreshCw className="w-4 h-4 animate-spin text-blue-500" />
                <span className="text-sm font-medium text-blue-700 dark:text-blue-300">
                  Processing... {status.progress}/{status.total}
                </span>
              </div>
              {status.current_repo && (
                <p className="text-xs text-blue-600 dark:text-blue-400 ml-7">
                  Current: {status.current_repo}
                </p>
              )}
              {status.total > 0 && (
                <div className="w-full bg-blue-200 dark:bg-blue-900/50 rounded-full h-2 mt-3">
                  <div
                    className="bg-blue-500 h-2 rounded-full transition-all"
                    style={{ width: `${(status.progress / status.total) * 100}%` }}
                  />
                </div>
              )}
            </div>
          </div>
        )}

        {message && (
          <div className="px-6 md:px-8 pb-4">
            <p className="text-sm text-zinc-600 dark:text-zinc-400">{message}</p>
          </div>
        )}

        <div className="p-6 md:p-8 border-t border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-900/50 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex flex-col gap-1 text-sm text-zinc-600 dark:text-zinc-400">
            <span><strong>Incremental:</strong> Update basic info (stars, description).</span>
            <span><strong>Full:</strong> Reset AI analysis & re-process READMEs.</span>
            <span><strong>Analyze:</strong> Run AI categorization for pending repos.</span>
          </div>
          <div className="flex flex-col sm:flex-row gap-3 w-full sm:w-auto">
            <button
              onClick={() => handleSync(false)}
              disabled={syncing}
              className="w-full sm:w-auto flex items-center justify-center gap-2 px-5 py-2.5 bg-white bg-zinc-100 hover:bg-zinc-200 dark:bg-zinc-800 dark:hover:bg-zinc-700 text-zinc-900 dark:text-white rounded-xl font-medium transition-colors shadow-sm disabled:opacity-50 border border-zinc-200 dark:border-zinc-700"
            >
              <RefreshCw className={`w-4 h-4 ${syncing ? 'animate-spin' : ''}`} />
              Incremental Sync
            </button>
            <button
              onClick={() => handleSync(true)}
              disabled={syncing}
              className="w-full sm:w-auto flex items-center justify-center gap-2 px-5 py-2.5 bg-white bg-zinc-100 hover:bg-zinc-200 dark:bg-zinc-800 dark:hover:bg-zinc-700 text-zinc-900 dark:text-white rounded-xl font-medium transition-colors shadow-sm disabled:opacity-50 border border-zinc-200 dark:border-zinc-700"
            >
              <Download className="w-4 h-4" />
              Full Sync
            </button>
            <button
              onClick={handleAiAnalysis}
              disabled={syncing || (status?.pending_repos === 0)}
              className="w-full sm:w-auto flex items-center justify-center gap-2 px-6 py-2.5 bg-zinc-900 hover:bg-zinc-800 dark:bg-zinc-50 dark:hover:bg-zinc-200 text-white dark:text-zinc-900 rounded-xl font-medium transition-colors shadow-sm disabled:opacity-50"
            >
              <Bot className={`w-4 h-4 ${syncing ? 'animate-pulse' : ''}`} />
              Run AI Analysis
            </button>
          </div>
        </div>
      </div>

      <h3 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50 mb-4">Sync History</h3>
      <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl overflow-hidden">
        {(!status?.logs || status.logs.length === 0) ? (
          <div className="p-6 text-center text-zinc-500 dark:text-zinc-400 text-sm">
            No sync history yet. Click "Force Sync Now" to start your first sync.
          </div>
        ) : (
          status.logs.map((log, i) => (
            <div key={i} className="flex items-start gap-4 p-5 border-b border-zinc-100 dark:border-zinc-800 last:border-0">
              <div className="mt-0.5">
                {log.status === 'success' && <CheckCircle2 className="w-5 h-5 text-emerald-500" />}
                {log.status === 'warning' && <AlertCircle className="w-5 h-5 text-amber-500" />}
                {log.status === 'error' && <AlertCircle className="w-5 h-5 text-red-500" />}
              </div>
              <div>
                <div className="font-medium text-zinc-900 dark:text-zinc-50">{log.time}</div>
                <div className="text-sm text-zinc-500 dark:text-zinc-400 mt-1">{log.details}</div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
