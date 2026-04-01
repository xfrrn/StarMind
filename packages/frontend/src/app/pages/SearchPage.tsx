import React, { useCallback } from 'react';
import { Search, Sparkles, MessageSquare, Loader2, Clock, X, Trash2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useTranslation } from 'react-i18next';
import { RepoCard } from '../components/RepoCard';
import { useSearchState, useSearchHistory } from '../hooks';
import { motion, AnimatePresence } from 'motion/react';

export function SearchPage() {
  const { t } = useTranslation();
  const { state, doSearch, setQuery, clearResults } = useSearchState();
  const { query, isSearching, hasSearched, answer, results, error, statusMessage } = state;
  const { history, addHistory, removeHistory, clearHistory } = useSearchHistory();

  const handleSearch = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    doSearch(query);
    addHistory(query);
  }, [query, doSearch, addHistory]);

  const handleHistoryClick = useCallback((historyQuery: string) => {
    setQuery(historyQuery);
    doSearch(historyQuery);
    addHistory(historyQuery);
  }, [setQuery, doSearch, addHistory]);

  return (
    <div className="max-w-4xl mx-auto py-12 px-6">
      <div className="text-center mb-10">
        <h1 className="text-3xl font-bold tracking-tight text-zinc-900 dark:text-zinc-50 sm:text-4xl mb-3">
          {t('search.title')}
        </h1>
        <p className="text-zinc-500 dark:text-zinc-400 text-lg">
          {t('search.subtitle')}
        </p>
      </div>

      <div className="relative max-w-2xl mx-auto mb-16 shadow-sm dark:shadow-none">
        <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
          <Search className="h-5 w-5 text-zinc-400" />
        </div>
        <form onSubmit={handleSearch}>
          <input
            type="text"
            className="block w-full pl-12 pr-16 py-4 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl text-zinc-900 dark:text-zinc-100 placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-lg shadow-sm transition-all"
            placeholder={t('search.placeholder')}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button
            type="submit"
            disabled={!query.trim() || isSearching}
            className="absolute inset-y-2 right-2 flex items-center justify-center px-4 bg-zinc-900 hover:bg-zinc-800 dark:bg-zinc-50 dark:hover:bg-zinc-200 text-white dark:text-zinc-900 rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium"
          >
            {isSearching ? (
              <div className="w-5 h-5 border-2 border-white/30 border-t-white dark:border-zinc-900/30 dark:border-t-zinc-900 rounded-full animate-spin" />
            ) : (
              <span>{t('search.ask')}</span>
            )}
          </button>
        </form>
      </div>

      <AnimatePresence>
        {hasSearched && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.4 }}
          >
            {error ? (
              <div className="bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-900/50 rounded-2xl p-6 mb-8 text-red-700 dark:text-red-300">
                {error}
              </div>
            ) : (
              <>
                <div className="bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-950/20 dark:to-indigo-950/20 border border-blue-100 dark:border-blue-900/50 rounded-2xl p-6 mb-8">
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900/50 flex items-center justify-center text-blue-600 dark:text-blue-400">
                        <Sparkles className="w-4 h-4" />
                      </div>
                      <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50">
                        {t('search.aiSummary')}
                      </h2>
                    </div>
                    <button
                      onClick={clearResults}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-zinc-500 hover:text-red-500 dark:text-zinc-400 dark:hover:text-red-400 bg-white/50 dark:bg-zinc-800/50 hover:bg-red-50 dark:hover:bg-red-950/30 border border-zinc-200 dark:border-zinc-700 hover:border-red-200 dark:hover:border-red-900/50 rounded-lg transition-all"
                    >
                      <X className="w-3.5 h-3.5" />
                      {t('search.clearResults')}
                    </button>
                  </div>
                  <div className="text-zinc-700 dark:text-zinc-300 leading-relaxed prose prose-sm dark:prose-invert max-w-none">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {answer}
                    </ReactMarkdown>
                  </div>
                </div>

                {results.length > 0 && (
                  <>
                    <div className="mb-6 flex items-center justify-between">
                      <h3 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50 flex items-center gap-2">
                        <LibraryIcon className="w-5 h-5 text-zinc-400" />
                        {t('search.recommendedRepos')}
                      </h3>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      {results.map((repo, i) => (
                        <motion.div
                          key={repo.id}
                          initial={{ opacity: 0, y: 20 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: 0.2 + i * 0.1, duration: 0.4 }}
                        >
                          <RepoCard repo={repo} showAiReason />
                        </motion.div>
                      ))}
                    </div>
                  </>
                )}
              </>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Loading status indicator */}
      {isSearching && !hasSearched && statusMessage && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-12 flex flex-col items-center justify-center gap-4"
        >
          <div className="flex items-center gap-3 text-zinc-600 dark:text-zinc-400">
            <Loader2 className="w-5 h-5 animate-spin" />
            <span className="text-lg">{statusMessage}</span>
          </div>
        </motion.div>
      )}

      {!hasSearched && !isSearching && (
        <div className="mt-20">
          {/* Search History */}
          {history.length > 0 && (
            <div className="mb-10">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-medium text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">
                  {t('search.recentSearches')}
                </h3>
                <button
                  onClick={clearHistory}
                  className="text-xs text-zinc-400 hover:text-red-500 transition-colors flex items-center gap-1"
                >
                  <Trash2 className="w-3 h-3" />
                  {t('common.clear')}
                </button>
              </div>
              <div className="flex flex-wrap justify-center gap-2">
                {history.slice(0, 8).map((item) => (
                  <div
                    key={item.query}
                    className="group flex items-center gap-1"
                  >
                    <button
                      onClick={() => handleHistoryClick(item.query)}
                      className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-full text-sm text-zinc-600 dark:text-zinc-300 hover:border-zinc-300 dark:hover:border-zinc-700 hover:shadow-sm transition-all"
                    >
                      <Clock className="w-3.5 h-3.5 text-zinc-400" />
                      {item.query}
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        removeHistory(item.query);
                      }}
                      className="p-1 opacity-0 group-hover:opacity-100 text-zinc-400 hover:text-red-500 transition-all"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Suggested Queries */}
          <h3 className="text-sm font-medium text-zinc-500 dark:text-zinc-400 uppercase tracking-wider mb-6 text-center">
            {t('search.suggestedQueries')}
          </h3>
          <div className="flex flex-wrap justify-center gap-3">
            {[
              t('suggestions.reactDragDrop'),
              t('suggestions.lightweightDb'),
              t('suggestions.blogTemplates'),
              t('suggestions.pythonApiFrameworks')
            ].map((suggestion) => (
              <button
                key={suggestion}
                onClick={() => {
                  setQuery(suggestion);
                  doSearch(suggestion);
                  addHistory(suggestion);
                }}
                className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-full text-sm text-zinc-600 dark:text-zinc-300 hover:border-zinc-300 dark:hover:border-zinc-700 hover:shadow-sm transition-all"
              >
                <MessageSquare className="w-3.5 h-3.5" />
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function LibraryIcon(props: React.SVGProps<SVGSVGElement>) {
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
      <path d="m16 6 4 14" />
      <path d="M12 6v14" />
      <path d="M8 8v12" />
      <path d="M4 4v16" />
    </svg>
  );
}
