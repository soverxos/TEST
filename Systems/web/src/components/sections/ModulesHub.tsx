import { useEffect, useState } from 'react';
import { api, BotModule } from '../../api';
import { useI18n } from '../../contexts/I18nContext';
import { Box, Settings, ExternalLink, CheckCircle2, XCircle, AlertCircle } from 'lucide-react';

export const ModulesHub = () => {
  const { t } = useI18n();
  const [modules, setModules] = useState<BotModule[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadModules();
  }, []);

  const loadModules = async () => {
    try {
      // Load only user plugins (exclude system modules)
      const data = await api.getModules(false);
      // Filter out system modules on frontend as well (double check)
      const userModules = (data || []).filter(m => !m.is_system_module);
      setModules(userModules);
    } catch (error) {
      console.error('Error loading modules:', error);
      setModules([]);
    } finally {
      setLoading(false);
    }
  };

  const getModuleStatus = (module: BotModule) => {
    if (module.status === 'active') {
      return { label: t('modulesHub.active'), color: 'oneui-badge-success', icon: CheckCircle2 };
    }
    return { label: t('modulesHub.notConfigured'), color: 'oneui-badge-warning', icon: AlertCircle };
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="oneui-spinner"></div>
      </div>
    );
  }

  return (
    <div>
      {/* Page Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-2" style={{ color: 'var(--oneui-text)' }}>
          {t('modulesHub.title')}
        </h1>
        <p className="oneui-text-muted">{t('modulesHub.subtitle')}</p>
      </div>

      {/* Modules Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {modules.map((module) => {
          const status = getModuleStatus(module);
          const StatusIcon = status.icon;
          const isActive = module.status === 'active';

          return (
            <div key={module.name} className="oneui-card hover:shadow-lg transition-all">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className={`oneui-stat-icon ${isActive ? 'oneui-stat-icon-primary' : 'oneui-stat-icon-warning'}`}>
                    <Box className="w-6 h-6" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-lg mb-1" style={{ color: 'var(--oneui-text)' }}>
                      {module.display_name || module.name}
                    </h3>
                    <span className={`oneui-badge ${status.color} flex items-center gap-1 w-fit`}>
                      <StatusIcon className="w-3 h-3" />
                      {status.label}
                    </span>
                  </div>
                </div>
              </div>

              <p className="text-sm oneui-text-muted mb-4 line-clamp-2">
                {module.description || 'No description available'}
              </p>

              <div className="flex gap-2">
                {isActive ? (
                  <button className="oneui-btn oneui-btn-primary flex-1 flex items-center justify-center gap-2">
                    <ExternalLink className="w-4 h-4" />
                    {t('modulesHub.open')}
                  </button>
                ) : (
                  <button className="oneui-btn oneui-btn-secondary flex-1 flex items-center justify-center gap-2">
                    <Settings className="w-4 h-4" />
                    {t('modulesHub.configure')}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {modules.length === 0 && (
        <div className="oneui-card text-center py-12">
          <Box className="w-16 h-16 mx-auto mb-4 oneui-text-muted opacity-50" />
          <h3 className="text-xl font-bold mb-2" style={{ color: 'var(--oneui-text)' }}>
            {t('modulesHub.noModules')}
          </h3>
          <p className="text-sm oneui-text-muted max-w-md mx-auto mt-2">
            {t('modulesHub.noModulesDesc')}
          </p>
        </div>
      )}
    </div>
  );
};

