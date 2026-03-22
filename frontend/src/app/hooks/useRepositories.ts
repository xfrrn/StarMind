/**
 * Custom hook for managing repository list state and filtering.
 * Handles loading, pagination, and filter state.
 */
import { useState, useEffect, useCallback, useMemo } from 'react';
import { fetchRepositories, fetchStats, type RepoFilters, type StatsResponse } from '../api';
import type { Repository } from '../data';

export interface UseRepositoriesOptions {
  pageSize?: number;
  debounceMs?: number;
}

export interface RepositoriesState {
  repos: Repository[];
  total: number;
  page: number;
  loading: boolean;
  stats: StatsResponse | null;
  // Filters
  searchQuery: string;
  selectedLanguage: string;
  selectedCategory: string;
  selectedActivity: string;
  filterHasUI: boolean | undefined;
  filterHasAPI: boolean | undefined;
}

export interface UseRepositoriesReturn {
  state: RepositoriesState;
  // Pagination
  setPage: (page: number) => void;
  totalPages: number;
  // Filters
  setSearchQuery: (query: string) => void;
  setSelectedLanguage: (lang: string) => void;
  setSelectedCategory: (cat: string) => void;
  setSelectedActivity: (activity: string) => void;
  setFilterHasUI: (hasUI: boolean | undefined) => void;
  setFilterHasAPI: (hasAPI: boolean | undefined) => void;
  // Stats
  languageEntries: [string, number][];
  categoryEntries: [string, number][];
  // Actions
  reload: () => void;
}

export function useRepositories(options: UseRepositoriesOptions = {}): UseRepositoriesReturn {
  const { pageSize = 20, debounceMs = 300 } = options;

  const [state, setState] = useState<RepositoriesState>({
    repos: [],
    total: 0,
    page: 1,
    loading: true,
    stats: null,
    searchQuery: '',
    selectedLanguage: '',
    selectedCategory: '',
    selectedActivity: '',
    filterHasUI: undefined,
    filterHasAPI: undefined,
  });

  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState('');

  // Debounce search query
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearchQuery(state.searchQuery.trim());
      setState(prev => ({ ...prev, page: 1 }));
    }, debounceMs);
    return () => clearTimeout(timer);
  }, [state.searchQuery, debounceMs]);

  // Load repositories
  const loadRepos = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true }));
    try {
      const filters: RepoFilters = {
        page: state.page,
        limit: pageSize,
        search: debouncedSearchQuery || undefined,
        language: state.selectedLanguage || undefined,
        category: state.selectedCategory || undefined,
        activity_level: state.selectedActivity || undefined,
        has_ui: state.filterHasUI,
        has_api: state.filterHasAPI,
      };
      const data = await fetchRepositories(filters);
      setState(prev => ({ ...prev, repos: data.repositories, total: data.total }));
    } catch (err) {
      console.error('Failed to load repos:', err);
    } finally {
      setState(prev => ({ ...prev, loading: false }));
    }
  }, [state.page, debouncedSearchQuery, state.selectedLanguage, state.selectedCategory, state.selectedActivity, state.filterHasUI, state.filterHasAPI, pageSize]);

  // Reload when filters change
  useEffect(() => {
    loadRepos();
  }, [loadRepos]);

  // Load stats on mount
  useEffect(() => {
    fetchStats().then(stats => setState(prev => ({ ...prev, stats }))).catch(console.error);
  }, []);

  // Setters
  const setPage = useCallback((page: number) => {
    setState(prev => ({ ...prev, page }));
  }, []);

  const setSearchQuery = useCallback((query: string) => {
    setState(prev => ({ ...prev, searchQuery: query }));
  }, []);

  const setSelectedLanguage = useCallback((lang: string) => {
    setState(prev => ({ ...prev, selectedLanguage: lang, page: 1 }));
  }, []);

  const setSelectedCategory = useCallback((cat: string) => {
    setState(prev => ({ ...prev, selectedCategory: cat, page: 1 }));
  }, []);

  const setSelectedActivity = useCallback((activity: string) => {
    setState(prev => ({ ...prev, selectedActivity: activity, page: 1 }));
  }, []);

  const setFilterHasUI = useCallback((hasUI: boolean | undefined) => {
    setState(prev => ({ ...prev, filterHasUI: hasUI, page: 1 }));
  }, []);

  const setFilterHasAPI = useCallback((hasAPI: boolean | undefined) => {
    setState(prev => ({ ...prev, filterHasAPI: hasAPI, page: 1 }));
  }, []);

  const reload = useCallback(() => {
    loadRepos();
  }, [loadRepos]);

  // Computed values
  const totalPages = useMemo(() => Math.ceil(state.total / pageSize), [state.total, pageSize]);
  const languageEntries = useMemo(() => state.stats ? Object.entries(state.stats.languages).slice(0, 8) : [], [state.stats]);
  const categoryEntries = useMemo(() => state.stats ? Object.entries(state.stats.categories) : [], [state.stats]);

  return {
    state,
    setPage,
    totalPages,
    setSearchQuery,
    setSelectedLanguage,
    setSelectedCategory,
    setSelectedActivity,
    setFilterHasUI,
    setFilterHasAPI,
    languageEntries,
    categoryEntries,
    reload,
  };
}
