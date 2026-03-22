import React, { memo } from 'react';
import { Star, Github, ArrowRight, Activity, Terminal } from 'lucide-react';
import { Link } from 'react-router';
import { Repository } from '../data';
import { Badge } from './Badge';

interface RepoCardProps {
  repo: Repository;
  showAiReason?: boolean;
}

export const RepoCard = memo(function RepoCard({ repo, showAiReason = false }: RepoCardProps) {
  return (
    <div className="group relative flex flex-col justify-between p-5 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl hover:shadow-lg hover:shadow-zinc-100/50 dark:hover:shadow-zinc-950/50 transition-all duration-200">
      <div>
        <div className="flex items-start justify-between gap-4 mb-3">
          <div className="flex-1 min-w-0">
            <h3 className="text-base font-semibold text-zinc-900 dark:text-zinc-50 truncate">
              {repo.name}
            </h3>
            <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400 line-clamp-2">
              {repo.description}
            </p>
          </div>
          <a
            href={repo.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-shrink-0 text-zinc-400 hover:text-zinc-900 dark:hover:text-zinc-50 transition-colors"
            title="View on GitHub"
          >
            <Github className="w-5 h-5" />
          </a>
        </div>

        {showAiReason && repo.aiReason && (
          <div className="mt-4 mb-4 p-3 bg-blue-50/50 dark:bg-blue-900/10 border border-blue-100 dark:border-blue-900/30 rounded-lg">
            <div className="flex gap-2 text-sm text-blue-900 dark:text-blue-200">
              <SparklesIcon className="w-4 h-4 mt-0.5 flex-shrink-0 text-blue-500" />
              <p className="leading-relaxed">{repo.aiReason}</p>
            </div>
          </div>
        )}

        <div className="flex flex-wrap gap-2 mt-4">
          <Badge variant="accent" className="gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full bg-blue-500" />
            {repo.language}
          </Badge>
          <Badge variant="outline">{repo.category}</Badge>
          {repo.tags.slice(0, 3).map((tag) => (
            <Badge key={tag} variant="secondary">{tag}</Badge>
          ))}
        </div>
      </div>

      <div className="mt-5 pt-4 border-t border-zinc-100 dark:border-zinc-800 flex items-center justify-between">
        <div className="flex items-center gap-4 text-xs text-zinc-500 dark:text-zinc-400 font-medium">
          <div className="flex items-center gap-1.5">
            <Star className="w-4 h-4 fill-zinc-400 text-zinc-400 dark:fill-zinc-500 dark:text-zinc-500" />
            <span>{(repo.stars / 1000).toFixed(1)}k</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Activity className="w-4 h-4" />
            <span>{repo.activityLevel}</span>
          </div>
        </div>

        <Link
          to={`/repositories/${repo.id}`}
          className="inline-flex items-center gap-1.5 text-sm font-medium text-zinc-900 dark:text-zinc-50 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
        >
          Details
          <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </div>
  );
});

const SparklesIcon = memo(function SparklesIcon(props: React.SVGProps<SVGSVGElement>) {
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
});
