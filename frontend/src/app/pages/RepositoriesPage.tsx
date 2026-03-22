import React, { useState, useEffect, useCallback, memo, useMemo } from 'react';
import { Search, ChevronDown, Settings2 } from 'lucide-react';
import { RepoCard } from '../components/RepoCard';
import { Badge } from '../components/Badge';
import { fetchRepositories, fetchStats, type RepoFilters, type StatsResponse } from '../api';
import type { Repository } from '../data';

export function RepositoriesPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState('');
  const [repos, setRepos] = useState<Repository[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<StatsResponse | null>(null);

  // Filters
  const [selectedLanguage, setSelectedLanguage] = useState<string>('');
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [selectedActivity, setSelectedActivity] = useState<string>('');
  const [filterHasUI, setFilterHasUI] = useState<boolean | undefined>(undefined);
  const [filterHasAPI, setFilterHasAPI] = useState<boolean | undefined>(undefined);

  const loadRepos = async () => {
    setLoading(true);
    try {
      const filters: RepoFilters = {
        page,
        limit: 20,
        search: debouncedSearchQuery || undefined,
        language: selectedLanguage || undefined,
        category: selectedCategory || undefined,
        activity_level: selectedActivity || undefined,
        has_ui: filterHasUI,
        has_api: filterHasAPI,
      };
      const data = await fetchRepositories(filters);
      setRepos(data.repositories);
      setTotal(data.total);
    } catch (err) {
      console.error('Failed to load repos:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearchQuery(searchQuery.trim());
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  useEffect(() => {
    loadRepos();
  }, [
    page,
    debouncedSearchQuery,
    selectedLanguage,
    selectedCategory,
    selectedActivity,
    filterHasUI,
    filterHasAPI,
  ]);

  useEffect(() => {
    fetchStats().then(setStats).catch(console.error);
  }, []);

  const languageEntries = stats ? Object.entries(stats.languages).slice(0, 8) : [];
  const categoryEntries = stats ? Object.entries(stats.categories) : [];

  return (
    <div className="flex flex-col h-full bg-white dark:bg-zinc-950 text-zinc-900 dark:text-zinc-50">
      <div className="flex items-center justify-between px-8 py-6 border-b border-zinc-200 dark:border-zinc-800 flex-shrink-0">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Your Repositories</h1>
          <p className="text-zinc-500 dark:text-zinc-400 mt-1 text-sm">
            Browse and filter through your {total.toLocaleString()} synced starred repositories.
          </p>
        </div>
        <div className="flex gap-3">
          <div className="relative w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
            <input
              type="text"
              placeholder="Search repositories..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setPage(1);
              }}
              className="w-full pl-9 pr-4 py-2 bg-zinc-50 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 transition-shadow"
            />
          </div>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Filter Sidebar */}
        <div className="w-64 flex-shrink-0 border-r border-zinc-200 dark:border-zinc-800 p-6 overflow-y-auto hidden lg:block bg-zinc-50/50 dark:bg-zinc-900/20">
          <div className="space-y-8">
            <FilterSection title="Language">
              <FilterCheckbox
                label="All"
                count={stats?.total || 0}
                checked={selectedLanguage === ''}
                onChange={() => { setSelectedLanguage(''); setPage(1); }}
              />
              {languageEntries.map(([lang, count]) => (
                <FilterCheckbox
                  key={lang}
                  label={lang}
                  count={count}
                  checked={selectedLanguage === lang}
                  onChange={() => { setSelectedLanguage(selectedLanguage === lang ? '' : lang); setPage(1); }}
                />
              ))}
            </FilterSection>

            <FilterSection title="Category">
              <FilterCheckbox
                label="All"
                count={stats?.total || 0}
                checked={selectedCategory === ''}
                onChange={() => { setSelectedCategory(''); setPage(1); }}
              />
              {categoryEntries.map(([cat, count]) => (
                <FilterCheckbox
                  key={cat}
                  label={cat}
                  count={count}
                  checked={selectedCategory === cat}
                  onChange={() => { setSelectedCategory(selectedCategory === cat ? '' : cat); setPage(1); }}
                />
              ))}
            </FilterSection>

            <FilterSection title="Features">
              <FilterCheckbox
                label="Has UI"
                count={0}
                checked={filterHasUI === true}
                onChange={() => { setFilterHasUI(filterHasUI === true ? undefined : true); setPage(1); }}
              />
              <FilterCheckbox
                label="Has API"
                count={0}
                checked={filterHasAPI === true}
                onChange={() => { setFilterHasAPI(filterHasAPI === true ? undefined : true); setPage(1); }}
              />
            </FilterSection>

            <FilterSection title="Activity Level">
              {['High', 'Medium', 'Low'].map((level) => (
                <FilterCheckbox
                  key={level}
                  label={level}
                  count={0}
                  checked={selectedActivity === level}
                  onChange={() => { setSelectedActivity(selectedActivity === level ? '' : level); setPage(1); }}
                />
              ))}
            </FilterSection>
          </div>
        </div>

        {/* List Content */}
        <div className="flex-1 overflow-y-auto p-6 lg:p-8">
          {loading ? (
            <div className="flex items-center justify-center py-20">
              <div className="w-8 h-8 border-2 border-zinc-300 border-t-zinc-900 dark:border-zinc-700 dark:border-t-zinc-50 rounded-full animate-spin" />
            </div>
          ) : repos.length === 0 ? (
            <div className="text-center py-20 text-zinc-500 dark:text-zinc-400">
              <p className="text-lg mb-2">No repositories found</p>
              <p className="text-sm">Try adjusting your filters or sync your starred repos first.</p>
            </div>
          ) : (
            <>
              <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                {repos.map((repo) => (
                  <RepoCard key={repo.id} repo={repo} />
                ))}
              </div>
              {total > 20 && (
                <div className="flex justify-center gap-2 mt-8">
                  <button
                    disabled={page <= 1}
                    onClick={() => setPage(p => p - 1)}
                    className="px-4 py-2 bg-zinc-100 dark:bg-zinc-800 rounded-lg text-sm disabled:opacity-50"
                  >
                    Previous
                  </button>
                  <span className="px-4 py-2 text-sm text-zinc-500">
                    Page {page} of {Math.ceil(total / 20)}
                  </span>
                  <button
                    disabled={page >= Math.ceil(total / 20)}
                    onClick={() => setPage(p => p + 1)}
                    className="px-4 py-2 bg-zinc-100 dark:bg-zinc-800 rounded-lg text-sm disabled:opacity-50"
                  >
                    Next
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

const FilterSection = memo(function FilterSection({ title, children }: { title: string, children: React.ReactNode }) {
  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-50 flex items-center justify-between">
        {title}
        <ChevronDown className="w-4 h-4 text-zinc-400" />
      </h3>
      <div className="space-y-2">
        {children}
      </div>
    </div>
  );
});

const FilterCheckbox = memo(function FilterCheckbox({ label, count, checked = false, onChange }: { label: string, count: number, checked?: boolean, onChange?: () => void }) {
  return (
    <label className="flex items-center justify-between group cursor-pointer">
      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          checked={checked}
          onChange={onChange}
          className="w-4 h-4 rounded border-zinc-300 dark:border-zinc-700 text-blue-600 focus:ring-blue-500 dark:bg-zinc-800"
        />
        <span className="text-sm text-zinc-600 dark:text-zinc-400 group-hover:text-zinc-900 dark:group-hover:text-zinc-50 transition-colors">
          {label}
        </span>
      </div>
      {count > 0 && <Badge variant="secondary" className="text-[10px] px-1.5 py-0">{count}</Badge>}
    </label>
  );
});
