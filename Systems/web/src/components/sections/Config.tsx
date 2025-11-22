import { useState } from 'react';
import { useI18n } from '../../contexts/I18nContext';
import { Sliders, Database, Key, Globe, Save, CheckCircle2 } from 'lucide-react';

export const Config = () => {
  const { t } = useI18n();
  const [config, setConfig] = useState({
    botToken: '••••••••••••••••••••',
    apiUrl: 'https://api.telegram.org',
    webhookUrl: 'https://your-domain.com/webhook',
    maxRetries: '3',
    timeout: '30',
  });

  const [saved, setSaved] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <div>
      {/* Page Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-2" style={{ color: 'var(--oneui-text)' }}>
          Core Configuration
        </h1>
        <p className="oneui-text-muted">Manage bot's core settings and parameters</p>
      </div>

      {/* Status Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        {[
          { icon: Database, label: 'Database', value: 'Connected', color: 'oneui-text-success' },
          { icon: Key, label: 'API Status', value: 'Active', color: 'oneui-text-primary' },
          { icon: Globe, label: 'Webhook', value: 'Running', color: 'oneui-text-primary' },
        ].map((status) => {
          const Icon = status.icon;
          return (
            <div key={status.label} className="oneui-card">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm oneui-text-muted mb-1">{status.label}</p>
                  <p className={`text-xl font-bold ${status.color}`}>{status.value}</p>
                </div>
                <div className={`oneui-stat-icon ${status.color.includes('success') ? 'oneui-stat-icon-success' : 'oneui-stat-icon-primary'}`}>
                  <Icon className="w-6 h-6" />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Configuration Form */}
      <form onSubmit={handleSave} className="space-y-6">
        {/* Authentication */}
        <div className="oneui-card">
          <div className="oneui-card-header">
            <div className="flex items-center gap-3">
              <div className="oneui-stat-icon oneui-stat-icon-primary">
                <Key className="w-5 h-5" />
              </div>
              <h3 className="oneui-card-title">Authentication</h3>
            </div>
          </div>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2" style={{ color: 'var(--oneui-text)' }}>
                Bot Token
              </label>
              <input
                type="password"
                value={config.botToken}
                onChange={(e) => setConfig({ ...config, botToken: e.target.value })}
                className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                style={{
                  backgroundColor: 'var(--oneui-bg-alt)',
                  borderColor: 'var(--oneui-border)',
                  color: 'var(--oneui-text)',
                }}
              />
            </div>
          </div>
        </div>

        {/* API Configuration */}
        <div className="oneui-card">
          <div className="oneui-card-header">
            <div className="flex items-center gap-3">
              <div className="oneui-stat-icon oneui-stat-icon-primary">
                <Globe className="w-5 h-5" />
              </div>
              <h3 className="oneui-card-title">API Configuration</h3>
            </div>
          </div>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2" style={{ color: 'var(--oneui-text)' }}>
                API URL
              </label>
              <input
                type="text"
                value={config.apiUrl}
                onChange={(e) => setConfig({ ...config, apiUrl: e.target.value })}
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
                Webhook URL
              </label>
              <input
                type="text"
                value={config.webhookUrl}
                onChange={(e) => setConfig({ ...config, webhookUrl: e.target.value })}
                className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                style={{
                  backgroundColor: 'var(--oneui-bg-alt)',
                  borderColor: 'var(--oneui-border)',
                  color: 'var(--oneui-text)',
                }}
              />
            </div>
          </div>
        </div>

        {/* Performance */}
        <div className="oneui-card">
          <div className="oneui-card-header">
            <div className="flex items-center gap-3">
              <div className="oneui-stat-icon oneui-stat-icon-warning">
                <Sliders className="w-5 h-5" />
              </div>
              <h3 className="oneui-card-title">Performance</h3>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2" style={{ color: 'var(--oneui-text)' }}>
                Max Retries
              </label>
              <input
                type="number"
                value={config.maxRetries}
                onChange={(e) => setConfig({ ...config, maxRetries: e.target.value })}
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
                Timeout (seconds)
              </label>
              <input
                type="number"
                value={config.timeout}
                onChange={(e) => setConfig({ ...config, timeout: e.target.value })}
                className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                style={{
                  backgroundColor: 'var(--oneui-bg-alt)',
                  borderColor: 'var(--oneui-border)',
                  color: 'var(--oneui-text)',
                }}
              />
            </div>
          </div>
        </div>

        {/* Save Button */}
        <div className="flex items-center gap-3">
          <button type="submit" className="oneui-btn oneui-btn-primary flex items-center gap-2">
            <Save className="w-4 h-4" />
            Save Configuration
          </button>
          {saved && (
            <div className="flex items-center gap-2 text-green-600 dark:text-green-400">
              <CheckCircle2 className="w-5 h-5" />
              <span className="text-sm font-medium">Configuration saved!</span>
            </div>
          )}
        </div>
      </form>
    </div>
  );
};
