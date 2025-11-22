import { useState, useEffect } from 'react';
import { useI18n } from '../../contexts/I18nContext';
import { api, AuditLog, AuditStats, ApiKey } from '../../api';
import { Shield, AlertTriangle, Activity, Key, Filter, RefreshCw, Search } from 'lucide-react';

export const SecurityOperations = () => {
  const { t } = useI18n();
  const [activeTab, setActiveTab] = useState<'audit' | 'access' | 'stats'>('audit');
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [auditStats, setAuditStats] = useState<AuditStats | null>(null);
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    module_name: '',
    event_type: '',
    severity: '',
  });

  useEffect(() => {
    if (activeTab === 'audit') {
      loadAuditLogs();
    } else if (activeTab === 'access') {
      loadApiKeys();
    } else if (activeTab === 'stats') {
      loadAuditStats();
    }
  }, [activeTab, filters]);

  const loadAuditLogs = async () => {
    try {
      setLoading(true);
      const params: any = { limit: 100 };
      if (filters.module_name) params.module_name = filters.module_name;
      if (filters.event_type) params.event_type = filters.event_type;
      if (filters.severity) params.severity = filters.severity;
      const data = await api.getAuditLogs(params);
      setAuditLogs(data || []);
    } catch (error) {
      console.error('Error loading audit logs:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadAuditStats = async () => {
    try {
      setLoading(true);
      const data = await api.getAuditStats();
      setAuditStats(data);
    } catch (error) {
      console.error('Error loading audit stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadApiKeys = async () => {
    try {
      setLoading(true);
      const data = await api.getApiKeys();
      setApiKeys(data || []);
    } catch (error) {
      console.error('Error loading API keys:', error);
    } finally {
      setLoading(false);
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'oneui-badge-danger';
      case 'high':
        return 'oneui-badge-warning';
      case 'medium':
        return 'oneui-badge-info';
      case 'low':
        return 'oneui-badge-success';
      default:
        return 'oneui-badge-secondary';
    }
  };

  const formatTimestamp = (timestamp: number) => {
    try {
      return new Date(timestamp * 1000).toLocaleString();
    } catch {
      return 'N/A';
    }
  };

  return (
    <div>
      {/* Page Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-2" style={{ color: 'var(--oneui-text)' }}>
          {t('soc.title') || 'Security Operations Center'}
        </h1>
        <p className="oneui-text-muted">
          {t('soc.subtitle') || 'Monitor and manage security events, access control, and threats'}
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 border-b" style={{ borderColor: 'var(--oneui-border)' }}>
        {[
          { id: 'audit', label: t('soc.auditLogs') || 'Audit Logs', icon: Shield },
          { id: 'access', label: t('soc.accessControl') || 'Access Control', icon: Key },
          { id: 'stats', label: t('soc.statistics') || 'Statistics', icon: Activity },
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

      {/* Audit Logs */}
      {activeTab === 'audit' && (
        <div className="space-y-4">
          {/* Filters */}
          <div className="oneui-card">
            <div className="oneui-card-header">
              <div className="flex items-center gap-3">
                <Filter className="w-5 h-5" />
                <h3 className="oneui-card-title">{t('soc.filters') || 'Filters'}</h3>
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2" style={{ color: 'var(--oneui-text)' }}>
                  {t('soc.moduleName') || 'Module Name'}
                </label>
                <input
                  type="text"
                  value={filters.module_name}
                  onChange={(e) => setFilters({ ...filters, module_name: e.target.value })}
                  placeholder={t('soc.filterByModule') || 'Filter by module...'}
                  className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  style={{
                    backgroundColor: 'var(--oneui-bg-alt)',
                    borderColor: 'var(--oneui-border)',
                    color: 'var(--oneui-text)',
                  }}
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2" style={{ color: 'var(--oneui-text)' }}>
                  {t('soc.eventType') || 'Event Type'}
                </label>
                <select
                  value={filters.event_type}
                  onChange={(e) => setFilters({ ...filters, event_type: e.target.value })}
                  className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  style={{
                    backgroundColor: 'var(--oneui-bg-alt)',
                    borderColor: 'var(--oneui-border)',
                    color: 'var(--oneui-text)',
                  }}
                >
                  <option value="">{t('soc.allTypes') || 'All Types'}</option>
                  <option value="module_load">Module Load</option>
                  <option value="command_execution">Command Execution</option>
                  <option value="database_access">Database Access</option>
                  <option value="security_violation">Security Violation</option>
                  <option value="admin_function_access">Admin Function Access</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-2" style={{ color: 'var(--oneui-text)' }}>
                  {t('soc.severity') || 'Severity'}
                </label>
                <select
                  value={filters.severity}
                  onChange={(e) => setFilters({ ...filters, severity: e.target.value })}
                  className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  style={{
                    backgroundColor: 'var(--oneui-bg-alt)',
                    borderColor: 'var(--oneui-border)',
                    color: 'var(--oneui-text)',
                  }}
                >
                  <option value="">{t('soc.allSeverities') || 'All Severities'}</option>
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
                </select>
              </div>
            </div>
            <div className="mt-4">
              <button
                onClick={loadAuditLogs}
                className="oneui-btn oneui-btn-primary flex items-center gap-2"
              >
                <RefreshCw className="w-4 h-4" />
                {t('common.refresh') || 'Refresh'}
              </button>
            </div>
          </div>

          {/* Logs Table */}
          <div className="oneui-card">
            {loading ? (
              <div className="flex items-center justify-center py-8">
                <div className="oneui-spinner"></div>
              </div>
            ) : auditLogs.length === 0 ? (
              <div className="text-center py-12">
                <Shield className="w-16 h-16 mx-auto mb-4 oneui-text-muted" />
                <h3 className="text-xl font-bold mb-2" style={{ color: 'var(--oneui-text)' }}>
                  {t('soc.noLogs') || 'No audit logs found'}
                </h3>
                <p className="oneui-text-muted">
                  {t('soc.noLogsDesc') || 'No security events match your filters.'}
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="oneui-table min-w-full">
                  <thead>
                    <tr>
                      <th>{t('soc.timestamp') || 'Timestamp'}</th>
                      <th>{t('soc.eventType') || 'Event Type'}</th>
                      <th>{t('soc.module') || 'Module'}</th>
                      <th>{t('soc.severity') || 'Severity'}</th>
                      <th>{t('soc.user') || 'User'}</th>
                      <th>{t('soc.ip') || 'IP Address'}</th>
                      <th>{t('soc.status') || 'Status'}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {auditLogs.map((log) => (
                      <tr key={log.event_id}>
                        <td className="oneui-text-muted text-sm">
                          {formatTimestamp(log.timestamp)}
                        </td>
                        <td>
                          <code className="text-sm font-mono" style={{ color: 'var(--oneui-text)' }}>
                            {log.event_type}
                          </code>
                        </td>
                        <td className="font-medium" style={{ color: 'var(--oneui-text)' }}>
                          {log.module_name}
                        </td>
                        <td>
                          <span className={`oneui-badge ${getSeverityColor(log.severity)}`}>
                            {log.severity}
                          </span>
                        </td>
                        <td className="oneui-text-muted">
                          {log.user_id ? `#${log.user_id}` : '-'}
                        </td>
                        <td className="oneui-text-muted font-mono text-sm">
                          {log.ip_address || '-'}
                        </td>
                        <td>
                          {log.success ? (
                            <span className="oneui-badge oneui-badge-success">
                              {t('common.success') || 'Success'}
                            </span>
                          ) : (
                            <span className="oneui-badge oneui-badge-danger">
                              {t('common.error') || 'Error'}
                            </span>
                          )}
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

      {/* Access Control */}
      {activeTab === 'access' && (
        <div className="oneui-card">
          <div className="oneui-card-header">
            <div className="flex items-center justify-between w-full">
              <div className="flex items-center gap-3">
                <div className="oneui-stat-icon oneui-stat-icon-primary">
                  <Key className="w-5 h-5" />
                </div>
                <h3 className="oneui-card-title">
                  {t('soc.apiKeys') || 'API Keys'}
                </h3>
              </div>
              <button
                onClick={loadApiKeys}
                className="oneui-btn oneui-btn-secondary text-sm flex items-center gap-2"
              >
                <RefreshCw className="w-4 h-4" />
                {t('common.refresh') || 'Refresh'}
              </button>
            </div>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-8">
              <div className="oneui-spinner"></div>
            </div>
          ) : apiKeys.length === 0 ? (
            <div className="text-center py-12">
              <Key className="w-16 h-16 mx-auto mb-4 oneui-text-muted" />
              <h3 className="text-xl font-bold mb-2" style={{ color: 'var(--oneui-text)' }}>
                {t('soc.noApiKeys') || 'No API keys'}
              </h3>
              <p className="oneui-text-muted">
                {t('soc.noApiKeysDesc') || 'No API keys are configured. Use CLI to create keys.'}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="oneui-table min-w-full">
                <thead>
                  <tr>
                    <th>{t('soc.keyName') || 'Key Name'}</th>
                    <th>{t('soc.permissions') || 'Permissions'}</th>
                    <th>{t('soc.created') || 'Created'}</th>
                    <th>{t('soc.expires') || 'Expires'}</th>
                    <th>{t('soc.lastUsed') || 'Last Used'}</th>
                    <th>{t('soc.usageCount') || 'Usage Count'}</th>
                  </tr>
                </thead>
                <tbody>
                  {apiKeys.map((key) => (
                    <tr key={key.name}>
                      <td className="font-medium" style={{ color: 'var(--oneui-text)' }}>
                        {key.name}
                      </td>
                      <td>
                        <span className="oneui-badge oneui-badge-info">
                          {key.permissions}
                        </span>
                      </td>
                      <td className="oneui-text-muted">
                        {key.created_at ? new Date(key.created_at).toLocaleDateString() : '-'}
                      </td>
                      <td className="oneui-text-muted">
                        {key.expires_at ? new Date(key.expires_at).toLocaleDateString() : t('common.never') || 'Never'}
                      </td>
                      <td className="oneui-text-muted">
                        {key.last_used ? new Date(key.last_used).toLocaleString() : t('common.never') || 'Never'}
                      </td>
                      <td className="oneui-text-muted">
                        {key.usage_count || 0}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Statistics */}
      {activeTab === 'stats' && (
        <div className="space-y-6">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <div className="oneui-spinner"></div>
            </div>
          ) : auditStats ? (
            <>
              {/* Overview Cards */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div className="oneui-card">
                  <div className="oneui-card-header">
                    <h3 className="oneui-card-title">{t('soc.totalEvents') || 'Total Events'}</h3>
                  </div>
                  <div className="text-3xl font-bold" style={{ color: 'var(--oneui-text)' }}>
                    {auditStats.total_events || 0}
                  </div>
                </div>
                <div className="oneui-card">
                  <div className="oneui-card-header">
                    <h3 className="oneui-card-title">{t('soc.violations') || 'Violations'}</h3>
                  </div>
                  <div className="text-3xl font-bold" style={{ color: 'var(--oneui-danger)' }}>
                    {auditStats.violations_count || 0}
                  </div>
                </div>
                <div className="oneui-card">
                  <div className="oneui-card-header">
                    <h3 className="oneui-card-title">{t('soc.eventTypes') || 'Event Types'}</h3>
                  </div>
                  <div className="text-3xl font-bold" style={{ color: 'var(--oneui-text)' }}>
                    {Object.keys(auditStats.events_by_type || {}).length}
                  </div>
                </div>
                <div className="oneui-card">
                  <div className="oneui-card-header">
                    <h3 className="oneui-card-title">{t('soc.modules') || 'Modules'}</h3>
                  </div>
                  <div className="text-3xl font-bold" style={{ color: 'var(--oneui-text)' }}>
                    {Object.keys(auditStats.events_by_module || {}).length}
                  </div>
                </div>
              </div>

              {/* Events by Type */}
              <div className="oneui-card">
                <div className="oneui-card-header">
                  <h3 className="oneui-card-title">{t('soc.eventsByType') || 'Events by Type'}</h3>
                </div>
                <div className="overflow-x-auto">
                  <table className="oneui-table min-w-full">
                    <thead>
                      <tr>
                        <th>{t('soc.eventType') || 'Event Type'}</th>
                        <th>{t('soc.count') || 'Count'}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(auditStats.events_by_type || {}).map(([type, count]) => (
                        <tr key={type}>
                          <td className="font-medium" style={{ color: 'var(--oneui-text)' }}>
                            <code className="text-sm font-mono">{type}</code>
                          </td>
                          <td className="oneui-text-muted">{count as number}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Events by Severity */}
              <div className="oneui-card">
                <div className="oneui-card-header">
                  <h3 className="oneui-card-title">{t('soc.eventsBySeverity') || 'Events by Severity'}</h3>
                </div>
                <div className="overflow-x-auto">
                  <table className="oneui-table min-w-full">
                    <thead>
                      <tr>
                        <th>{t('soc.severity') || 'Severity'}</th>
                        <th>{t('soc.count') || 'Count'}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(auditStats.events_by_severity || {}).map(([severity, count]) => (
                        <tr key={severity}>
                          <td>
                            <span className={`oneui-badge ${getSeverityColor(severity)}`}>
                              {severity}
                            </span>
                          </td>
                          <td className="oneui-text-muted">{count as number}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          ) : (
            <div className="text-center py-12">
              <Activity className="w-16 h-16 mx-auto mb-4 oneui-text-muted" />
              <h3 className="text-xl font-bold mb-2" style={{ color: 'var(--oneui-text)' }}>
                {t('soc.noStats') || 'No statistics available'}
              </h3>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

