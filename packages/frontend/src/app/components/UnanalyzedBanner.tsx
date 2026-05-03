import React, { useState, useEffect } from 'react';
import { AlertCircle, X, Sparkles, ArrowRight } from 'lucide-react';
import { Link } from 'react-router';
import { getSyncStatus, type SyncStatusResponse } from '../api';

export function UnanalyzedBanner() {
  const [status, setStatus] = useState<SyncStatusResponse | null>(null);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    getSyncStatus()
      .then(setStatus)
      .catch(console.error);
  }, []);

  // Don't show if dismissed, no data, no pending repos, or currently syncing
  if (dismissed || !status || status.pending_repos === 0 || status.is_syncing) {
    return null;
  }

  return (
    <div className="bg-amber-50 dark:bg-amber-950/50 border border-amber-200 dark:border-amber-800 rounded-xl p-4 mb-6">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-medium text-amber-800 dark:text-amber-200">
              {status.pending_repos} repos pending AI analysis
            </h3>
            <p className="text-sm text-amber-700 dark:text-amber-300 mt-1">
              Some repositories haven't been analyzed yet. Run AI analysis to get better search results and summaries.
            </p>
          </div>
        </div>
        <button
          onClick={() => setDismissed(true)}
          className="text-amber-600 dark:text-amber-400 hover:text-amber-800 dark:hover:text-amber-200"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
      <div className="mt-3 flex items-center gap-3">
        <Link
          to="/repositories?filter=pending"
          className="inline-flex items-center gap-1.5 text-sm font-medium text-amber-700 dark:text-amber-300 hover:text-amber-800 dark:hover:text-amber-200"
        >
          View pending repos
          <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>
    </div>
  );
}
