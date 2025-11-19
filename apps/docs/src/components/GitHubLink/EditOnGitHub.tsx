'use client';

import React from 'react';
import { Button } from '@/components/ui/button';
import { Github, ExternalLink, History } from 'lucide-react';

interface EditOnGitHubProps {
  filePath: string;
  repository?: string;
  branch?: string;
  variant?: 'button' | 'link' | 'minimal';
  showHistory?: boolean;
  className?: string;
}

export function EditOnGitHub({
  filePath,
  repository = 'plinto/plinto',
  branch = 'main',
  variant = 'button',
  showHistory = false,
  className = ''
}: EditOnGitHubProps) {
  const githubBaseUrl = `https://github.com/${repository}`;
  const editUrl = `${githubBaseUrl}/edit/${branch}/${filePath}`;
  const historyUrl = `${githubBaseUrl}/commits/${branch}/${filePath}`;
  const _blobUrl = `${githubBaseUrl}/blob/${branch}/${filePath}`;

  if (variant === 'minimal') {
    return (
      <a
        href={editUrl}
        target="_blank"
        rel="noopener noreferrer"
        className={`text-sm text-muted-foreground hover:text-foreground transition-colors inline-flex items-center gap-1 ${className}`}
      >
        <Github className="h-3 w-3" />
        Edit
      </a>
    );
  }

  if (variant === 'link') {
    return (
      <div className={`flex items-center gap-2 text-sm ${className}`}>
        <a
          href={editUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="text-muted-foreground hover:text-foreground transition-colors inline-flex items-center gap-1"
        >
          <Github className="h-4 w-4" />
          Edit on GitHub
        </a>
        {showHistory && (
          <>
            <span className="text-muted-foreground">•</span>
            <a
              href={historyUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-muted-foreground hover:text-foreground transition-colors inline-flex items-center gap-1"
            >
              <History className="h-4 w-4" />
              View history
            </a>
          </>
        )}
      </div>
    );
  }

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <Button
        variant="outline"
        size="sm"
        asChild
      >
        <a
          href={editUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2"
        >
          <Github className="h-4 w-4" />
          Edit on GitHub
          <ExternalLink className="h-3 w-3" />
        </a>
      </Button>
      {showHistory && (
        <Button
          variant="ghost"
          size="sm"
          asChild
        >
          <a
            href={historyUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2"
          >
            <History className="h-4 w-4" />
            History
          </a>
        </Button>
      )}
    </div>
  );
}

// Component for showing contributors
interface ContributorsProps {
  filePath: string;
  repository?: string;
  branch?: string;
  maxContributors?: number;
  className?: string;
}

export function Contributors({
  filePath,
  repository = 'plinto/plinto',
  branch = 'main',
  maxContributors = 5,
  className = ''
}: ContributorsProps) {
  const [contributors, setContributors] = React.useState<any[]>([]);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    // Fetch contributors from GitHub API
    const fetchContributors = async () => {
      try {
        const response = await fetch(
          `https://api.github.com/repos/${repository}/commits?path=${filePath}&sha=${branch}`
        );
        const commits = await response.json();

        // Extract unique contributors
        const uniqueContributors = new Map();
        commits.forEach((commit: any) => {
          if (commit.author && !uniqueContributors.has(commit.author.login)) {
            uniqueContributors.set(commit.author.login, {
              login: commit.author.login,
              avatar_url: commit.author.avatar_url,
              html_url: commit.author.html_url
            });
          }
        });

        setContributors(Array.from(uniqueContributors.values()).slice(0, maxContributors));
      } catch (error) {
        console.error('Failed to fetch contributors:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchContributors();
  }, [filePath, repository, branch, maxContributors]);

  if (loading) {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <span className="text-sm text-muted-foreground">Loading contributors...</span>
      </div>
    );
  }

  if (contributors.length === 0) {
    return null;
  }

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <span className="text-sm text-muted-foreground">Contributors:</span>
      <div className="flex -space-x-2">
        {contributors.map((contributor) => (
          <a
            key={contributor.login}
            href={contributor.html_url}
            target="_blank"
            rel="noopener noreferrer"
            className="relative"
            title={contributor.login}
          >
            <img
              src={contributor.avatar_url}
              alt={contributor.login}
              className="h-6 w-6 rounded-full border-2 border-background hover:z-10 transition-transform hover:scale-110"
            />
          </a>
        ))}
      </div>
    </div>
  );
}

// Component for last updated time
interface LastUpdatedProps {
  filePath: string;
  repository?: string;
  branch?: string;
  className?: string;
}

export function LastUpdated({
  filePath,
  repository = 'plinto/plinto',
  branch = 'main',
  className = ''
}: LastUpdatedProps) {
  const [lastUpdated, setLastUpdated] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    // Fetch last commit date from GitHub API
    const fetchLastUpdated = async () => {
      try {
        const response = await fetch(
          `https://api.github.com/repos/${repository}/commits?path=${filePath}&sha=${branch}&per_page=1`
        );
        const commits = await response.json();

        if (commits.length > 0) {
          const date = new Date(commits[0].commit.author.date);
          const formattedDate = date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
          });
          setLastUpdated(formattedDate);
        }
      } catch (error) {
        console.error('Failed to fetch last updated date:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchLastUpdated();
  }, [filePath, repository, branch]);

  if (loading) {
    return null;
  }

  if (!lastUpdated) {
    return null;
  }

  return (
    <div className={`text-sm text-muted-foreground ${className}`}>
      Last updated: {lastUpdated}
    </div>
  );
}