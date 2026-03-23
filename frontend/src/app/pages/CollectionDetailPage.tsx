import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router';
import { ArrowLeft, Folder, ExternalLink, Trash2, Star, Activity } from 'lucide-react';
import { getCollection, getCollectionRepos, deleteCollection, type Collection, type CollectionRepo } from '../api';

export function CollectionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [collection, setCollection] = useState<Collection | null>(null);
  const [repos, setRepos] = useState<CollectionRepo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);

  useEffect(() => {
    if (!id) return;
    setLoading(true);

    Promise.all([
      getCollection(id),
      getCollectionRepos(id, 1, 20)
    ])
      .then(([collectionData, reposData]) => {
        setCollection(collectionData);
        setRepos(reposData.repositories);
        setHasMore(reposData.has_more);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [id]);

  const loadMore = async () => {
    if (!id || loadingMore) return;
    setLoadingMore(true);
    const nextPage = page + 1;
    try {
      const data = await getCollectionRepos(id, nextPage, 20);
      setRepos(prev => [...prev, ...data.repositories]);
      setHasMore(data.has_more);
      setPage(nextPage);
    } catch (err) {
      console.error('Failed to load more:', err);
    } finally {
      setLoadingMore(false);
    }
  };

  const handleDeleteCollection = async () => {
    if (!collection || !confirm(`Delete collection "${collection.name}"? This cannot be undone.`)) return;
    try {
      await deleteCollection(collection.id);
      window.history.back();
    } catch (err: any) {
      setError(err.message);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="w-8 h-8 border-2 border-zinc-300 border-t-zinc-900 dark:border-zinc-700 dark:border-t-zinc-50 rounded-full animate-spin" />
      </div>
    );
  }

  if (error || !collection) {
    return (
      <div className="max-w-5xl mx-auto py-8 px-6 text-center">
        <p className="text-red-500">{error || 'Collection not found'}</p>
        <Link to="/collections" className="text-blue-500 hover:underline mt-4 inline-block">← Back to collections</Link>
      </div>
    );
  }

  return (
    <div className="w-full max-w-[1520px] mx-auto py-8 px-6 xl:px-10">
      {/* Breadcrumb */}
      <div className="mb-6 flex items-center gap-4">
        <Link
          to="/collections"
          className="inline-flex items-center justify-center w-8 h-8 rounded-full hover:bg-zinc-100 dark:hover:bg-zinc-900 text-zinc-500 transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div className="flex items-center gap-3 text-sm text-zinc-500 dark:text-zinc-400 font-medium">
          <Link to="/collections" className="hover:text-zinc-900 dark:hover:text-zinc-50 transition-colors">Collections</Link>
          <span>/</span>
          <span className="text-zinc-900 dark:text-zinc-50">{collection.name}</span>
        </div>
      </div>

      {/* Header */}
      <div className="mb-8">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-4">
            <div
              className="w-14 h-14 rounded-2xl flex items-center justify-center"
              style={{ backgroundColor: `${collection.color}20`, color: collection.color }}
            >
              <Folder className="w-7 h-7" />
            </div>
            <div>
              <h1 className="text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
                {collection.name}
              </h1>
              <p className="text-zinc-500 dark:text-zinc-400 mt-1">
                {collection.repo_count} repositories
              </p>
            </div>
          </div>
          <button
            onClick={handleDeleteCollection}
            className="flex items-center gap-2 px-4 py-2 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950 rounded-xl font-medium transition-colors"
          >
            <Trash2 className="w-4 h-4" />
            Delete
          </button>
        </div>

        {collection.description && (
          <p className="text-zinc-600 dark:text-zinc-400 mt-4 text-lg max-w-3xl">
            {collection.description}
          </p>
        )}

        {collection.tags.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-4">
            {collection.tags.map(tag => (
              <span
                key={tag}
                className="px-3 py-1 text-sm bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 rounded-full"
              >
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Repositories List */}
      {repos.length === 0 ? (
        <div className="text-center py-20 bg-zinc-50 dark:bg-zinc-900 rounded-2xl border border-zinc-200 dark:border-zinc-800">
          <Folder className="w-12 h-12 mx-auto text-zinc-300 dark:text-zinc-700 mb-4" />
          <h3 className="text-lg font-medium text-zinc-900 dark:text-zinc-50 mb-2">
            No repositories yet
          </h3>
          <p className="text-zinc-500 dark:text-zinc-400 mb-6">
            Add repositories from the repository detail page
          </p>
          <Link
            to="/repositories"
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-xl font-medium transition-colors"
          >
            Browse Repositories
          </Link>
        </div>
      ) : (
        <div className="space-y-4">
          {repos.map(repo => (
            <RepoRow key={repo.id} repo={repo} collectionId={collection.id} />
          ))}

          {hasMore && (
            <div className="text-center pt-4">
              <button
                onClick={loadMore}
                disabled={loadingMore}
                className="px-6 py-2 bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 text-zinc-700 dark:text-zinc-300 rounded-xl font-medium transition-colors disabled:opacity-50"
              >
                {loadingMore ? 'Loading...' : 'Load More'}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function RepoRow({ repo, collectionId }: { repo: CollectionRepo; collectionId: string }) {
  return (
    <Link
      to={`/repositories/${repo.id}`}
      className="block bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-4 hover:shadow-md transition-shadow"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 mb-1">
            <h3 className="font-semibold text-zinc-900 dark:text-zinc-50 truncate">
              {repo.name}
            </h3>
            {repo.language && (
              <span className="px-2 py-0.5 text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full">
                {repo.language}
              </span>
            )}
          </div>
          {repo.description && (
            <p className="text-sm text-zinc-500 dark:text-zinc-400 line-clamp-2">
              {repo.description}
            </p>
          )}
          {repo.notes && (
            <p className="text-sm text-zinc-400 dark:text-zinc-500 mt-2 italic">
              Note: {repo.notes}
            </p>
          )}
        </div>
        <div className="flex items-center gap-4 text-sm text-zinc-500 dark:text-zinc-400 shrink-0">
          <div className="flex items-center gap-1">
            <Star className="w-4 h-4 fill-amber-400 text-amber-400" />
            <span>{(repo.stars / 1000).toFixed(1)}k</span>
          </div>
          <ExternalLink className="w-4 h-4" />
        </div>
      </div>
    </Link>
  );
}

export default CollectionDetailPage;
