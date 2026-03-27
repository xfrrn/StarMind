import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router';
import { useTranslation } from 'react-i18next';
import { Archive, Download, Clock, Eye, AlertTriangle, Loader2 } from 'lucide-react';
import { getSharedArchiveInfo, getSharedArchiveDownloadUrl, type SharedArchiveInfo } from '../api';

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

export function SharedArchivePage() {
  const { t } = useTranslation();
  const { shareId } = useParams<{ shareId: string }>();
  const [info, setInfo] = useState<SharedArchiveInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!shareId) return;
    loadInfo();
  }, [shareId]);

  const loadInfo = async () => {
    setLoading(true);
    try {
      const data = await getSharedArchiveInfo(shareId!);
      setInfo(data);
    } catch (err: any) {
      if (err.message?.includes('410')) {
        setError('expired');
      } else if (err.message?.includes('404')) {
        setError('not_found');
      } else {
        setError('error');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    window.open(getSharedArchiveDownloadUrl(shareId!), '_blank');
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-zinc-50 dark:bg-zinc-950">
        <Loader2 className="w-8 h-8 animate-spin text-zinc-400" />
      </div>
    );
  }

  if (error === 'expired') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-zinc-50 dark:bg-zinc-950 p-4">
        <div className="text-center">
          <div className="w-16 h-16 rounded-2xl bg-red-100 dark:bg-red-900/30 flex items-center justify-center mx-auto mb-4">
            <AlertTriangle className="w-8 h-8 text-red-500" />
          </div>
          <h1 className="text-xl font-bold text-zinc-900 dark:text-zinc-50 mb-2">
            {t('sharedArchive.expired')}
          </h1>
          <p className="text-zinc-500 dark:text-zinc-400">
            {t('sharedArchive.expiredDesc')}
          </p>
        </div>
      </div>
    );
  }

  if (error === 'not_found') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-zinc-50 dark:bg-zinc-950 p-4">
        <div className="text-center">
          <div className="w-16 h-16 rounded-2xl bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center mx-auto mb-4">
            <Archive className="w-8 h-8 text-zinc-400" />
          </div>
          <h1 className="text-xl font-bold text-zinc-900 dark:text-zinc-50 mb-2">
            {t('sharedArchive.notFound')}
          </h1>
          <p className="text-zinc-500 dark:text-zinc-400">
            {t('sharedArchive.notFoundDesc')}
          </p>
        </div>
      </div>
    );
  }

  if (!info) return null;

  const expiresDate = new Date(info.expires_at);

  return (
    <div className="min-h-screen flex items-center justify-center bg-zinc-50 dark:bg-zinc-950 p-4">
      <div className="w-full max-w-md bg-white dark:bg-zinc-900 rounded-2xl shadow-xl border border-zinc-200 dark:border-zinc-800 overflow-hidden">
        <div className="p-6 border-b border-zinc-200 dark:border-zinc-800">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center">
              <Archive className="w-6 h-6 text-amber-600 dark:text-amber-400" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-zinc-900 dark:text-zinc-50">
                {info.repo_name}
              </h1>
              <p className="text-sm text-zinc-500 dark:text-zinc-400">
                {formatBytes(info.archive_size)}
              </p>
            </div>
          </div>
        </div>

        <div className="p-6 space-y-4">
          {info.repo_description && (
            <p className="text-sm text-zinc-600 dark:text-zinc-400">
              {info.repo_description}
            </p>
          )}

          <div className="flex items-center gap-4 text-sm text-zinc-500 dark:text-zinc-400">
            <div className="flex items-center gap-1.5">
              <Clock className="w-4 h-4" />
              <span>{t('sharedArchive.expires')}: {expiresDate.toLocaleString()}</span>
            </div>
          </div>

          <div className="flex items-center gap-2 text-xs text-zinc-400 dark:text-zinc-500">
            <Eye className="w-3.5 h-3.5" />
            <span>{t('sharedArchive.viewCount')}: {info.view_count}</span>
          </div>

          <button
            onClick={handleDownload}
            className="w-full flex items-center justify-center gap-2 py-3 bg-blue-500 hover:bg-blue-600 text-white rounded-xl font-medium transition-colors"
          >
            <Download className="w-5 h-5" />
            {t('sharedArchive.download')}
          </button>
        </div>
      </div>
    </div>
  );
}
