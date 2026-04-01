/**
 * Custom hooks for state management.
 */
export { useSearch, type SearchState, type UseSearchReturn } from './useSearch';
export { useRepositories, type RepositoriesState, type UseRepositoriesReturn, type UseRepositoriesOptions } from './useRepositories';
export { useTheme, type Theme } from './useTheme';
export { useSearchHistory, type SearchHistoryItem, type UseSearchHistoryReturn } from './useSearchHistory';

// Context hooks
export { useSearchState, SearchStateProvider, type SearchState as GlobalSearchState } from '../contexts/SearchStateContext';
