import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { X, Copy, Check, Link as LinkIcon, Clock } from 'lucide-react';
import { createArchiveShare, getArchiveShareStatus, deleteArchiveShare, type ArchivedRepo } from '../api';

interface ArchiveShareModalProps {
  repo: ArchivedRepo;
  onClose: () => void;
}

export function ArchiveShareModal({ repo, onClose }: ArchiveShareModalProps) {
  const { t } = useTranslation();
  const [shareUrl, setShareUrl] = useState<string | null>(null);
  const [expiresAt, setExpiresAt] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [copied, setCopied] = useState(false);
  const [selectedHours, setSelectedHours] = useState(24);

  const expireOptions = [
    { hours: 1, label: t('archives.expiresIn.1hour') },
    { hours: 24, label: t('archives.expiresIn.24hours') },
    { hours: 168, label: t('archives.expiresIn.7days') },
    { hours: 720, label: t('archives.expiresIn.30days') },
  ];

  useEffect(() => {
    loadShareStatus();
  }, [repo.id]);

  const loadShareStatus = async () => {
    setLoading(true);
    try {
      const status = await getArchiveShareStatus(String(repo.id));
      if (status.is_shared && status.share_url) {
        setShareUrl(status.share_url);
        setExpiresAt(status.expires_at);
      }
    } catch (err) {
      console.error('Failed to load share status:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateShare = async () => {
    setCreating(true);
    try {
      const result = await createArchiveShare(String(repo.id), selectedHours);
      setShareUrl(result.share_url);
      setExpiresAt(result.expires_at);
    } catch (err) {
      console.error('Failed to create share:', err);
      alert(t('archives.shareFailed'));
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteShare = async () => {
    if (!confirm(t('archives.deleteShareConfirm'))) return;
    try {
      await deleteArchiveShare(String(repo.id));
      setShareUrl(null);
      setExpiresAt(null);
    } catch (err) {
      console.error('Failed to delete share:', err);
    }
  };

  const handleCopy = async () => {
    if (!shareUrl) return;
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const formatExpiresTime = (isoString: string) => {
    const date = new Date(isoString);
    return date.toLocaleString();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white dark:bg-zinc-900 rounded-2xl shadow-xl w-full max-w-md mx-4 overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-200 dark:border-zinc-800">
          <div>
            <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">
              {t('archives.shareArchive')}
            </h2>
            <p className="text-sm text-zinc-500 dark:text-zinc-400 truncate">
              {repo.name}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-400"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <div className="w-6 h-6 border-2 border-zinc-300 border-t-zinc-900 dark:border-zinc-700 dark:border-t-zinc-50 rounded-full animate-spin" />
            </div>
          ) : shareUrl ? (
            <div className="space-y-4">
              <div className="flex items-center gap-2 p-3 bg-zinc-100 dark:bg-zinc-800 rounded-lg">
                <LinkIcon className="w-4 h-4 text-zinc-400 flex-shrink-0" />
                <input
                  type="text"
                  value={shareUrl}
                  readOnly
                  className="flex-1 bg-transparent text-sm text-zinc-700 dark:text-zinc-300 outline-none truncate"
                />
                <button
                  onClick={handleCopy}
                  className="flex items-center gap-1 px-2 py-1 text-xs font-medium text-blue-500 hover:text-blue-600 bg-blue-50 dark:bg-blue-900/30 rounded transition-colors"
                >
                  {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                  {copied ? t('archives.copied') : t('archives.copy')}
                </button>
              </div>

              {expiresAt && (
                <div className="flex items-center gap-2 text-sm text-zinc-500 dark:text-zinc-400">
                  <Clock className="w-4 h-4" />
                  <span>{t('archives.expiresAt')}: {formatExpiresTime(expiresAt)}</span>
                </div>
              )}

              <button
                onClick={handleDeleteShare}
                className="w-full py-2 text-sm text-red-500 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
              >
                {t('archives.deleteShare')}
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              <p className="text-sm text-zinc-500 dark:text-zinc-400">
                {t('archives.selectExpiration')}
              </p>

              <div className="grid grid-cols-2 gap-2">
                {expireOptions.map((option) => (
                  <button
                    key={option.hours}
                    onClick={() => setSelectedHours(option.hours)}
                    className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                      selectedHours === option.hours
                        ? 'bg-blue-500 text-white'
                        : 'bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-200 dark:hover:bg-zinc-700'
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>

              <button
                onClick={handleCreateShare}
                disabled={creating}
                className="w-full py-2.5 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
              >
                {creating ? t('archives.creating') : t('archives.createShare')}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
