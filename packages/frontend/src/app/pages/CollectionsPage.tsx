import React, { useState, useEffect } from 'react';
import { Link } from 'react-router';
import { useTranslation } from 'react-i18next';
import {
  Folder,
  Star,
  Heart,
  Bookmark,
  Tag as TagIcon,
  Briefcase,
  Code,
  Zap,
  Plus,
  MoreVertical,
  Trash2,
  Edit3,
  Search,
  X,
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import {
  listCollections,
  createCollection,
  updateCollection,
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

const ICON_MAP: Record<string, React.ComponentType<{ className?: string }>> = {
  folder: Folder,
  star: Star,
  heart: Heart,
  bookmark: Bookmark,
  tag: TagIcon,
  briefcase: Briefcase,
  code: Code,
  zap: Zap,
};

function renderIcon(iconName: string, className?: string) {
  const Icon = ICON_MAP[iconName] || Folder;
  return <Icon className={className} />;
}

// Animation variants
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.08 }
  }
};

const cardVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.4, ease: 'easeOut' }
  }
};

const modalBackdropVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1 }
};

const modalContentVariants = {
  hidden: { opacity: 0, scale: 0.95, y: 20 },
  visible: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: { duration: 0.2, ease: 'easeOut' }
  },
  exit: {
    opacity: 0,
    scale: 0.95,
    y: 20,
    transition: { duration: 0.15, ease: 'easeIn' }
  }
};

export function CollectionsPage() {
  const { t } = useTranslation();
  const [collections, setCollections] = useState<Collection[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTags, setSelectedTags] = useState<string[]>([]);

  // Form state
  const [editingId, setEditingId] = useState<string | null>(null);
  const [formName, setFormName] = useState('');
  const [formDescription, setFormDescription] = useState('');
  const [formTags, setFormTags] = useState<string[]>([]);
  const [formColor, setFormColor] = useState(PRESET_COLORS[0]);
  const [formIcon, setFormIcon] = useState('folder');
  const [saving, setSaving] = useState(false);

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

  const openCreateModal = () => {
    setEditingId(null);
    setFormName('');
    setFormDescription('');
    setFormTags([]);
    setFormColor(PRESET_COLORS[0]);
    setFormIcon('folder');
    setShowModal(true);
  };

  const openEditModal = (collection: Collection) => {
    setEditingId(collection.id);
    setFormName(collection.name);
    setFormDescription(collection.description);
    setFormTags(collection.tags);
    setFormColor(collection.color || PRESET_COLORS[0]);
    setFormIcon(collection.icon || 'folder');
    setShowModal(true);
  };

  const handleSave = async () => {
    if (!formName.trim()) return;

    setSaving(true);
    try {
      if (editingId) {
        await updateCollection(editingId, {
          name: formName,
          description: formDescription,
          tags: formTags,
          color: formColor,
          icon: formIcon,
        });
      } else {
        await createCollection({
          name: formName,
          description: formDescription,
          tags: formTags,
          color: formColor,
          icon: formIcon,
        });
      }
      setShowModal(false);
      await loadCollections();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(t('collections.deleteConfirm', { name }))) return;

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
            {t('collections.title')}
          </h1>
          <p className="text-zinc-500 dark:text-zinc-400 mt-2 text-lg">
            {t('collections.description')}
          </p>
        </div>
        <button
          onClick={openCreateModal}
          className="flex items-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-xl font-medium transition-colors"
        >
          <Plus className="w-4 h-4" />
          {t('collections.newCollection')}
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
            placeholder={t('collections.searchPlaceholder')}
            className="w-full pl-10 pr-4 py-2 bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        {allTags.length > 0 && (
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm text-zinc-500">{t('common.filter')}:</span>
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
                {t('common.clear')}
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
            {collections.length === 0 ? t('collections.noCollections') : t('collections.noMatchingCollections')}
          </h3>
          <p className="text-zinc-500 dark:text-zinc-400 mb-6">
            {collections.length === 0
              ? t('collections.noCollectionsHint')
              : t('collections.noMatchingHint')}
          </p>
          {collections.length === 0 && (
            <button
              onClick={openCreateModal}
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-xl font-medium transition-colors"
            >
              <Plus className="w-4 h-4" />
              {t('collections.createCollection')}
            </button>
          )}
        </div>
      ) : (
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
        >
          {filteredCollections.map((collection) => (
            <CollectionCard
              key={collection.id}
              collection={collection}
              onEdit={() => openEditModal(collection)}
              onDelete={() => handleDelete(collection.id, collection.name)}
            />
          ))}
        </motion.div>
      )}

      {/* Modal */}
      <AnimatePresence>
        {showModal && (
          <motion.div
            variants={modalBackdropVariants}
            initial="hidden"
            animate="visible"
            exit="hidden"
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
            onClick={(e) => e.target === e.currentTarget && setShowModal(false)}
          >
            <motion.div
              variants={modalContentVariants}
              initial="hidden"
              animate="visible"
              exit="exit"
              className="bg-white dark:bg-zinc-900 rounded-2xl shadow-xl w-full max-w-md mx-4 overflow-hidden"
            >
              <CollectionModalContent
                t={t}
                isEdit={!!editingId}
                name={formName}
                setName={setFormName}
                description={formDescription}
                setDescription={setFormDescription}
                tags={formTags}
                setTags={setFormTags}
                color={formColor}
                setColor={setFormColor}
                icon={formIcon}
                setIcon={setFormIcon}
                saving={saving}
                onSave={handleSave}
                onClose={() => setShowModal(false)}
              />
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function CollectionCard({
  collection,
  onEdit,
  onDelete,
}: {
  collection: Collection;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const [showMenu, setShowMenu] = useState(false);

  return (
    <motion.div
      variants={cardVariants}
      className="group relative bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl overflow-hidden hover:shadow-lg hover:border-zinc-300 dark:hover:border-zinc-700 transition-all"
    >
      {/* Color accent */}
      <div
        className="h-1.5"
        style={{ backgroundColor: collection.color || PRESET_COLORS[0] }}
      />

      {/* Clickable content */}
      <Link to={`/collections/${collection.id}`} className="block p-5">
        {/* Header */}
        <div className="flex items-center gap-3 mb-3">
          <div
            className="w-10 h-10 rounded-xl flex items-center justify-center"
            style={{
              backgroundColor: `${collection.color || PRESET_COLORS[0]}20`,
              color: collection.color || PRESET_COLORS[0]
            }}
          >
            {renderIcon(collection.icon || 'folder', 'w-5 h-5')}
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-zinc-900 dark:text-zinc-50 truncate">
              {collection.name}
            </h3>
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              {t('collections.repositories', { count: collection.repo_count })}
            </p>
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
                <span
                  key={repo.id}
                  className="block text-sm text-zinc-700 dark:text-zinc-300 truncate"
                  onClick={(e) => e.stopPropagation()}
                >
                  {repo.name}
                </span>
              ))}
            </div>
          </div>
        )}
      </Link>

      {/* Menu - outside the link */}
      <div className="absolute top-5 right-5">
        <button
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            setShowMenu(!showMenu);
          }}
          className="p-1.5 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-300 transition-colors"
        >
          <MoreVertical className="w-4 h-4" />
        </button>
        <AnimatePresence>
          {showMenu && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setShowMenu(false)} />
              <motion.div
                initial={{ opacity: 0, scale: 0.95, y: -10 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95, y: -10 }}
                transition={{ duration: 0.15 }}
                className="absolute right-0 top-full mt-1 w-36 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl shadow-lg z-20 py-1 overflow-hidden"
              >
                <button
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    setShowMenu(false);
                    onEdit();
                  }}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm text-zinc-700 dark:text-zinc-300 hover:bg-zinc-50 dark:hover:bg-zinc-800 transition-colors"
                >
                  <Edit3 className="w-4 h-4" />
                  {t('common.edit')}
                </button>
                <button
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    setShowMenu(false);
                    onDelete();
                  }}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950 transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                  {t('common.delete')}
                </button>
              </motion.div>
            </>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}

function CollectionModalContent({
  t,
  isEdit,
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
  t: (key: string, options?: Record<string, unknown>) => string;
  isEdit: boolean;
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
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-200 dark:border-zinc-800">
        <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">
          {isEdit ? t('collections.editCollection') : t('collections.createCollection')}
        </h2>
        <button
          onClick={onClose}
          className="p-1.5 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-400 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Content */}
      <div className="p-6 space-y-4 max-h-[60vh] overflow-y-auto">
        {/* Name */}
        <div>
          <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-1.5">
            {t('collections.name')} *
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder={t('collections.namePlaceholder')}
            className="w-full px-3 py-2 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* Description */}
        <div>
          <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-1.5">
            {t('collections.description')}
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder={t('collections.descriptionPlaceholder')}
            rows={2}
            className="w-full px-3 py-2 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
          />
        </div>

        {/* Tags */}
        <div>
          <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-1.5">
            {t('collections.tags')}
          </label>
          <div className="flex gap-2 mb-2">
            <input
              type="text"
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addTag())}
              placeholder={t('collections.tagsPlaceholder')}
              className="flex-1 px-3 py-2 bg-zinc-50 dark:bg-zinc-950 border border-zinc-200 dark:border-zinc-800 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              onClick={addTag}
              className="px-3 py-2 bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 text-zinc-700 dark:text-zinc-300 rounded-lg text-sm font-medium transition-colors"
            >
              {t('common.add')}
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
            {t('collections.icon')}
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
            {t('collections.color')}
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

      {/* Footer */}
      <div className="px-6 py-4 bg-zinc-50 dark:bg-zinc-900/50 border-t border-zinc-200 dark:border-zinc-800 flex justify-end gap-3">
        <button
          onClick={onClose}
          className="px-4 py-2 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-lg text-sm font-medium transition-colors"
        >
          {t('common.cancel')}
        </button>
        <button
          onClick={onSave}
          disabled={!name.trim() || saving}
          className="px-4 py-2 bg-blue-500 hover:bg-blue-600 disabled:bg-zinc-300 dark:disabled:bg-zinc-700 text-white rounded-lg text-sm font-medium transition-colors disabled:cursor-not-allowed"
        >
          {saving ? t('common.saving') : isEdit ? t('common.save') : t('common.create')}
        </button>
      </div>
    </>
  );
}

export default CollectionsPage;
