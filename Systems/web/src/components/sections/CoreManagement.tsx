import { useState, useEffect } from 'react';
import { useI18n } from '../../contexts/I18nContext';
import { api, Service, FeatureFlag } from '../../api';
import { Settings, Play, Square, RotateCw, ToggleLeft, ToggleRight, Save, RefreshCw } from 'lucide-react';
import Editor from '@monaco-editor/react';

export const CoreManagement = () => {
  const { t } = useI18n();
  const [activeTab, setActiveTab] = useState<'config' | 'services' | 'flags'>('config');
  const [configContent, setConfigContent] = useState('');
  const [services, setServices] = useState<Service[]>([]);
  const [featureFlags, setFeatureFlags] = useState<FeatureFlag[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadData();
  }, [activeTab]);

  const loadData = async () => {
    try {
      setLoading(true);
      if (activeTab === 'config') {
        const config = await api.getConfig();
        setConfigContent(config.content);
      } else if (activeTab === 'services') {
        const servicesData = await api.getServices();
        setServices(servicesData);
      } else if (activeTab === 'flags') {
        const flags = await api.getFeatureFlags();
        setFeatureFlags(flags);
      }
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleServiceAction = async (serviceId: string, action: 'start' | 'stop' | 'restart') => {
    try {
      await api.serviceAction(serviceId, action);
      // Reload services to get updated status
      await loadData();
    } catch (error: any) {
      console.error('Error performing service action:', error);
      alert(`Failed to ${action} service: ${error.message || error}`);
    }
  };

  const toggleFeatureFlag = async (flagName: string) => {
    const flag = featureFlags.find(f => f.name === flagName);
    if (!flag) return;
    
    try {
      await api.updateFeatureFlag(flagName, !flag.enabled);
      setFeatureFlags(prev => prev.map(f => 
        f.name === flagName ? { ...f, enabled: !f.enabled } : f
      ));
    } catch (error: any) {
      console.error('Error updating feature flag:', error);
      alert(`Failed to update feature flag: ${error.message || error}`);
    }
  };

  const saveConfig = async () => {
    try {
      setSaving(true);
      await api.updateConfig(configContent);
      alert('Configuration saved successfully! Restart required to apply changes.');
    } catch (error: any) {
      console.error('Error saving config:', error);
      alert(`Failed to save config: ${error.message || error}`);
    } finally {
      setSaving(false);
    }
  };

  const reloadConfig = async () => {
    try {
      const result = await api.reloadConfig();
      alert(result.message);
    } catch (error: any) {
      console.error('Error reloading config:', error);
      alert(`Failed to reload config: ${error.message || error}`);
    }
  };

  return (
    <div>
      {/* Page Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-2" style={{ color: 'var(--oneui-text)' }}>
          🧠 Core Management
        </h1>
        <p className="oneui-text-muted">Manage core system configuration and services</p>
      </div>

      {loading && (
        <div className="flex items-center justify-center h-64">
          <div className="oneui-spinner"></div>
        </div>
      )}

      {!loading && (
        <>
      {/* Tabs */}
      <div className="flex gap-2 mb-6 border-b" style={{ borderColor: 'var(--oneui-border)' }}>
        {[
          { id: 'config', label: 'Configuration Editor', icon: Settings },
          { id: 'services', label: 'Services Controller', icon: Play },
          { id: 'flags', label: 'Feature Flags', icon: ToggleRight },
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

      {/* Configuration Editor */}
      {activeTab === 'config' && (
        <div className="oneui-card">
          <div className="oneui-card-header">
            <div className="flex items-center justify-between w-full">
              <h3 className="oneui-card-title">Core Settings Editor</h3>
              <div className="flex gap-2">
                <button onClick={reloadConfig} className="oneui-btn oneui-btn-secondary flex items-center gap-2">
                  <RefreshCw className="w-4 h-4" />
                  Hot Reload
                </button>
                <button onClick={saveConfig} className="oneui-btn oneui-btn-primary flex items-center gap-2">
                  <Save className="w-4 h-4" />
                  Save
                </button>
              </div>
            </div>
          </div>
          <div className="mt-4" style={{ height: '500px', border: '1px solid var(--oneui-border)', borderRadius: '0.5rem' }}>
            <Editor
              height="100%"
              defaultLanguage="yaml"
              value={configContent}
              onChange={(value) => setConfigContent(value || '')}
              theme="vs-dark"
              options={{
                minimap: { enabled: false },
                fontSize: 14,
                wordWrap: 'on',
                automaticLayout: true,
              }}
            />
          </div>
        </div>
      )}

      {/* Services Controller */}
      {activeTab === 'services' && (
        <div className="oneui-card">
          <div className="oneui-card-header">
            <h3 className="oneui-card-title">System Services</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="oneui-table min-w-full">
              <thead>
                <tr>
                  <th>Service</th>
                  <th>Description</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {services.map((service) => (
                  <tr key={service.id}>
                    <td className="font-medium" style={{ color: 'var(--oneui-text)' }}>
                      {service.name}
                    </td>
                    <td className="oneui-text-muted">{service.description}</td>
                    <td>
                      <span className={`oneui-badge ${
                        service.status === 'running' ? 'oneui-badge-success' :
                        service.status === 'restarting' ? 'oneui-badge-warning' :
                        'oneui-badge-danger'
                      }`}>
                        {service.status}
                      </span>
                    </td>
                    <td>
                      <div className="flex gap-2">
                        {service.status === 'running' ? (
                          <>
                            <button
                              onClick={() => handleServiceAction(service.id, 'stop')}
                              className="oneui-btn oneui-btn-secondary text-sm"
                            >
                              <Square className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => handleServiceAction(service.id, 'restart')}
                              className="oneui-btn oneui-btn-secondary text-sm"
                              disabled={service.status === 'restarting'}
                            >
                              <RotateCw className="w-4 h-4" />
                            </button>
                          </>
                        ) : (
                          <button
                            onClick={() => handleServiceAction(service.id, 'start')}
                            className="oneui-btn oneui-btn-primary text-sm"
                          >
                            <Play className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Feature Flags */}
      {activeTab === 'flags' && (
        <div className="oneui-card">
          <div className="oneui-card-header">
            <h3 className="oneui-card-title">Feature Flags</h3>
          </div>
          <div className="space-y-4">
            {featureFlags.map((flag) => (
              <div
                key={flag.name}
                className="p-4 rounded-lg border"
                style={{
                  backgroundColor: 'var(--oneui-bg-alt)',
                  borderColor: 'var(--oneui-border)',
                }}
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h4 className="font-semibold" style={{ color: 'var(--oneui-text)' }}>
                        {flag.name}
                      </h4>
                      <label className="relative inline-flex items-center cursor-pointer">
                        <input
                          type="checkbox"
                          className="sr-only peer"
                          checked={flag.enabled}
                          onChange={() => toggleFeatureFlag(flag.name)}
                        />
                        <div className="w-11 h-6 bg-gray-300 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-indigo-300 dark:peer-focus:ring-indigo-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all dark:after:border-gray-600 peer-checked:bg-indigo-600"></div>
                      </label>
                    </div>
                    <p className="text-sm oneui-text-muted">{flag.description}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
        </>
      )}
    </div>
  );
};

