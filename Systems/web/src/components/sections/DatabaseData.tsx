import { useState, useEffect } from 'react';
import { useI18n } from '../../contexts/I18nContext';
import { api, Migration, CacheKey } from '../../api';
import { Database, Code, History, RefreshCw, Trash2, Play, ArrowUp, ArrowDown, Search } from 'lucide-react';

export const DatabaseData = () => {
  const { t } = useI18n();
  const [activeTab, setActiveTab] = useState<'sql' | 'migrations' | 'cache'>('sql');
  const [sqlQuery, setSqlQuery] = useState('SELECT * FROM users LIMIT 10;');
  const [sqlResult, setSqlResult] = useState<{columns: string[], data: Record<string, any>[], row_count: number} | null>(null);
  const [sqlError, setSqlError] = useState<string | null>(null);
  const [sqlLoading, setSqlLoading] = useState(false);
  const [migrations, setMigrations] = useState<Migration[]>([]);
  const [migrationsLoading, setMigrationsLoading] = useState(false);
  const [cacheKeys, setCacheKeys] = useState<CacheKey[]>([]);
  const [cachePattern, setCachePattern] = useState('');
  const [cacheLoading, setCacheLoading] = useState(false);

  useEffect(() => {
    if (activeTab === 'migrations') {
      loadMigrations();
    } else if (activeTab === 'cache') {
      loadCacheKeys();
    }
  }, [activeTab]);

  const executeQuery = async () => {
    if (!sqlQuery.trim()) return;
    
    setSqlLoading(true);
    setSqlError(null);
    setSqlResult(null);
    
    try {
      const result = await api.executeSqlQuery(sqlQuery);
      setSqlResult(result);
    } catch (error: any) {
      setSqlError(error.message || 'Query execution failed');
    } finally {
      setSqlLoading(false);
    }
  };

  const loadMigrations = async () => {
    try {
      setMigrationsLoading(true);
      const data = await api.getMigrations();
      setMigrations(data || []);
    } catch (error) {
      console.error('Error loading migrations:', error);
    } finally {
      setMigrationsLoading(false);
    }
  };

  const loadCacheKeys = async () => {
    try {
      setCacheLoading(true);
      const data = await api.getCacheKeys(cachePattern || undefined, 100);
      setCacheKeys(data || []);
    } catch (error) {
      console.error('Error loading cache keys:', error);
    } finally {
      setCacheLoading(false);
    }
  };

  const handleMigrationAction = async (action: 'upgrade' | 'downgrade', revision?: string) => {
    if (!confirm(t('database.confirmMigration') || `Execute ${action} migration?`)) return;
    
    try {
      const result = await api.migrationAction(action, revision);
      alert(result.message);
      await loadMigrations();
    } catch (error: any) {
      alert(`Failed: ${error.message || error}`);
    }
  };

  const handleFlushCache = async () => {
    if (!confirm(t('database.confirmFlushCache') || 'Flush all cache? This action cannot be undone.')) return;
    
    try {
      await api.flushCache();
      alert(t('database.cacheFlushed') || 'Cache flushed successfully');
      await loadCacheKeys();
    } catch (error: any) {
      alert(`Failed: ${error.message || error}`);
    }
  };

  return (
    <div>
      {/* Page Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-2" style={{ color: 'var(--oneui-text)' }}>
          {t('database.title') || 'Database & Data'}
        </h1>
        <p className="oneui-text-muted">
          {t('database.subtitle') || 'SQL Runner, Migrations, and Cache Management'}
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 border-b" style={{ borderColor: 'var(--oneui-border)' }}>
        {[
          { id: 'sql', label: t('database.sqlRunner') || 'SQL Runner', icon: Code },
          { id: 'migrations', label: t('database.migrations') || 'Migrations', icon: History },
          { id: 'cache', label: t('database.cache') || 'Cache Explorer', icon: Database },
        ].map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`px-4 py-2 flex items-center gap-2 border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                  : 'border-transparent oneui-text-muted hover:text-indigo-600 dark:hover:text-indigo-400'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span className="font-medium">{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* SQL Runner */}
      {activeTab === 'sql' && (
        <div className="space-y-4">
          <div className="oneui-card">
            <div className="oneui-card-header">
              <div className="flex items-center gap-3">
                <div className="oneui-stat-icon oneui-stat-icon-primary">
                  <Code className="w-5 h-5" />
                </div>
                <h3 className="oneui-card-title">{t('database.sqlRunner') || 'SQL Runner'}</h3>
              </div>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2" style={{ color: 'var(--oneui-text)' }}>
                  {t('database.query') || 'SQL Query (SELECT only)'}
                </label>
                <textarea
                  value={sqlQuery}
                  onChange={(e) => setSqlQuery(e.target.value)}
                  rows={8}
                  className="w-full px-4 py-2 border rounded-lg font-mono text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  style={{
                    backgroundColor: 'var(--oneui-bg-alt)',
                    borderColor: 'var(--oneui-border)',
                    color: 'var(--oneui-text)',
                  }}
                  placeholder="SELECT * FROM users LIMIT 10;"
                />
                <p className="text-xs oneui-text-muted mt-1">
                  {t('database.sqlNote') || 'Only SELECT queries are allowed for security.'}
                </p>
              </div>
              <button
                onClick={executeQuery}
                disabled={sqlLoading || !sqlQuery.trim()}
                className="oneui-btn oneui-btn-primary flex items-center gap-2"
              >
                <Play className="w-4 h-4" />
                {sqlLoading ? (t('common.loading') || 'Loading...') : (t('database.execute') || 'Execute')}
              </button>
            </div>
          </div>

          {/* Results */}
          {sqlError && (
            <div className="oneui-card">
              <div className="p-4 rounded-lg" style={{ backgroundColor: 'rgba(239, 68, 68, 0.1)', borderLeft: '4px solid var(--oneui-danger)' }}>
                <p className="text-sm font-medium" style={{ color: 'var(--oneui-danger)' }}>
                  {t('common.error') || 'Error'}: {sqlError}
                </p>
              </div>
            </div>
          )}

          {sqlResult && (
            <div className="oneui-card">
              <div className="oneui-card-header">
                <h3 className="oneui-card-title">
                  {t('database.results') || 'Results'} ({sqlResult.row_count} {t('database.rows') || 'rows'})
                </h3>
              </div>
              <div className="overflow-x-auto">
                <table className="oneui-table min-w-full">
                  <thead>
                    <tr>
                      {sqlResult.columns.map((col) => (
                        <th key={col}>{col}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {sqlResult.data.map((row, idx) => (
                      <tr key={idx}>
                        {sqlResult.columns.map((col) => (
                          <td key={col} className="oneui-text-muted text-sm">
                            {row[col] !== null && row[col] !== undefined ? String(row[col]) : 'NULL'}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Migrations */}
      {activeTab === 'migrations' && (
        <div className="space-y-4">
          <div className="oneui-card">
            <div className="oneui-card-header">
              <div className="flex items-center justify-between w-full">
                <div className="flex items-center gap-3">
                  <div className="oneui-stat-icon oneui-stat-icon-primary">
                    <History className="w-5 h-5" />
                  </div>
                  <h3 className="oneui-card-title">{t('database.migrations') || 'Migrations'}</h3>
                </div>
                <button
                  onClick={loadMigrations}
                  className="oneui-btn oneui-btn-secondary text-sm flex items-center gap-2"
                >
                  <RefreshCw className="w-4 h-4" />
                  {t('common.refresh') || 'Refresh'}
                </button>
              </div>
            </div>

            {migrationsLoading ? (
              <div className="flex items-center justify-center py-8">
                <div className="oneui-spinner"></div>
              </div>
            ) : migrations.length === 0 ? (
              <div className="text-center py-12">
                <History className="w-16 h-16 mx-auto mb-4 oneui-text-muted" />
                <h3 className="text-xl font-bold mb-2" style={{ color: 'var(--oneui-text)' }}>
                  {t('database.noMigrations') || 'No migrations found'}
                </h3>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="oneui-table min-w-full">
                  <thead>
                    <tr>
                      <th>{t('database.revision') || 'Revision'}</th>
                      <th>{t('database.description') || 'Description'}</th>
                      <th>{t('database.status') || 'Status'}</th>
                      <th>{t('common.actions') || 'Actions'}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {migrations.map((migration) => (
                      <tr key={migration.revision}>
                        <td>
                          <code className="text-sm font-mono" style={{ color: 'var(--oneui-text)' }}>
                            {migration.revision}
                          </code>
                        </td>
                        <td className="oneui-text-muted">
                          {migration.doc || '-'}
                        </td>
                        <td>
                          {migration.is_current ? (
                            <span className="oneui-badge oneui-badge-success">
                              {t('database.current') || 'Current'}
                            </span>
                          ) : (
                            <span className="oneui-badge oneui-badge-secondary">
                              {t('database.pending') || 'Pending'}
                            </span>
                          )}
                        </td>
                        <td>
                          <div className="flex gap-2">
                            {!migration.is_current && (
                              <button
                                onClick={() => handleMigrationAction('upgrade', migration.revision)}
                                className="oneui-btn oneui-btn-secondary text-sm flex items-center gap-1"
                                title={t('database.upgrade') || 'Upgrade'}
                              >
                                <ArrowUp className="w-3 h-3" />
                              </button>
                            )}
                            {migration.is_current && migration.down_revision && (
                              <button
                                onClick={() => handleMigrationAction('downgrade', migration.down_revision || undefined)}
                                className="oneui-btn oneui-btn-secondary text-sm flex items-center gap-1"
                                title={t('database.downgrade') || 'Downgrade'}
                              >
                                <ArrowDown className="w-3 h-3" />
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Cache Explorer */}
      {activeTab === 'cache' && (
        <div className="space-y-4">
          <div className="oneui-card">
            <div className="oneui-card-header">
              <div className="flex items-center justify-between w-full">
                <div className="flex items-center gap-3">
                  <div className="oneui-stat-icon oneui-stat-icon-primary">
                    <Database className="w-5 h-5" />
                  </div>
                  <h3 className="oneui-card-title">{t('database.cacheExplorer') || 'Cache Explorer'}</h3>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={handleFlushCache}
                    className="oneui-btn oneui-btn-secondary text-sm flex items-center gap-2"
                  >
                    <Trash2 className="w-4 h-4" />
                    {t('database.flushCache') || 'Flush Cache'}
                  </button>
                  <button
                    onClick={loadCacheKeys}
                    className="oneui-btn oneui-btn-secondary text-sm flex items-center gap-2"
                  >
                    <RefreshCw className="w-4 h-4" />
                    {t('common.refresh') || 'Refresh'}
                  </button>
                </div>
              </div>
            </div>

            <div className="mb-4">
              <div className="flex gap-2">
                <div className="flex-1 relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 oneui-text-muted" />
                  <input
                    type="text"
                    value={cachePattern}
                    onChange={(e) => setCachePattern(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && loadCacheKeys()}
                    placeholder={t('database.searchPattern') || 'Search pattern (e.g., user:* or *)...'}
                    className="w-full pl-10 pr-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    style={{
                      backgroundColor: 'var(--oneui-bg-alt)',
                      borderColor: 'var(--oneui-border)',
                      color: 'var(--oneui-text)',
                    }}
                  />
                </div>
                <button
                  onClick={loadCacheKeys}
                  className="oneui-btn oneui-btn-primary"
                >
                  {t('database.search') || 'Search'}
                </button>
              </div>
            </div>

            {cacheLoading ? (
              <div className="flex items-center justify-center py-8">
                <div className="oneui-spinner"></div>
              </div>
            ) : cacheKeys.length === 0 ? (
              <div className="text-center py-12">
                <Database className="w-16 h-16 mx-auto mb-4 oneui-text-muted" />
                <h3 className="text-xl font-bold mb-2" style={{ color: 'var(--oneui-text)' }}>
                  {t('database.noCacheKeys') || 'No cache keys found'}
                </h3>
                <p className="oneui-text-muted">
                  {t('database.noCacheKeysDesc') || 'No keys match your search pattern.'}
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="oneui-table min-w-full">
                  <thead>
                    <tr>
                      <th>{t('database.key') || 'Key'}</th>
                      <th>{t('database.ttl') || 'TTL'}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {cacheKeys.map((item) => (
                      <tr key={item.key}>
                        <td>
                          <code className="text-sm font-mono" style={{ color: 'var(--oneui-text)' }}>
                            {item.key}
                          </code>
                        </td>
                        <td className="oneui-text-muted">
                          {item.ttl !== null ? `${item.ttl}s` : t('database.noExpiry') || 'No expiry'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

