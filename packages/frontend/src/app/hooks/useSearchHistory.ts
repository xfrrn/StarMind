/**
 * Custom hook for managing search history in localStorage.
 * Stores up to 20 recent searches, sorted by time.
 */
import { useState, useCallback, useEffect } from 'react';

const STORAGE_KEY = 'starmind_search_history';
const MAX_HISTORY = 20;

export interface SearchHistoryItem {
  query: string;
  timestamp: number;
}

export interface UseSearchHistoryReturn {
  history: SearchHistoryItem[];
  addHistory: (query: string) => void;
  removeHistory: (query: string) => void;
  clearHistory: () => void;
}

function loadHistory(): SearchHistoryItem[] {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return [];
    const parsed = JSON.parse(stored);
    if (!Array.isArray(parsed)) return [];
    return parsed;
  } catch {
    return [];
  }
}

function saveHistory(history: SearchHistoryItem[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
  } catch (e) {
    console.warn('Failed to save search history:', e);
  }
}

export function useSearchHistory(): UseSearchHistoryReturn {
  const [history, setHistory] = useState<SearchHistoryItem[]>([]);

  // Load history on mount
  useEffect(() => {
    setHistory(loadHistory());
  }, []);

  const addHistory = useCallback((query: string) => {
    if (!query.trim()) return;

    const trimmedQuery = query.trim();
    const timestamp = Date.now();

    setHistory((prev) => {
      // Remove existing entry with same query
      const filtered = prev.filter((item) => item.query !== trimmedQuery);
      // Add new entry at the beginning
      const updated = [{ query: trimmedQuery, timestamp }, ...filtered];
      // Keep only MAX_HISTORY items
      const truncated = updated.slice(0, MAX_HISTORY);
      saveHistory(truncated);
      return truncated;
    });
  }, []);

  const removeHistory = useCallback((query: string) => {
    setHistory((prev) => {
      const updated = prev.filter((item) => item.query !== query);
      saveHistory(updated);
      return updated;
    });
  }, []);

  const clearHistory = useCallback(() => {
    setHistory([]);
    localStorage.removeItem(STORAGE_KEY);
  }, []);

  return { history, addHistory, removeHistory, clearHistory };
}
