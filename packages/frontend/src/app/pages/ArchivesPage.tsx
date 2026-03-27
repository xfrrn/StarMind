import React, { useState, useEffect } from 'react';
import { Link } from 'react-router';
import { useTranslation } from 'react-i18next';
import { Archive, Download, Trash2, Star, ExternalLink, RefreshCw, Share2, Loader2 } from 'lucide-react';
import { listArchives, deleteArchive, getArchiveDownloadUrl, createArchive, type ArchivedRepo } from '../api';
import { Badge } from '../components/Badge';
import { ArchiveShareModal } from '../components/ArchiveShareModal';

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

function formatRelativeTime(isoString: string | null | undefined): string {
  if (!isoString) return '';
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const seconds = Math.floor(diffMs / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (seconds < 60) return `${seconds} seconds ago`;
  if (minutes < 60) return `${minutes} ${minutes === 1 ? 'min' : 'mins'} ago`;
  if (hours < 24) return `${hours} ${hours === 1 ? 'hour' : 'hours'} ago`;
  if (days < 30) return `${days} ${days === 1 ? 'day' : 'days'} ago`;
  return date.toLocaleDateString();
}

export function ArchivesPage() {
  const { t } = useTranslation();
  const [archives, setArchives] = useState<ArchivedRepo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [updatingId, setUpdatingId] = useState<number | null>(null);
  const [shareModalRepo, setShareModalRepo] = useState<ArchivedRepo | null>(null);

  useEffect(() => {
    loadArchives();
  }, []);

  const loadArchives = async () => {
    setLoading(true);
    try {
      const data = await listArchives();
      setArchives(data.repositories);
    } catch (err) {
      setError('Failed to load archives');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (repoId: number, repoName: string) => {
    if (!confirm(t('archives.deleteConfirm', { name: repoName }))) return;
    try {
      await deleteArchive(String(repoId));
      setArchives(prev => prev.filter(a => a.id !== repoId));
    } catch (err) {
      console.error('Failed to delete archive:', err);
    }
  };

  const handleDownload = (repoId: number) => {
    window.open(getArchiveDownloadUrl(String(repoId)), '_blank');
  };

  const handleUpdate = async (repoId: number) => {
    setUpdatingId(repoId);
    try {
      await createArchive(String(repoId));
      await loadArchives();
    } catch (err) {
      console.error('Failed to update archive:', err);
      alert(t('archives.updateFailed'));
    } finally {
      setUpdatingId(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="w-8 h-8 border-2 border-zinc-300 border-t-zinc-900 dark:border-zinc-700 dark:border-t-zinc-50 rounded-full animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-5xl mx-auto py-8 px-6 text-center">
        <p className="text-red-500">{error}</p>
        <button onClick={loadArchives} className="mt-4 text-blue-500 hover:underline">
          {t('common.retry') || 'Retry'}
        </button>
      </div>
    );
  }

  return (
    <div className="w-full max-w-[1520px] mx-auto py-8 px-6 xl:px-10">
      <header className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-xl bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center">
            <Archive className="w-5 h-5 text-amber-600 dark:text-amber-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">
              {t('archives.title')}
            </h1>
            <p className="text-sm text-zinc-500 dark:text-zinc-400">
              {t('archives.description')} · {archives.length} {t('archives.repositories')}
            </p>
          </div>
        </div>
      </header>

      {archives.length === 0 ? (
        <div className="text-center py-16">
          <div className="w-16 h-16 rounded-2xl bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center mx-auto mb-4">
            <Archive className="w-8 h-8 text-zinc-400" />
          </div>
          <p className="text-zinc-500 dark:text-zinc-400 mb-2">{t('archives.noArchives')}</p>
          <p className="text-sm text-zinc-400 dark:text-zinc-500">{t('archives.noArchivesHint')}</p>
          <Link
            to="/repositories"
            className="mt-4 inline-block text-blue-500 hover:text-blue-600 text-sm font-medium"
          >
            {t('archives.browseRepos')} →
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {archives.map((repo) => (
            <div
              key={repo.id}
              className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-5 hover:border-zinc-300 dark:hover:border-zinc-700 transition-colors"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1 min-w-0">
                  <Link
                    to={`/repositories/${repo.id}`}
                    className="text-lg font-semibold text-zinc-900 dark:text-zinc-50 hover:text-blue-500 dark:hover:text-blue-400 truncate block"
                  >
                    {repo.name}
                  </Link>
                  <p className="text-sm text-zinc-500 dark:text-zinc-400 line-clamp-2 mt-1">
                    {repo.description || t('common.noDescription')}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-4 text-sm text-zinc-500 dark:text-zinc-400 mb-4">
                {repo.language && (
                  <Badge variant="outline" className="text-xs py-0.5 px-2">
                    {repo.language}
                  </Badge>
                )}
                <div className="flex items-center gap-1">
                  <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
                  <span>{(repo.stars / 1000).toFixed(1)}k</span>
                </div>
                <div className="flex items-center gap-1">
                  <Archive className="w-3.5 h-3.5" />
                  <span>{formatBytes(repo.archive_size)}</span>
                </div>
              </div>

              <div className="text-xs text-zinc-400 dark:text-zinc-500 mb-4">
                {t('archives.archivedAt')}: {formatRelativeTime(repo.archived_at)}
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleDownload(repo.id)}
                  className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-emerald-100 hover:bg-emerald-200 dark:bg-emerald-900/30 dark:hover:bg-emerald-900/50 text-emerald-700 dark:text-emerald-400 rounded-lg text-sm font-medium transition-colors"
                >
                  <Download className="w-4 h-4" />
                  {t('archives.download')}
                </button>
                <button
                  onClick={() => handleUpdate(repo.id)}
                  disabled={updatingId === repo.id}
                  className="p-2 text-zinc-400 hover:text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-colors disabled:opacity-50"
                  title={t('archives.update')}
                >
                  {updatingId === repo.id ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <RefreshCw className="w-4 h-4" />
                  )}
                </button>
                <button
                  onClick={() => setShareModalRepo(repo)}
                  className="p-2 text-zinc-400 hover:text-purple-500 hover:bg-purple-50 dark:hover:bg-purple-900/20 rounded-lg transition-colors"
                  title={t('archives.share')}
                >
                  <Share2 className="w-4 h-4" />
                </button>
                <button
                  onClick={() => handleDelete(repo.id, repo.name)}
                  className="p-2 text-zinc-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                  title={t('archives.delete')}
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {shareModalRepo && (
        <ArchiveShareModal
          repo={shareModalRepo}
          onClose={() => setShareModalRepo(null)}
        />
      )}
    </div>
  );
}
