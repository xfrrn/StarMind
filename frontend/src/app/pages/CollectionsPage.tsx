import React, { useState, useEffect } from 'react';
import { Link } from 'react-router';
import {
  Folder,
  Plus,
  MoreVertical,
  Trash2,
  Edit3,
  Tag,
  ExternalLink,
  Search,
  X,
} from 'lucide-react';
import {
  listCollections,
  createCollection,
  deleteCollection,
  type Collection,
} from '../api';

const PRESET_COLORS = [
  '#3B82F6', // blue
  '#10B981', // emerald
  '#F59E0B', // amber
  '#EF4444', // red
  '#8B5CF6', // violet
  '#EC4899', // pink
  '#06B6D4', // cyan
  '#84CC16', // lime
];

const PRESET_ICONS = [
  'folder',
  'star',
  'heart',
  'bookmark',
  'tag',
  'briefcase',
  'code',
  'zap',
];

export function CollectionsPage() {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTags, setSelectedTags] = useState<string[]>([]);

  // Form state for new collection
  const [newName, setNewName] = useState('');
  const [newDescription, setNewDescription] = useState('');
  const [newTags, setNewTags] = useState<string[]>([]);
  const [newColor, setNewColor] = useState(PRESET_COLORS[0]);
  const [newIcon, setNewIcon] = useState('folder');
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    loadCollections();
  }, []);

  const loadCollections = async () => {
    setLoading(true);
    try {
      const data = await listCollections(true);
      setCollections(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateCollection = async () => {
    if (!newName.trim()) return;

    setCreating(true);
    try {
      await createCollection({
        name: newName,
        description: newDescription,
        tags: newTags,
        color: newColor,
        icon: newIcon,
      });
      setShowCreateModal(false);
      setNewName('');
      setNewDescription('');
      setNewTags([]);
      setNewColor(PRESET_COLORS[0]);
      setNewIcon('folder');
      await loadCollections();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteCollection = async (id: string, name: string) => {
    if (!confirm(`Delete collection "${name}"? This cannot be undone.`)) return;

    try {
      await deleteCollection(id);
      await loadCollections();
    } catch (err: any) {
      setError(err.message);
    }
  };

  // Get all unique tags from collections
  const allTags = [...new Set(collections.flatMap((c) => c.tags))];

  // Filter collections by search and tags
  const filteredCollections = collections.filter((col) => {
    const matchesSearch =
      !searchQuery ||
      col.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      col.description.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesTags =
      selectedTags.length === 0 || selectedTags.every((tag) => col.tags.includes(tag));
    return matchesSearch && matchesTags;
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="w-8 h-8 border-2 border-zinc-300 border-t-zinc-900 dark:border-zinc-700 dark:border-t-zinc-50 rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="w-full max-w-[1520px] mx-auto py-8 px-6 xl:px-10">
      {/* Header */}
      <div className="mb-8 flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50">
            Collections
          </h1>
          <p className="text-zinc-500 dark:text-zinc-400 mt-2 text-lg">
            Organize your starred repositories into collections
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-xl font-medium transition-colors"
        >
          <Plus className="w-4 h-4" />
          New Collection
        </button>
      </div>

      {error && (
        <div className="mb-6 p-4 bg-red-50 dark:bg-red-950 text-red-600 dark:text-red-400 rounded-xl">
          {error}
        </div>
      )}

      {/* Filters */}
      <div className="mb-6 flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search collections..."
            className="w-full pl-10 pr-4 py-2 bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        {allTags.length > 0 && (
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm text-zinc-500">Filter:</span>
            {allTags.map((tag) => (
              <button
                key={tag}
                onClick={() =>
                  setSelectedTags((prev) =>
                    prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]
                  )
                }
                className={`px-3 py-1 text-xs font-medium rounded-full transition-colors ${
                  selectedTags.includes(tag)
                    ? 'bg-blue-500 text-white'
                    : 'bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 hover:bg-zinc-200 dark:hover:bg-zinc-700'
                }`}
              >
                {tag}
              </button>
            ))}
            {selectedTags.length > 0 && (
              <button
                onClick={() => setSelectedTags([])}
                className="text-xs text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300"
              >
                Clear
              </button>
            )}
          </div>
        )}
      </div>

      {/* Collections Grid */}
      {filteredCollections.length === 0 ? (
        <div className="text-center py-20">
          <Folder className="w-12 h-12 mx-auto text-zinc-300 dark:text-zinc-700 mb-4" />
          <h3 className="text-lg font-medium text-zinc-900 dark:text-zinc-50 mb-2">
            {collections.length === 0 ? 'No collections yet' : 'No matching collections'}
          </h3>
          <p className="text-zinc-500 dark:text-zinc-400 mb-6">
            {collections.length === 0
              ? 'Create your first collection to organize repositories'
              : 'Try adjusting your search or filters'}
          </p>
          {collections.length === 0 && (
            <button
              onClick={() => setShowCreateModal(true)}
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-xl font-medium transition-colors"
            >
              <Plus className="w-4 h-4" />
              Create Collection
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredCollections.map((collection) => (
            <CollectionCard
              key={collection.id}
              collection={collection}
              onDelete={() => handleDeleteCollection(collection.id, collection.name)}
            />
          ))}
        </div>
      )}

      {/* Create Modal */}
      {showCreateModal && (
        <CreateCollectionModal
          name={newName}
          setName={setNewName}
          description={newDescription}
          setDescription={setNewDescription}
          tags={newTags}
          setTags={setNewTags}
          color={newColor}
          setColor={setNewColor}
          icon={newIcon}
          setIcon={setNewIcon}
          creating={creating}
          onCreate={handleCreateCollection}
          onClose={() => setShowCreateModal(false)}
        />
      )}
    </div>
  );
}

function CollectionCard({
  collection,
  onDelete,
}: {
  collection: Collection;
  onDelete: () => void;
}) {
  const [showMenu, setShowMenu] = useState(false);

  return (
    <div
      className="group relative bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl overflow-hidden hover:shadow-lg transition-shadow"
    >
      {/* Color accent */}
      <div
        className="h-1.5"
        style={{ backgroundColor: collection.color }}
      />

      <div className="p-5">
        {/* Header */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-3">
            <div
              className="w-10 h-10 rounded-xl flex items-center justify-center"
              style={{ backgroundColor: `${collection.color}20`, color: collection.color }}
            >
              <Folder className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-semibold text-zinc-900 dark:text-zinc-50">
                {collection.name}
              </h3>
              <p className="text-xs text-zinc-500 dark:text-zinc-400">
                {collection.repo_count} repositories
              </p>
            </div>
          </div>

          {/* Menu */}
          <div className="relative">
            <button
              onClick={() => setShowMenu(!showMenu)}
              className="p-1.5 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300"
            >
              <MoreVertical className="w-4 h-4" />
            </button>
            {showMenu && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setShowMenu(false)} />
                <div className="absolute right-0 top-full mt-1 w-36 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl shadow-lg z-20 py-1">
                  <Link
                    to={`/collections/${collection.id}`}
                    className="flex items-center gap-2 px-3 py-2 text-sm text-zinc-700 dark:text-zinc-300 hover:bg-zinc-50 dark:hover:bg-zinc-800"
                  >
                    <ExternalLink className="w-4 h-4" />
                    View
                  </Link>
                  <button
                    onClick={() => {
                      setShowMenu(false);
                      onDelete();
                    }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950"
                  >
                    <Trash2 className="w-4 h-4" />
                    Delete
                  </button>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Description */}
        {collection.description && (
          <p className="text-sm text-zinc-600 dark:text-zinc-400 mb-4 line-clamp-2">
            {collection.description}
          </p>
        )}

        {/* Tags */}
        {collection.tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {collection.tags.slice(0, 4).map((tag) => (
              <span
                key={tag}
                className="px-2 py-0.5 text-xs bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400 rounded-full"
              >
                {tag}
              </span>
            ))}
            {collection.tags.length > 4 && (
              <span className="px-2 py-0.5 text-xs text-zinc-400">
                +{collection.tags.length - 4}
              </span>
            )}
          </div>
        )}

        {/* Preview repos */}
        {'repositories' in collection && Array.isArray((collection as any).repositories) && (collection as any).repositories.length > 0 && (
          <div className="mt-4 pt-4 border-t border-zinc-100 dark:border-zinc-800">
            <p className="text-xs text-zinc-500 dark:text-zinc-400 mb-2">Recently added:</p>
            <div className="space-y-1">
              {(collection as any).repositories.slice(0, 3).map((repo: any) => (
                <Link
                  key={repo.id}
                  to={`/repositories/${repo.id}`}
                  className="block text-sm text-zinc-700 dark:text-zinc-300 hover:text-blue-600 dark:hover:text-blue-400 truncate"
                >
                  {repo.name}
                </Link>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function CreateCollectionModal({
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
  creating,
  onCreate,
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
  creating: boolean;
  onCreate: () => void;
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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white dark:bg-zinc-900 rounded-2xl shadow-xl w-full max-w-md mx-4 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-200 dark:border-zinc-800">
          <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">
            Create Collection
          </h2>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-400"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4">
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
                      className="hover:text-red-500"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                ))}
              </div>
            )}
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
                  onClick={() => setColor(c)}
                  className={`w-8 h-8 rounded-lg transition-transform ${
                    color === c ? 'ring-2 ring-offset-2 ring-zinc-400 scale-110' : ''
                  }`}
                  style={{ backgroundColor: c }}
                />
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-zinc-50 dark:bg-zinc-900/50 border-t border-zinc-200 dark:border-zinc-800 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-lg text-sm font-medium transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onCreate}
            disabled={!name.trim() || creating}
            className="px-4 py-2 bg-blue-500 hover:bg-blue-600 disabled:bg-zinc-300 dark:disabled:bg-zinc-700 text-white rounded-lg text-sm font-medium transition-colors disabled:cursor-not-allowed"
          >
            {creating ? 'Creating...' : 'Create'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default CollectionsPage;
