/**
 * SearchStateContext - AI搜索状态的全局Context
 * 将搜索状态提升到Context层级，使得导航时状态不会丢失
 */
import React, { createContext, useContext, useState, useCallback, useRef, useEffect } from 'react';
import { chatSearchStream, type Repository, type StatusEvent } from '../api';

export interface SearchState {
  query: string;
  isSearching: boolean;
  hasSearched: boolean;
  answer: string;
  results: Repository[];
  error: string;
  statusMessage: string;
}

interface SearchStateContextValue {
  state: SearchState;
  doSearch: (query: string) => void;
  setQuery: (query: string) => void;
  clearResults: () => void;
}

const STORAGE_KEY = 'starmind_search_state';

const initialState: SearchState = {
  query: '',
  isSearching: false,
  hasSearched: false,
  answer: '',
  results: [],
  error: '',
  statusMessage: '',
};

// 从 sessionStorage 加载状态
function loadState(): SearchState {
  try {
    const stored = sessionStorage.getItem(STORAGE_KEY);
    if (!stored) return initialState;
    const parsed = JSON.parse(stored);
    // 不恢复正在搜索的状态
    if (parsed.isSearching) {
      return { ...parsed, isSearching: false, statusMessage: '' };
    }
    return parsed;
  } catch {
    return initialState;
  }
}

// 保存状态到 sessionStorage
function saveState(state: SearchState): void {
  try {
    // 只保存有意义的状态
    if (state.hasSearched || state.query) {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    }
  } catch (e) {
    console.warn('Failed to save search state:', e);
  }
}

const SearchStateContext = createContext<SearchStateContextValue | null>(null);

export function SearchStateProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<SearchState>(loadState);
  const abortRef = useRef<(() => void) | null>(null);

  // 保存状态到 sessionStorage
  useEffect(() => {
    saveState(state);
  }, [state]);

  const doSearch = useCallback((searchQuery: string) => {
    if (!searchQuery.trim()) return;

    // 取消之前的流
    if (abortRef.current) {
      abortRef.current();
    }

    setState(prev => ({
      ...prev,
      query: searchQuery,
      isSearching: true,
      hasSearched: false,
      error: '',
      answer: '',
      results: [],
      statusMessage: '正在分析查询...',
    }));

    abortRef.current = chatSearchStream(searchQuery, {
      onStatus: (status: StatusEvent) => {
        setState(prev => ({ ...prev, statusMessage: status.message }));
      },
      onRepositories: (repos) => {
        setState(prev => ({ ...prev, results: repos, hasSearched: true }));
      },
      onToken: (token) => {
        setState(prev => ({ ...prev, answer: prev.answer + token }));
      },
      onDone: () => {
        setState(prev => ({ ...prev, isSearching: false, statusMessage: '' }));
        abortRef.current = null;
      },
      onError: (err) => {
        setState(prev => ({
          ...prev,
          error: err,
          isSearching: false,
          statusMessage: '',
          hasSearched: true,
        }));
        abortRef.current = null;
      },
    });
  }, []);

  const setQuery = useCallback((query: string) => {
    setState(prev => ({ ...prev, query }));
  }, []);

  const clearResults = useCallback(() => {
    if (abortRef.current) {
      abortRef.current();
      abortRef.current = null;
    }
    setState(initialState);
    sessionStorage.removeItem(STORAGE_KEY);
  }, []);

  return (
    <SearchStateContext.Provider value={{ state, doSearch, setQuery, clearResults }}>
      {children}
    </SearchStateContext.Provider>
  );
}

export function useSearchState(): SearchStateContextValue {
  const context = useContext(SearchStateContext);
  if (!context) {
    throw new Error('useSearchState must be used within a SearchStateProvider');
  }
  return context;
}
