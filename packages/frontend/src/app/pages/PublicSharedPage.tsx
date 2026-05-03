import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router';
import { Star, ExternalLink, Github, Folder, AlertCircle } from 'lucide-react';
import { motion } from 'motion/react';
import { getPublicSharedCollection, type PublicCollectionResponse } from '../api';

const ICON_MAP: Record<string, React.ComponentType<{ className?: string }>> = {
  folder: Folder,
};

const PRESET_COLORS = [
  '#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6',
  '#EC4899', '#06B6D4', '#84CC16',
];

export function PublicSharedPage() {
  const { shareId } = useParams<{ shareId: string }>();
  const [collection, setCollection] = useState<PublicCollectionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!shareId) return;
    setLoading(true);
    getPublicSharedCollection(shareId)
      .then(setCollection)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [shareId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-zinc-300 border-t-zinc-900 dark:border-zinc-700 dark:border-t-zinc-50 rounded-full animate-spin" />
      </div>
    );
  }

  if (error || !collection) {
    return (
      <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 flex items-center justify-center p-6">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 mx-auto text-red-500 mb-4" />
          <h1 className="text-xl font-bold text-zinc-900 dark:text-zinc-50 mb-2">
            Collection Not Found
          </h1>
          <p className="text-zinc-500 dark:text-zinc-400">
            {error || 'This shared collection may have been removed or the link is invalid.'}
          </p>
        </div>
      </div>
    );
  }

  const color = collection.color || PRESET_COLORS[0];
  const Icon = ICON_MAP[collection.icon] || Folder;

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950">
      {/* Header */}
      <div className="bg-white dark:bg-zinc-900 border-b border-zinc-200 dark:border-zinc-800">
        <div className="max-w-5xl mx-auto px-6 py-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-start gap-4"
          >
            <div
              className="w-14 h-14 rounded-2xl flex items-center justify-center shrink-0"
              style={{ backgroundColor: `${color}20`, color }}
            >
              <Icon className="w-7 h-7" />
            </div>
            <div className="flex-1 min-w-0">
              <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50 mb-1">
                {collection.name}
              </h1>
              {collection.description && (
                <p className="text-zinc-600 dark:text-zinc-400 mb-3">
                  {collection.description}
                </p>
              )}
              <div className="flex items-center gap-4 text-sm">
                <span className="text-zinc-500 dark:text-zinc-400">
                  {collection.repo_count} repositories
                </span>
                {collection.tags.length > 0 && (
                  <div className="flex items-center gap-2">
                    {collection.tags.slice(0, 3).map((tag) => (
                      <span
                        key={tag}
                        className="px-2 py-0.5 bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 rounded-full text-xs"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        </div>
      </div>

      {/* Repositories */}
      <div className="max-w-5xl mx-auto px-6 py-8">
        {collection.repositories.length === 0 ? (
          <div className="text-center py-12 text-zinc-500 dark:text-zinc-400">
            No repositories in this collection
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {collection.repositories.map((repo, index) => (
              <motion.a
                key={repo.id}
                href={repo.url}
                target="_blank"
                rel="noopener noreferrer"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: Math.min(index * 0.05, 0.3) }}
                className="group bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-5 hover:shadow-md hover:border-zinc-300 dark:hover:border-zinc-700 transition-all"
              >
                <div className="flex items-start justify-between gap-4 mb-2">
                  <h3 className="font-semibold text-zinc-900 dark:text-zinc-50 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                    {repo.name}
                  </h3>
                  <ExternalLink className="w-4 h-4 text-zinc-400 opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
                </div>
                {repo.description && (
                  <p className="text-sm text-zinc-500 dark:text-zinc-400 line-clamp-2 mb-3">
                    {repo.description}
                  </p>
                )}
                {repo.notes && (
                  <p className="text-sm text-zinc-400 dark:text-zinc-500 italic mb-3">
                    Note: {repo.notes}
                  </p>
                )}
                <div className="flex items-center gap-4 text-xs text-zinc-500 dark:text-zinc-400">
                  {repo.language && (
                    <span className="px-2 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full">
                      {repo.language}
                    </span>
                  )}
                  <div className="flex items-center gap-1">
                    <Star className="w-3 h-3 fill-amber-400 text-amber-400" />
                    <span>{(repo.stars / 1000).toFixed(1)}k</span>
                  </div>
                </div>
              </motion.a>
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="border-t border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900">
        <div className="max-w-5xl mx-auto px-6 py-4 text-center text-sm text-zinc-500 dark:text-zinc-400">
          <div className="flex items-center justify-center gap-2">
            <Github className="w-4 h-4" />
            <span>Shared via StarMind</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default PublicSharedPage;
