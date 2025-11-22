import { useState, useEffect } from 'react';
import { useI18n } from '../../contexts/I18nContext';
import { Github, Star, GitFork, Eye, TrendingUp, AlertCircle } from 'lucide-react';

interface GitHubRepo {
  name: string;
  fullName: string;
  description: string;
  stars: number;
  forks: number;
  watchers: number;
  language: string;
  url: string;
  updatedAt: string;
}

export const GitHubWidget = () => {
  const { t } = useI18n();
  const [repos, setRepos] = useState<GitHubRepo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [username, setUsername] = useState('');

  useEffect(() => {
    const saved = localStorage.getItem('sdb_github_username');
    if (saved) {
      setUsername(saved);
      loadRepos(saved);
    } else {
      setLoading(false);
    }
  }, []);

  const loadRepos = async (user: string) => {
    if (!user.trim()) {
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      // In a real implementation, this would call GitHub API
      // For now, we'll use mock data
      await new Promise(resolve => setTimeout(resolve, 500));
      
      // Mock GitHub repos
      const mockRepos: GitHubRepo[] = [
        {
          name: 'swiftdevbot',
          fullName: 'user/swiftdevbot',
          description: 'Modular Telegram bot platform',
          stars: 42,
          forks: 8,
          watchers: 15,
          language: 'Python',
          url: 'https://github.com/user/swiftdevbot',
          updatedAt: '2024-01-15',
        },
        {
          name: 'web-dashboard',
          fullName: 'user/web-dashboard',
          description: 'React dashboard for SwiftDevBot',
          stars: 28,
          forks: 5,
          watchers: 10,
          language: 'TypeScript',
          url: 'https://github.com/user/web-dashboard',
          updatedAt: '2024-01-14',
        },
      ];
      
      setRepos(mockRepos);
      localStorage.setItem('sdb_github_username', user);
    } catch (err) {
      setError(t('home.github.error') || 'Failed to load repositories');
      console.error('Error loading GitHub repos:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (username.trim()) {
      loadRepos(username.trim());
    }
  };

  if (loading) {
    return <div className="text-center py-4 oneui-text-muted">Loading...</div>;
  }

  if (!username) {
    return (
      <div className="space-y-3">
        <div className="flex items-center gap-2 mb-3">
          <Github className="w-5 h-5" style={{ color: 'var(--oneui-primary)' }} />
          <span className="text-sm font-semibold" style={{ color: 'var(--oneui-text)' }}>
            {t('home.github.title') || 'GitHub Repositories'}
          </span>
        </div>
        <form onSubmit={handleSubmit} className="space-y-2">
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder={t('home.github.usernamePlaceholder') || 'GitHub username'}
            className="w-full px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
            style={{
              backgroundColor: 'var(--oneui-bg-alt)',
              borderColor: 'var(--oneui-border)',
              color: 'var(--oneui-text)',
            }}
          />
          <button
            type="submit"
            className="w-full px-4 py-2 text-sm bg-indigo-500 text-white rounded-lg hover:bg-indigo-600 transition-colors"
          >
            {t('home.github.load') || 'Load Repositories'}
          </button>
        </form>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <AlertCircle className="w-12 h-12 mx-auto mb-2 text-red-500" />
        <p className="text-sm oneui-text-muted">{error}</p>
        <button
          onClick={() => {
            setUsername('');
            setError(null);
          }}
          className="mt-4 text-sm text-indigo-500 hover:underline"
        >
          {t('home.github.changeUser') || 'Change username'}
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Github className="w-5 h-5" style={{ color: 'var(--oneui-primary)' }} />
          <span className="text-sm font-semibold" style={{ color: 'var(--oneui-text)' }}>
            {username}
          </span>
        </div>
        <button
          onClick={() => {
            setUsername('');
            setRepos([]);
          }}
          className="text-xs text-indigo-500 hover:underline"
        >
          {t('home.github.change') || 'Change'}
        </button>
      </div>

      {/* Repositories */}
      <div className="space-y-2 max-h-64 overflow-y-auto">
        {repos.length === 0 ? (
          <div className="text-center py-8">
            <Github className="w-12 h-12 mx-auto mb-2 oneui-text-muted" />
            <p className="text-sm oneui-text-muted">
              {t('home.github.noRepos') || 'No repositories found'}
            </p>
          </div>
        ) : (
          repos.map((repo) => (
            <div
              key={repo.name}
              className="p-3 rounded-lg border"
              style={{
                backgroundColor: 'var(--oneui-bg-alt)',
                borderColor: 'var(--oneui-border)',
              }}
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex-1 min-w-0">
                  <a
                    href={repo.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm font-semibold hover:text-indigo-500 transition-colors"
                    style={{ color: 'var(--oneui-text)' }}
                  >
                    {repo.name}
                  </a>
                  {repo.description && (
                    <p className="text-xs oneui-text-muted mt-1 line-clamp-2">
                      {repo.description}
                    </p>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-4 text-xs">
                <div className="flex items-center gap-1">
                  <Star className="w-3 h-3 oneui-text-muted" />
                  <span className="oneui-text-muted">{repo.stars}</span>
                </div>
                <div className="flex items-center gap-1">
                  <GitFork className="w-3 h-3 oneui-text-muted" />
                  <span className="oneui-text-muted">{repo.forks}</span>
                </div>
                <div className="flex items-center gap-1">
                  <Eye className="w-3 h-3 oneui-text-muted" />
                  <span className="oneui-text-muted">{repo.watchers}</span>
                </div>
                {repo.language && (
                  <span className="oneui-text-muted ml-auto">{repo.language}</span>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

