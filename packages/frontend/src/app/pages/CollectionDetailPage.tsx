import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router';
import {
  ArrowLeft,
  ExternalLink,
  Trash2,
  Star,
  Edit3,
  X,
  Plus,
  Share2,
  Copy,
  Check,
  Link as LinkIcon,
  Sparkles,
  Tag as TagIcon,
  Filter,
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import ReactMarkdown from 'react-markdown';
import {
  getCollection,
  getCollectionRepos,
  deleteCollection,
  updateCollection,
  removeRepoFromCollection,
  getShareStatus,
  createShare,
  deleteShare,
  updateCollectionOverview,
  generateCollectionOverview,
  updateRepoTags,
  getCollectionRepoTags,
  type Collection,
  type CollectionRepo,
} from '../api';
import { useInfiniteScroll } from '../hooks/useInfiniteScroll';
import { cn } from '../utils';

const PRESET_COLORS = [
  '#3B82F6',
  '#10B981',
  '#F59E0B',
  '#EF4444',
  '#8B5CF6',
  '#EC4899',
  '#06B6D4',
  '#84CC16',
];

const ICON_MAP: Record<string, React.ComponentType<{ className?: string }>> = {
  folder: () => <svg viewBox="0 0 24 24" fill="currentColor" className="w-7 h-7"><path d="M10 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"/></svg>,
  star: Star,
  heart: () => <svg viewBox="0 0 24 24" fill="currentColor" className="w-7 h-7"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>,
  bookmark: () => <svg viewBox="0 0 24 24" fill="currentColor" className="w-7 h-7"><path d="M17 3H7c-1.1 0-2 .9-2 2v16l7-3 7 3V5c0-1.1-.9-2-2-2z"/></svg>,
  tag: () => <svg viewBox="0 0 24 24" fill="currentColor" className="w-7 h-7"><path d="M21.41 11.58l-9-9C12.05 2.22 11.55 2 11 2H4c-1.1 0-2 .9-2 2v7c0 .55.22 1.05.59 1.42l9 9c.36.36.86.58 1.41.58s1.05-.22 1.41-.59l7-7c.37-.36.59-.86.59-1.41s-.23-1.06-.59-1.42z"/></svg>,
  briefcase: () => <svg viewBox="0 0 24 24" fill="currentColor" className="w-7 h-7"><path d="M20 6h-4V4c0-1.1-.9-2-2-2h-4c-1.1 0-2 .9-2 2v2H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2zM10 4h4v2h-4V4z"/></svg>,
  code: () => <svg viewBox="0 0 24 24" fill="currentColor" className="w-7 h-7"><path d="M9.4 16.6L4.8 12l4.6-4.6L8 6l-6 6 6 6 1.4-1.4zm5.2 0l4.6-4.6-4.6-4.6L16 6l6 6-6 6-1.4-1.4z"/></svg>,
  zap: () => <svg viewBox="0 0 24 24" fill="currentColor" className="w-7 h-7"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>,
};

function renderIcon(iconName: string, className?: string) {
  const Icon = ICON_MAP[iconName];
  if (!Icon) return <svg viewBox="0 0 24 24" fill="currentColor" className={className}><path d="M10 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z"/></svg>;
  return <Icon className={className} />;
}

const modalBackdropVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1 }
};

const modalContentVariants = {
  hidden: { opacity: 0, scale: 0.95, y: 20 },
  visible: { opacity: 1, scale: 1, y: 0, transition: { duration: 0.2, ease: 'easeOut' } },
  exit: { opacity: 0, scale: 0.95, y: 20, transition: { duration: 0.15, ease: 'easeIn' } }
};

export function CollectionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [collection, setCollection] = useState<Collection | null>(null);
  const [repos, setRepos] = useState<CollectionRepo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);

  // Edit form state
  const [editName, setEditName] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [editTags, setEditTags] = useState<string[]>([]);
  const [editColor, setEditColor] = useState(PRESET_COLORS[0]);
  const [editIcon, setEditIcon] = useState('folder');
  const [saving, setSaving] = useState(false);

  // Share state
  const [shareStatus, setShareStatus] = useState<{ is_shared: boolean; share_id: string | null; view_count: number } | null>(null);
  const [showShareModal, setShowShareModal] = useState(false);
  const [copied, setCopied] = useState(false);

  // Overview expand/collapse state
  const [overviewExpanded, setOverviewExpanded] = useState(false);
  const OVERVIEW_MAX_HEIGHT = 300; // pixels

  // Check if overview is long (roughly estimate by character count)
  const isOverviewLong = collection?.ai_introduction && collection.ai_introduction.length > 800;
  const [showOverviewEditModal, setShowOverviewEditModal] = useState(false);
  const [showAiGenerateModal, setShowAiGenerateModal] = useState(false);
  const [overviewContent, setOverviewContent] = useState('');
  const [savingOverview, setSavingOverview] = useState(false);
  const [aiPrompt, setAiPrompt] = useState('');
  const [generating, setGenerating] = useState(false);
  const [generatedContent, setGeneratedContent] = useState('');

  // Tag filter state
  const [allRepoTags, setAllRepoTags] = useState<string[]>([]);
  const [selectedFilterTags, setSelectedFilterTags] = useState<string[]>([]);

  useEffect(() => {
    if (!id) return;
    setLoading(true);

    Promise.all([
      getCollection(id),
      getCollectionRepos(id, 1, 20, selectedFilterTags),
      getShareStatus(id),
      getCollectionRepoTags(id),
    ])
      .then(([collectionData, reposData, shareData, tagsData]) => {
        setCollection(collectionData);
        setRepos(reposData.repositories);
        setHasMore(reposData.has_more);
        // Initialize edit form
        setEditName(collectionData.name);
        setEditDescription(collectionData.description);
        setEditTags(collectionData.tags);
        setEditColor(collectionData.color || PRESET_COLORS[0]);
        setEditIcon(collectionData.icon || 'folder');
        // Initialize share status
        setShareStatus(shareData);
        // Initialize overview
        setOverviewContent(collectionData.ai_introduction || '');
        // Initialize repo tags
        setAllRepoTags(tagsData.tags);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [id]);

  // Reload repos when filter tags change
  useEffect(() => {
    if (!id) return;
    setPage(1);
    getCollectionRepos(id, 1, 20, selectedFilterTags)
      .then((data) => {
        setRepos(data.repositories);
        setHasMore(data.has_more);
      })
      .catch((err) => console.error('Failed to reload repos:', err));
  }, [id, selectedFilterTags]);

  const loadMore = async () => {
    if (!id || loadingMore) return;
    setLoadingMore(true);
    const nextPage = page + 1;
    try {
      const data = await getCollectionRepos(id, nextPage, 20, selectedFilterTags);
      setRepos(prev => [...prev, ...data.repositories]);
      setHasMore(data.has_more);
      setPage(nextPage);
    } catch (err) {
      console.error('Failed to load more:', err);
    } finally {
      setLoadingMore(false);
    }
  };

  const sentinelRef = useInfiniteScroll({
    onLoadMore: loadMore,
    hasMore,
    loading: loadingMore,
  });

  const handleDeleteCollection = async () => {
    if (!collection || !confirm(`Delete collection "${collection.name}"? This cannot be undone.`)) return;
    try {
      await deleteCollection(collection.id);
      window.history.back();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleEditCollection = async () => {
    if (!collection || !editName.trim()) return;
    setSaving(true);
    try {
      await updateCollection(collection.id, {
        name: editName,
        description: editDescription,
        tags: editTags,
        color: editColor,
        icon: editIcon,
      });
      const updated = await getCollection(collection.id);
      setCollection(updated);
      setShowEditModal(false);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleRemoveRepo = async (repoId: string, repoName: string) => {
    if (!collection || !confirm(`Remove "${repoName}" from this collection?`)) return;
    try {
      await removeRepoFromCollection(collection.id, parseInt(repoId));
      setRepos(prev => prev.filter(r => r.id !== repoId));
      // Update collection repo_count
      const updated = await getCollection(collection.id);
      setCollection(updated);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleCreateShare = async () => {
    if (!id) return;
    try {
      const share = await createShare(id);
      setShareStatus({ is_shared: true, share_id: share.share_id, view_count: 0 });
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleDeleteShare = async () => {
    if (!id || !confirm('Remove public access to this collection?')) return;
    try {
      await deleteShare(id);
      setShareStatus({ is_shared: false, share_id: null, view_count: 0 });
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleCopyShareLink = () => {
    if (!shareStatus?.share_id) return;
    const url = `${window.location.origin}/shared/${shareStatus.share_id}`;
    navigator.clipboard.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleSaveOverview = async () => {
    if (!collection) return;
    setSavingOverview(true);
    try {
      const updated = await updateCollectionOverview(collection.id, overviewContent);
      setCollection(updated);
      setShowOverviewEditModal(false);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSavingOverview(false);
    }
  };

  const handleGenerateOverview = async () => {
    if (!collection) return;
    setGenerating(true);
    try {
      const result = await generateCollectionOverview(collection.id, aiPrompt);
      setGeneratedContent(result.content);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setGenerating(false);
    }
  };

  const handleAcceptGeneratedOverview = async () => {
    if (!collection) return;
    setSavingOverview(true);
    try {
      const updated = await updateCollectionOverview(collection.id, generatedContent);
      setCollection(updated);
      setOverviewContent(generatedContent);
      setShowAiGenerateModal(false);
      setAiPrompt('');
      setGeneratedContent('');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSavingOverview(false);
    }
  };

  const handleUpdateRepoTags = async (repoId: string, newTags: string[]) => {
    if (!collection) return;
    try {
      await updateRepoTags(collection.id, repoId, newTags);
      // Update local state
      setRepos(prev => prev.map(r =>
        r.id === repoId ? { ...r, repo_tags: newTags } : r
      ));
      // Refresh all repo tags
      const tagsData = await getCollectionRepoTags(collection.id);
      setAllRepoTags(tagsData.tags);
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
      <motion.div
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        className="mb-6 flex items-center gap-4"
      >
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
      </motion.div>

      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-4">
            <div
              className="w-14 h-14 rounded-2xl flex items-center justify-center"
              style={{ backgroundColor: `${collection.color}20`, color: collection.color }}
            >
              {renderIcon(collection.icon || 'folder', 'w-7 h-7')}
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
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowShareModal(true)}
              className="flex items-center gap-2 px-4 py-2 text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-950 rounded-xl font-medium transition-colors"
            >
              <Share2 className="w-4 h-4" />
              Share
            </button>
            <button
              onClick={() => setShowEditModal(true)}
              className="flex items-center gap-2 px-4 py-2 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-xl font-medium transition-colors"
            >
              <Edit3 className="w-4 h-4" />
              Edit
            </button>
            <button
              onClick={handleDeleteCollection}
              className="flex items-center gap-2 px-4 py-2 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950 rounded-xl font-medium transition-colors"
            >
              <Trash2 className="w-4 h-4" />
              Delete
            </button>
          </div>
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
      </motion.div>

      {/* Overview Card */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="mb-8 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl overflow-hidden"
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-200 dark:border-zinc-800">
          <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50 flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-blue-500" />
            Overview
          </h2>
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                setAiPrompt('');
                setGeneratedContent('');
                setShowAiGenerateModal(true);
              }}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-950 rounded-lg font-medium transition-colors"
            >
              <Sparkles className="w-4 h-4" />
              AI Generate
            </button>
            <button
              onClick={() => {
                setOverviewContent(collection.ai_introduction || '');
                setShowOverviewEditModal(true);
              }}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-lg font-medium transition-colors"
            >
              <Edit3 className="w-4 h-4" />
              Edit
            </button>
          </div>
        </div>
        <div className="px-6 py-4">
          {collection.ai_introduction ? (
            <div>
              <div
                className={cn(
                  "prose prose-zinc dark:prose-invert max-w-none prose-headings:text-zinc-900 dark:prose-headings:text-zinc-50 prose-p:text-zinc-600 dark:prose-p:text-zinc-400 prose-li:text-zinc-600 dark:prose-li:text-zinc-400 overflow-hidden transition-all duration-300",
                  !overviewExpanded && isOverviewLong && "max-h-[300px] relative"
                )}
              >
                <ReactMarkdown>{collection.ai_introduction}</ReactMarkdown>
                {!overviewExpanded && isOverviewLong && (
                  <div className="absolute bottom-0 left-0 right-0 h-24 bg-gradient-to-t from-white dark:from-zinc-900 to-transparent pointer-events-none" />
                )}
              </div>
              {isOverviewLong && (
                <button
                  onClick={() => setOverviewExpanded(!overviewExpanded)}
                  className="mt-3 text-sm text-blue-600 dark:text-blue-400 hover:underline font-medium"
                >
                  {overviewExpanded ? '收起' : '展开全部'}
                </button>
              )}
            </div>
          ) : (
            <div className="text-center py-8 text-zinc-400 dark:text-zinc-500">
              <Sparkles className="w-10 h-10 mx-auto mb-3 opacity-50" />
              <p>No overview yet. Use AI to generate one or write your own.</p>
            </div>
          )}
        </div>
      </motion.div>

      {/* Tag Filter */}
      {allRepoTags.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="mb-6 flex items-center gap-3"
        >
          <Filter className="w-4 h-4 text-zinc-400" />
          <div className="flex flex-wrap gap-2">
            {allRepoTags.map(tag => (
              <button
                key={tag}
                onClick={() => {
                  setSelectedFilterTags(prev =>
                    prev.includes(tag)
                      ? prev.filter(t => t !== tag)
                      : [...prev, tag]
                  );
                }}
                className={`px-3 py-1 text-sm rounded-full transition-colors ${
                  selectedFilterTags.includes(tag)
                    ? 'bg-blue-500 text-white'
                    : 'bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 hover:bg-zinc-200 dark:hover:bg-zinc-700'
                }`}
              >
                {tag}
              </button>
            ))}
            {selectedFilterTags.length > 0 && (
              <button
                onClick={() => setSelectedFilterTags([])}
                className="px-3 py-1 text-sm text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300 transition-colors"
              >
                Clear
              </button>
            )}
          </div>
        </motion.div>
      )}

      {/* Repositories List */}
      {repos.length === 0 ? (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-center py-20 bg-zinc-50 dark:bg-zinc-900 rounded-2xl border border-zinc-200 dark:border-zinc-800"
        >
          <div className="w-12 h-12 mx-auto text-zinc-300 dark:text-zinc-700 mb-4 flex items-center justify-center">
            {renderIcon(collection.icon || 'folder', 'w-12 h-12')}
          </div>
          <h3 className="text-lg font-medium text-zinc-900 dark:text-zinc-50 mb-2">
            {selectedFilterTags.length > 0 ? 'No matching repositories' : 'No repositories yet'}
          </h3>
          <p className="text-zinc-500 dark:text-zinc-400 mb-6">
            {selectedFilterTags.length > 0
              ? 'Try different tags or clear the filter'
              : 'Add repositories from the repository detail page'}
          </p>
          {selectedFilterTags.length > 0 ? (
            <button
              onClick={() => setSelectedFilterTags([])}
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-xl font-medium transition-colors"
            >
              Clear Filter
            </button>
          ) : (
            <Link
              to="/repositories"
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-xl font-medium transition-colors"
            >
              <Plus className="w-4 h-4" />
              Browse Repositories
            </Link>
          )}
        </motion.div>
      ) : (
        <div className="space-y-4">
          <AnimatePresence>
            {repos.map((repo, index) => (
              <motion.div
                key={repo.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ delay: Math.min(index * 0.05, 0.3) }}
              >
                <RepoRow
                  repo={repo}
                  onRemove={() => handleRemoveRepo(repo.id, repo.name)}
                  onUpdateTags={(tags) => handleUpdateRepoTags(repo.id, tags)}
                />
              </motion.div>
            ))}
          </AnimatePresence>

          {/* Infinite scroll sentinel */}
          <div ref={sentinelRef} className="h-4" />

          {loadingMore && (
            <div className="text-center py-4">
              <div className="w-6 h-6 border-2 border-zinc-300 border-t-zinc-900 dark:border-zinc-700 dark:border-t-zinc-50 rounded-full animate-spin mx-auto" />
            </div>
          )}

          {!hasMore && repos.length > 0 && (
            <p className="text-center text-sm text-zinc-400 py-4">
              You've reached the end
            </p>
          )}
        </div>
      )}

      {/* Edit Modal */}
      <AnimatePresence>
        {showEditModal && (
          <motion.div
            variants={modalBackdropVariants}
            initial="hidden"
            animate="visible"
            exit="hidden"
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
            onClick={(e) => e.target === e.currentTarget && setShowEditModal(false)}
          >
            <motion.div
              variants={modalContentVariants}
              initial="hidden"
              animate="visible"
              exit="exit"
              className="bg-white dark:bg-zinc-900 rounded-2xl shadow-xl w-full max-w-md mx-4 overflow-hidden"
            >
              <EditCollectionModalContent
                name={editName}
                setName={setEditName}
                description={editDescription}
                setDescription={setEditDescription}
                tags={editTags}
                setTags={setEditTags}
                color={editColor}
                setColor={setEditColor}
                icon={editIcon}
                setIcon={setEditIcon}
                saving={saving}
                onSave={handleEditCollection}
                onClose={() => setShowEditModal(false)}
              />
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Share Modal */}
      <AnimatePresence>
        {showShareModal && (
          <motion.div
            variants={modalBackdropVariants}
            initial="hidden"
            animate="visible"
            exit="hidden"
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
            onClick={(e) => e.target === e.currentTarget && setShowShareModal(false)}
          >
            <motion.div
              variants={modalContentVariants}
              initial="hidden"
              animate="visible"
              exit="exit"
              className="bg-white dark:bg-zinc-900 rounded-2xl shadow-xl w-full max-w-md mx-4 overflow-hidden"
            >
              <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-200 dark:border-zinc-800">
                <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">
                  Share Collection
                </h2>
                <button
                  onClick={() => setShowShareModal(false)}
                  className="p-1.5 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-400 transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="p-6 space-y-4">
                {shareStatus?.is_shared ? (
                  <>
                    <p className="text-sm text-zinc-600 dark:text-zinc-400">
                      This collection is publicly accessible via the link below.
                    </p>
                    <div className="flex items-center gap-2">
                      <input
                        type="text"
                        readOnly
                        value={`${window.location.origin}/shared/${shareStatus.share_id}`}
                        className="flex-1 px-3 py-2 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-lg text-sm text-zinc-600 dark:text-zinc-400"
                      />
                      <button
                        onClick={handleCopyShareLink}
                        className="flex items-center gap-2 px-3 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm font-medium transition-colors"
                      >
                        {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                      </button>
                    </div>
                    <div className="flex items-center justify-between text-sm text-zinc-500 dark:text-zinc-400">
                      <span>{shareStatus.view_count} views</span>
                    </div>
                    <button
                      onClick={handleDeleteShare}
                      className="w-full flex items-center justify-center gap-2 px-4 py-2 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950 rounded-lg text-sm font-medium transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                      Remove Public Access
                    </button>
                  </>
                ) : (
                  <>
                    <p className="text-sm text-zinc-600 dark:text-zinc-400">
                      Create a public link to share this collection with others.
                      Anyone with the link will be able to view the repositories.
                    </p>
                    <button
                      onClick={handleCreateShare}
                      className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm font-medium transition-colors"
                    >
                      <Share2 className="w-4 h-4" />
                      Create Share Link
                    </button>
                  </>
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Overview Edit Modal */}
      <AnimatePresence>
        {showOverviewEditModal && (
          <motion.div
            variants={modalBackdropVariants}
            initial="hidden"
            animate="visible"
            exit="hidden"
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
            onClick={(e) => e.target === e.currentTarget && setShowOverviewEditModal(false)}
          >
            <motion.div
              variants={modalContentVariants}
              initial="hidden"
              animate="visible"
              exit="exit"
              className="bg-white dark:bg-zinc-900 rounded-2xl shadow-xl w-full max-w-2xl mx-4 overflow-hidden"
            >
              <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-200 dark:border-zinc-800">
                <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">
                  Edit Overview
                </h2>
                <button
                  onClick={() => setShowOverviewEditModal(false)}
                  className="p-1.5 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-400 transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              <div className="p-6">
                <textarea
                  value={overviewContent}
                  onChange={(e) => setOverviewContent(e.target.value)}
                  placeholder="Write your overview in Markdown..."
                  rows={12}
                  className="w-full px-4 py-3 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-xl text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                />
              </div>
              <div className="px-6 py-4 bg-zinc-50 dark:bg-zinc-900/50 border-t border-zinc-200 dark:border-zinc-800 flex justify-end gap-3">
                <button
                  onClick={() => setShowOverviewEditModal(false)}
                  className="px-4 py-2 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-lg text-sm font-medium transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveOverview}
                  disabled={savingOverview}
                  className="px-4 py-2 bg-blue-500 hover:bg-blue-600 disabled:bg-zinc-300 dark:disabled:bg-zinc-700 text-white rounded-lg text-sm font-medium transition-colors disabled:cursor-not-allowed"
                >
                  {savingOverview ? 'Saving...' : 'Save'}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* AI Generate Modal */}
      <AnimatePresence>
        {showAiGenerateModal && (
          <motion.div
            variants={modalBackdropVariants}
            initial="hidden"
            animate="visible"
            exit="hidden"
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
            onClick={(e) => e.target === e.currentTarget && setShowAiGenerateModal(false)}
          >
            <motion.div
              variants={modalContentVariants}
              initial="hidden"
              animate="visible"
              exit="exit"
              className="bg-white dark:bg-zinc-900 rounded-2xl shadow-xl w-full max-w-2xl mx-4 overflow-hidden max-h-[90vh] flex flex-col"
            >
              <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-200 dark:border-zinc-800 shrink-0">
                <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50 flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-blue-500" />
                  AI Generate Overview
                </h2>
                <button
                  onClick={() => setShowAiGenerateModal(false)}
                  className="p-1.5 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-400 transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              <div className="p-6 overflow-y-auto flex-1">
                <div className="mb-4">
                  <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-1.5">
                    Prompt (optional)
                  </label>
                  <textarea
                    value={aiPrompt}
                    onChange={(e) => setAiPrompt(e.target.value)}
                    placeholder="e.g., Focus on the most useful tools for web development..."
                    rows={2}
                    className="w-full px-3 py-2 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                  />
                </div>
                <button
                  onClick={handleGenerateOverview}
                  disabled={generating}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 disabled:bg-zinc-300 dark:disabled:bg-zinc-700 text-white rounded-lg text-sm font-medium transition-colors disabled:cursor-not-allowed"
                >
                  {generating ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      Generating...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4" />
                      Generate
                    </>
                  )}
                </button>

                {generatedContent && (
                  <div className="mt-6">
                    <h3 className="text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-2">
                      Generated Overview
                    </h3>
                    <div className="bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-xl p-4 max-h-80 overflow-y-auto">
                      <div className="prose prose-zinc dark:prose-invert max-w-none prose-sm">
                        <ReactMarkdown>{generatedContent}</ReactMarkdown>
                      </div>
                    </div>
                  </div>
                )}
              </div>
              {generatedContent && (
                <div className="px-6 py-4 bg-zinc-50 dark:bg-zinc-900/50 border-t border-zinc-200 dark:border-zinc-800 flex justify-end gap-3 shrink-0">
                  <button
                    onClick={() => setGeneratedContent('')}
                    className="px-4 py-2 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-lg text-sm font-medium transition-colors"
                  >
                    Regenerate
                  </button>
                  <button
                    onClick={handleAcceptGeneratedOverview}
                    disabled={savingOverview}
                    className="px-4 py-2 bg-blue-500 hover:bg-blue-600 disabled:bg-zinc-300 dark:disabled:bg-zinc-700 text-white rounded-lg text-sm font-medium transition-colors disabled:cursor-not-allowed"
                  >
                    {savingOverview ? 'Saving...' : 'Accept & Save'}
                  </button>
                </div>
              )}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function RepoRow({
  repo,
  onRemove,
  onUpdateTags
}: {
  repo: CollectionRepo;
  onRemove: () => void;
  onUpdateTags: (tags: string[]) => void;
}) {
  const [showRemove, setShowRemove] = useState(false);
  const [showTagEdit, setShowTagEdit] = useState(false);
  const [tagInput, setTagInput] = useState('');
  const [editingTags, setEditingTags] = useState<string[]>([]);

  const handleAddTag = () => {
    const tag = tagInput.trim();
    if (tag && !editingTags.includes(tag)) {
      const newTags = [...editingTags, tag];
      setEditingTags(newTags);
      onUpdateTags(newTags);
      setTagInput('');
    }
  };

  const handleRemoveTag = (tag: string) => {
    const newTags = editingTags.filter(t => t !== tag);
    setEditingTags(newTags);
    onUpdateTags(newTags);
  };

  const startTagEdit = () => {
    setEditingTags(repo.repo_tags || []);
    setShowTagEdit(true);
  };

  return (
    <div
      className="group relative bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl p-4 hover:shadow-md hover:border-zinc-300 dark:hover:border-zinc-700 transition-all"
      onMouseEnter={() => setShowRemove(true)}
      onMouseLeave={() => setShowRemove(false)}
    >
      <Link
        to={`/repositories/${repo.id}`}
        className="block"
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
            {/* Repo Tags */}
            {(repo.repo_tags && repo.repo_tags.length > 0) && (
              <div className="flex items-center gap-1.5 mt-2 flex-wrap">
                {repo.repo_tags.map(tag => (
                  <span
                    key={tag}
                    className="px-2 py-0.5 text-xs bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 rounded-full"
                  >
                    {tag}
                  </span>
                ))}
              </div>
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

      {/* Action buttons */}
      <AnimatePresence>
        {showRemove && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="absolute top-3 right-3 flex items-center gap-1"
          >
            <button
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                startTagEdit();
              }}
              className="p-1.5 rounded-lg bg-zinc-100 dark:bg-zinc-800 text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300 hover:bg-zinc-200 dark:hover:bg-zinc-700 transition-colors"
              title="Edit tags"
            >
              <TagIcon className="w-4 h-4" />
            </button>
            <motion.button
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              transition={{ duration: 0.15 }}
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                onRemove();
              }}
              className="p-1.5 rounded-lg bg-red-50 dark:bg-red-950 text-red-500 hover:bg-red-100 dark:hover:bg-red-900 transition-colors"
            >
              <X className="w-4 h-4" />
            </motion.button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Tag Edit Modal */}
      <AnimatePresence>
        {showTagEdit && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
            onClick={(e) => {
              e.stopPropagation();
              setShowTagEdit(false);
            }}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="bg-white dark:bg-zinc-900 rounded-2xl shadow-xl w-full max-w-sm mx-4 overflow-hidden"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-200 dark:border-zinc-800">
                <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">
                  Edit Tags
                </h2>
                <button
                  onClick={() => setShowTagEdit(false)}
                  className="p-1.5 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-400 transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              <div className="p-6">
                <div className="flex gap-2 mb-3">
                  <input
                    type="text"
                    value={tagInput}
                    onChange={(e) => setTagInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddTag())}
                    placeholder="Add a tag..."
                    className="flex-1 px-3 py-2 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <button
                    onClick={handleAddTag}
                    className="px-3 py-2 bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 text-zinc-700 dark:text-zinc-300 rounded-lg text-sm font-medium transition-colors"
                  >
                    Add
                  </button>
                </div>
                {editingTags.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {editingTags.map((tag) => (
                      <span
                        key={tag}
                        className="inline-flex items-center gap-1 px-2 py-0.5 bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 text-xs rounded-full"
                      >
                        {tag}
                        <button
                          onClick={() => handleRemoveTag(tag)}
                          className="hover:text-red-500 transition-colors"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </span>
                    ))}
                  </div>
                )}
              </div>
              <div className="px-6 py-4 bg-zinc-50 dark:bg-zinc-900/50 border-t border-zinc-200 dark:border-zinc-800 flex justify-end">
                <button
                  onClick={() => setShowTagEdit(false)}
                  className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm font-medium transition-colors"
                >
                  Done
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function EditCollectionModalContent({
  name,
  setName,
  description,
  setDescription,
  tags,
  setTags,
  color,
  setColor,
  icon,
  setIcon,
  saving,
  onSave,
  onClose,
}: {
  name: string;
  setName: (v: string) => void;
  description: string;
  setDescription: (v: string) => void;
  tags: string[];
  setTags: (v: string[]) => void;
  color: string;
  setColor: (v: string) => void;
  icon: string;
  setIcon: (v: string) => void;
  saving: boolean;
  onSave: () => void;
  onClose: () => void;
}) {
  const [tagInput, setTagInput] = useState('');

  const addTag = () => {
    const tag = tagInput.trim();
    if (tag && !tags.includes(tag)) {
      setTags([...tags, tag]);
      setTagInput('');
    }
  };

  const removeTag = (tag: string) => {
    setTags(tags.filter((t) => t !== tag));
  };

  return (
    <>
      <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-200 dark:border-zinc-800">
        <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">
          Edit Collection
        </h2>
        <button
          onClick={onClose}
          className="p-1.5 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-400 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      <div className="p-6 space-y-4 max-h-[60vh] overflow-y-auto">
        {/* Name */}
        <div>
          <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-1.5">
            Name *
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g., AI Tools"
            className="w-full px-3 py-2 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* Description */}
        <div>
          <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-1.5">
            Description
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="What's this collection about?"
            rows={2}
            className="w-full px-3 py-2 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
          />
        </div>

        {/* Tags */}
        <div>
          <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-1.5">
            Tags
          </label>
          <div className="flex gap-2 mb-2">
            <input
              type="text"
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addTag())}
              placeholder="Add a tag..."
              className="flex-1 px-3 py-2 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              onClick={addTag}
              className="px-3 py-2 bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 text-zinc-700 dark:text-zinc-300 rounded-lg text-sm font-medium transition-colors"
            >
              Add
            </button>
          </div>
          {tags.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {tags.map((tag) => (
                <span
                  key={tag}
                  className="inline-flex items-center gap-1 px-2 py-0.5 bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 text-xs rounded-full"
                >
                  {tag}
                  <button
                    onClick={() => removeTag(tag)}
                    className="hover:text-red-500 transition-colors"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Icon */}
        <div>
          <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-1.5">
            Icon
          </label>
          <div className="flex gap-2">
            {Object.entries(ICON_MAP).map(([iconName, IconComponent]) => (
              <button
                key={iconName}
                type="button"
                onClick={() => setIcon(iconName)}
                className={`w-10 h-10 rounded-xl flex items-center justify-center transition-all ${
                  icon === iconName
                    ? 'ring-2 ring-offset-2 ring-zinc-400 dark:ring-offset-zinc-900 scale-110'
                    : 'hover:scale-105'
                }`}
                style={{
                  backgroundColor: icon === iconName ? `${color}20` : 'transparent',
                  color: color
                }}
              >
                <IconComponent className="w-5 h-5" />
              </button>
            ))}
          </div>
        </div>

        {/* Color */}
        <div>
          <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-1.5">
            Color
          </label>
          <div className="flex gap-2">
            {PRESET_COLORS.map((c) => (
              <button
                key={c}
                type="button"
                onClick={() => setColor(c)}
                className={`w-8 h-8 rounded-lg transition-transform ${
                  color === c
                    ? 'ring-2 ring-offset-2 ring-zinc-400 dark:ring-offset-zinc-900 scale-110'
                    : 'hover:scale-105'
                }`}
                style={{ backgroundColor: c }}
              />
            ))}
          </div>
        </div>
      </div>

      <div className="px-6 py-4 bg-zinc-50 dark:bg-zinc-900/50 border-t border-zinc-200 dark:border-zinc-800 flex justify-end gap-3">
        <button
          onClick={onClose}
          className="px-4 py-2 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-lg text-sm font-medium transition-colors"
        >
          Cancel
        </button>
        <button
          onClick={onSave}
          disabled={!name.trim() || saving}
          className="px-4 py-2 bg-blue-500 hover:bg-blue-600 disabled:bg-zinc-300 dark:disabled:bg-zinc-700 text-white rounded-lg text-sm font-medium transition-colors disabled:cursor-not-allowed"
        >
          {saving ? 'Saving...' : 'Save'}
        </button>
      </div>
    </>
  );
}

export default CollectionDetailPage;
