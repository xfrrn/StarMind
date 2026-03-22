/**
 * Custom hook for managing search state and operations.
 * Consolidates multiple useState calls into a single state machine.
 */
import { useState, useCallback, useRef } from 'react';
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

export interface UseSearchReturn {
  state: SearchState;
  doSearch: (query: string) => void;
  setQuery: (query: string) => void;
  reset: () => void;
}

const initialState: SearchState = {
  query: '',
  isSearching: false,
  hasSearched: false,
  answer: '',
  results: [],
  error: '',
  statusMessage: '',
};

export function useSearch(): UseSearchReturn {
  const [state, setState] = useState<SearchState>(initialState);
  const abortRef = useRef<(() => void) | null>(null);

  const doSearch = useCallback((searchQuery: string) => {
    if (!searchQuery.trim()) return;

    // Cancel previous stream if any
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

  const reset = useCallback(() => {
    if (abortRef.current) {
      abortRef.current();
      abortRef.current = null;
    }
    setState(initialState);
  }, []);

  return { state, doSearch, setQuery, reset };
}
