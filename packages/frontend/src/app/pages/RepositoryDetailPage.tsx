import React, { useState, useEffect } from 'react';
import { useParams, Link, useSearchParams } from 'react-router';
import { ArrowLeft, Star, Activity, Github, FileText, FolderPlus, Check, X, Folder, StickyNote, Save, Pencil } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import { Badge } from '../components/Badge';
import { fetchRepository, listCollections, getRepoCollections, addRepoToCollection, removeRepoFromCollection, getRepoNote, updateRepoNote, deleteRepoNote, type Collection } from '../api';
import { RepoChat } from '../components/RepoChat';
import type { Repository } from '../data';

function resolveReadmeUrl(url: string, repoUrl: string, isImage: boolean): string {
  if (!url) return url;
  if (/^(https?:|mailto:|tel:|#)/i.test(url)) return url;

  const normalizedRepoUrl = repoUrl.replace(/\/+$/, '');
  const cleanedPath = url.replace(/^\.?\//, '');

  if (url.startsWith('/')) {
    return isImage
      ? `${normalizedRepoUrl}/raw/HEAD${url}`
      : `${normalizedRepoUrl}/blob/HEAD${url}`;
  }

  return isImage
    ? `${normalizedRepoUrl}/raw/HEAD/${cleanedPath}`
    : `${normalizedRepoUrl}/blob/HEAD/${cleanedPath}`;
}

export function RepositoryDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [searchParams] = useSearchParams();
  const [repo, setRepo] = useState<Repository | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Collections state
  const [allCollections, setAllCollections] = useState<Collection[]>([]);
  const [repoCollections, setRepoCollections] = useState<Collection[]>([]);
  const [showCollectionModal, setShowCollectionModal] = useState(false);

  // Note state
  const [note, setNote] = useState('');
  const [isEditingNote, setIsEditingNote] = useState(false);
  const [isSavingNote, setIsSavingNote] = useState(false);

  const autoFocusChat = searchParams.get('chat') === 'true';

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    fetchRepository(id)
      .then(setRepo)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    if (!id) return;
    Promise.all([
      listCollections(false),
      getRepoCollections(parseInt(id))
    ])
      .then(([all, repoCols]) => {
        setAllCollections(all);
        setRepoCollections(repoCols);
      })
      .catch(console.error);
  }, [id]);

  useEffect(() => {
    if (!id) return;
    getRepoNote(id)
      .then((data) => setNote(data.note))
      .catch(console.error);
  }, [id]);

  const handleSaveNote = async () => {
    if (!id) return;
    setIsSavingNote(true);
    try {
      await updateRepoNote(id, note);
      setIsEditingNote(false);
    } catch (err) {
      console.error('Failed to save note:', err);
    } finally {
      setIsSavingNote(false);
    }
  };

  const handleDeleteNote = async () => {
    if (!id) return;
    if (!confirm('Delete this note?')) return;
    try {
      await deleteRepoNote(id);
      setNote('');
      setIsEditingNote(false);
    } catch (err) {
      console.error('Failed to delete note:', err);
    }
  };

  const handleAddToCollection = async (collectionId: string) => {
    if (!id) return;
    try {
      await addRepoToCollection(collectionId, parseInt(id));
      const collection = allCollections.find(c => c.id === collectionId);
      if (collection) {
        setRepoCollections(prev => [...prev, collection]);
      }
    } catch (err) {
      console.error('Failed to add to collection:', err);
    }
  };

  const handleRemoveFromCollection = async (collectionId: string) => {
    if (!id) return;
    try {
      await removeRepoFromCollection(collectionId, parseInt(id));
      setRepoCollections(prev => prev.filter(c => c.id !== collectionId));
    } catch (err) {
      console.error('Failed to remove from collection:', err);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="w-8 h-8 border-2 border-zinc-300 border-t-zinc-900 dark:border-zinc-700 dark:border-t-zinc-50 rounded-full animate-spin" />
      </div>
    );
  }

  if (error || !repo) {
    return (
      <div className="max-w-5xl mx-auto py-8 px-6 text-center">
        <p className="text-red-500">{error || 'Repository not found'}</p>
        <Link to="/repositories" className="text-blue-500 hover:underline mt-4 inline-block">← Back to repositories</Link>
      </div>
    );
  }

  return (
    <div className="w-full max-w-[1520px] mx-auto py-8 px-6 xl:px-10 bg-white dark:bg-zinc-950">
      <div className="mb-6 flex items-center gap-4">
        <Link
          to="/repositories"
          className="inline-flex items-center justify-center w-8 h-8 rounded-full hover:bg-zinc-100 dark:hover:bg-zinc-900 text-zinc-500 transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div className="flex items-center gap-3 text-sm text-zinc-500 dark:text-zinc-400 font-medium">
          <Link to="/repositories" className="hover:text-zinc-900 dark:hover:text-zinc-50 transition-colors">Repositories</Link>
          <span>/</span>
          <span className="text-zinc-900 dark:text-zinc-50">{repo.name}</span>
        </div>
      </div>

      <header className="mb-10 pb-10 border-b border-zinc-200 dark:border-zinc-800 flex flex-col md:flex-row md:items-start justify-between gap-6">
        <div className="flex-1">
          <div className="flex items-center gap-4 mb-4">
            <h1 className="text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50 sm:text-4xl">
              {repo.name}
            </h1>
            <Badge variant="outline" className="text-xs py-1 px-2.5">
              {repo.language}
            </Badge>
          </div>
          <p className="text-lg text-zinc-600 dark:text-zinc-300 leading-relaxed max-w-3xl">
            {repo.description}
          </p>

          <div className="flex flex-wrap items-center gap-6 mt-6 text-sm text-zinc-600 dark:text-zinc-400">
            <div className="flex items-center gap-2">
              <Star className="w-4 h-4 fill-amber-400 text-amber-400" />
              <span className="font-semibold text-zinc-900 dark:text-zinc-50">{(repo.stars / 1000).toFixed(1)}k</span>
              <span>stars</span>
            </div>
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-emerald-500" />
              <span>Updated {repo.lastUpdated}</span>
            </div>
          </div>
        </div>

        <div className="flex flex-row md:flex-col gap-3 shrink-0">
          <a
            href={repo.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-center gap-2 px-5 py-2.5 bg-zinc-900 hover:bg-zinc-800 dark:bg-zinc-50 dark:hover:bg-zinc-200 text-white dark:text-zinc-900 rounded-xl font-medium transition-colors shadow-sm"
          >
            <Github className="w-4 h-4" />
            View on GitHub
          </a>
          <button
            onClick={() => setShowCollectionModal(true)}
            className="flex items-center justify-center gap-2 px-5 py-2.5 bg-zinc-100 hover:bg-zinc-200 dark:bg-zinc-800 dark:hover:bg-zinc-700 text-zinc-700 dark:text-zinc-300 rounded-xl font-medium transition-colors border border-zinc-200 dark:border-zinc-700"
          >
            <FolderPlus className="w-4 h-4" />
            Add to Collection
          </button>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-10">
        <div className="lg:col-span-3 space-y-10">
          {/* AI Summary Section */}
          <section className="bg-blue-50/50 dark:bg-blue-900/10 border border-blue-100 dark:border-blue-900/30 rounded-2xl p-6 md:p-8 relative overflow-hidden">
            <div className="absolute top-0 right-0 p-6 opacity-10 pointer-events-none">
              <SparklesIcon className="w-32 h-32 text-blue-500" />
            </div>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900/50 flex items-center justify-center text-blue-600 dark:text-blue-400">
                <SparklesIcon className="w-4 h-4" />
              </div>
              <h2 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50">
                AI Project Summary
              </h2>
            </div>
            <p className="text-zinc-700 dark:text-zinc-300 leading-relaxed relative z-10 text-base md:text-lg">
              {repo.aiReason || "No AI summary available yet. Trigger a sync to generate one."}
            </p>
          </section>

          {/* Repo Chat Section */}
          <section>
            <RepoChat repoId={id!} repo={repo} autoFocus={autoFocusChat} />
          </section>

          {/* Readme Content */}
          <section className="bg-zinc-50/50 dark:bg-zinc-900/20 border border-zinc-200 dark:border-zinc-800 rounded-2xl overflow-hidden">
            <div className="flex items-center gap-2 px-6 py-4 border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900/50">
              <FileText className="w-4 h-4 text-zinc-500" />
              <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">README.md</h3>
            </div>
            <div className="p-6 md:p-8">
              <div className="markdown-body github-readme-body">
                {repo.readme ? (
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    rehypePlugins={[rehypeRaw]}
                    urlTransform={(url, key) => resolveReadmeUrl(url, repo.url, key === 'src')}
                  >
                    {repo.readme}
                  </ReactMarkdown>
                ) : (
                  <p className="text-zinc-500 dark:text-zinc-400 italic">No README available.</p>
                )}
              </div>
            </div>
          </section>
        </div>

        {/* Sidebar Info */}
        <div className="space-y-8">
          {/* Personal Note Section */}
          <section>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-medium text-zinc-900 dark:text-zinc-50 uppercase tracking-wider">
                Personal Note
              </h3>
              {!isEditingNote && (
                <button
                  onClick={() => setIsEditingNote(true)}
                  className="p-1 rounded hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300"
                >
                  <Pencil className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
            {isEditingNote ? (
              <div className="space-y-3">
                <textarea
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  placeholder="Add your personal notes about this repository..."
                  rows={4}
                  className="w-full px-3 py-2 text-sm bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                />
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleSaveNote}
                    disabled={isSavingNote}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-500 hover:bg-blue-600 text-white text-xs font-medium rounded-lg transition-colors disabled:opacity-50"
                  >
                    <Save className="w-3 h-3" />
                    {isSavingNote ? 'Saving...' : 'Save'}
                  </button>
                  <button
                    onClick={() => { setIsEditingNote(false); getRepoNote(id!).then(d => setNote(d.note)); }}
                    className="px-3 py-1.5 text-xs text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300"
                  >
                    Cancel
                  </button>
                  {note && (
                    <button
                      onClick={handleDeleteNote}
                      className="px-3 py-1.5 text-xs text-red-500 hover:text-red-600"
                    >
                      Delete
                    </button>
                  )}
                </div>
              </div>
            ) : (
              <div className={`text-sm ${note ? 'text-zinc-700 dark:text-zinc-300' : 'text-zinc-400 dark:text-zinc-500 italic'}`}>
                {note || 'No personal note yet. Click edit to add one.'}
              </div>
            )}
          </section>

          {/* Collections Section */}
          {repoCollections.length > 0 && (
            <section>
              <h3 className="text-sm font-medium text-zinc-900 dark:text-zinc-50 mb-4 uppercase tracking-wider">
                Collections
              </h3>
              <div className="space-y-2">
                {repoCollections.map(collection => (
                  <Link
                    key={collection.id}
                    to={`/collections/${collection.id}`}
                    className="flex items-center gap-2 p-2 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
                  >
                    <div
                      className="w-6 h-6 rounded flex items-center justify-center"
                      style={{ backgroundColor: `${collection.color}20`, color: collection.color }}
                    >
                      <Folder className="w-3 h-3" />
                    </div>
                    <span className="text-sm text-zinc-700 dark:text-zinc-300">{collection.name}</span>
                  </Link>
                ))}
              </div>
            </section>
          )}

          <section>
            <h3 className="text-sm font-medium text-zinc-900 dark:text-zinc-50 mb-4 uppercase tracking-wider">
              Technology Stack
            </h3>
            <div className="flex flex-wrap gap-2">
              <Badge className="px-3 py-1 text-sm bg-blue-100 text-blue-800 dark:bg-blue-900/50 dark:text-blue-200 border-none">
                {repo.language}
              </Badge>
              {repo.hasUI && (
                <Badge variant="outline" className="px-3 py-1 text-sm">Frontend UI</Badge>
              )}
              {repo.hasAPI && (
                <Badge variant="outline" className="px-3 py-1 text-sm">REST API</Badge>
              )}
            </div>
          </section>

          <section>
            <h3 className="text-sm font-medium text-zinc-900 dark:text-zinc-50 mb-4 uppercase tracking-wider">
              Tags & Categories
            </h3>
            <div className="flex flex-wrap gap-2">
              <Badge variant="secondary" className="px-3 py-1 text-sm bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100">
                {repo.category}
              </Badge>
              {repo.tags.map(tag => (
                <Badge key={tag} variant="outline" className="px-3 py-1 text-sm">
                  {tag}
                </Badge>
              ))}
            </div>
          </section>

          <section>
            <h3 className="text-sm font-medium text-zinc-900 dark:text-zinc-50 mb-4 uppercase tracking-wider">
              About
            </h3>
            <div className="space-y-4 text-sm text-zinc-600 dark:text-zinc-400">
              <div className="flex items-center gap-3">
                <Activity className="w-4 h-4" />
                <span>Activity: {repo.activityLevel}</span>
              </div>
            </div>
          </section>
        </div>
      </div>

      {/* Add to Collection Modal */}
      {showCollectionModal && (
        <AddToCollectionModal
          repoName={repo.name}
          allCollections={allCollections}
          repoCollections={repoCollections}
          onAdd={handleAddToCollection}
          onRemove={handleRemoveFromCollection}
          onClose={() => setShowCollectionModal(false)}
        />
      )}
    </div>
  );
}

function AddToCollectionModal({
  repoName,
  allCollections,
  repoCollections,
  onAdd,
  onRemove,
  onClose,
}: {
  repoName: string;
  allCollections: Collection[];
  repoCollections: Collection[];
  onAdd: (collectionId: string) => void;
  onRemove: (collectionId: string) => void;
  onClose: () => void;
}) {
  const isInCollection = (collectionId: string) => {
    return repoCollections.some(c => c.id === collectionId);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white dark:bg-zinc-900 rounded-2xl shadow-xl w-full max-w-md mx-4 overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-200 dark:border-zinc-800">
          <div>
            <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">
              Add to Collection
            </h2>
            <p className="text-sm text-zinc-500 dark:text-zinc-400">
              {repoName}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-400"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 max-h-80 overflow-y-auto">
          {allCollections.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-zinc-500 dark:text-zinc-400 mb-4">
                No collections yet
              </p>
              <Link
                to="/collections"
                className="text-blue-500 hover:text-blue-600 text-sm font-medium"
              >
                Create a collection →
              </Link>
            </div>
          ) : (
            <div className="space-y-2">
              {allCollections.map((collection) => {
                const added = isInCollection(collection.id);
                return (
                  <button
                    key={collection.id}
                    onClick={() => added ? onRemove(collection.id) : onAdd(collection.id)}
                    className={`w-full flex items-center gap-3 p-3 rounded-xl transition-colors ${
                      added
                        ? 'bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800'
                        : 'hover:bg-zinc-50 dark:hover:bg-zinc-800 border border-transparent'
                    }`}
                  >
                    <div
                      className="w-8 h-8 rounded-lg flex items-center justify-center"
                      style={{ backgroundColor: `${collection.color}20`, color: collection.color }}
                    >
                      <Folder className="w-4 h-4" />
                    </div>
                    <div className="flex-1 text-left">
                      <p className="font-medium text-zinc-900 dark:text-zinc-50 text-sm">
                        {collection.name}
                      </p>
                      <p className="text-xs text-zinc-500 dark:text-zinc-400">
                        {collection.repo_count} repositories
                      </p>
                    </div>
                    {added && (
                      <div className="flex items-center gap-1 text-blue-600 dark:text-blue-400 text-sm font-medium">
                        <Check className="w-4 h-4" />
                        Added
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
          )}
        </div>

        <div className="px-6 py-4 bg-zinc-50 dark:bg-zinc-900/50 border-t border-zinc-200 dark:border-zinc-800 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-zinc-900 hover:bg-zinc-800 dark:bg-zinc-50 dark:hover:bg-zinc-200 text-white dark:text-zinc-900 rounded-lg text-sm font-medium transition-colors"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}

function SparklesIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      {...props}
    >
      <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z" />
      <path d="M5 3v4" />
      <path d="M19 17v4" />
      <path d="M3 5h4" />
      <path d="M17 19h4" />
    </svg>
  );
}
