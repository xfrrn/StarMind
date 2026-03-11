import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router';
import { ArrowLeft, Star, GitFork, Eye, Globe, Github, Terminal, Activity, FileText } from 'lucide-react';
import { Badge } from '../components/Badge';
import { fetchRepository } from '../api';
import type { Repository } from '../data';

export function RepositoryDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [repo, setRepo] = useState<Repository | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    fetchRepository(id)
      .then(setRepo)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [id]);

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
    <div className="max-w-5xl mx-auto py-8 px-6 lg:px-8 bg-white dark:bg-zinc-950">
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
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-10">
        <div className="lg:col-span-2 space-y-10">
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

          {/* Readme Content */}
          <section className="bg-zinc-50/50 dark:bg-zinc-900/20 border border-zinc-200 dark:border-zinc-800 rounded-2xl overflow-hidden">
            <div className="flex items-center gap-2 px-6 py-4 border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900/50">
              <FileText className="w-4 h-4 text-zinc-500" />
              <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">README.md</h3>
            </div>
            <div className="p-6 md:p-8">
              <div className="prose prose-zinc dark:prose-invert max-w-none">
                <pre className="whitespace-pre-wrap font-mono text-sm text-zinc-700 dark:text-zinc-300 bg-transparent p-0 m-0 border-0">
                  {repo.readme || "No README available."}
                </pre>
              </div>
            </div>
          </section>
        </div>

        {/* Sidebar Info */}
        <div className="space-y-8">
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
