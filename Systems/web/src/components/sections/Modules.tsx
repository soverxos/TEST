import { useEffect, useState } from 'react';
import { api, BotModule } from '../../api';
import { useAuth } from '../../contexts/AuthContext';
import { useI18n } from '../../contexts/I18nContext';
import { Box, CheckCircle2, XCircle, Loader2, MoreVertical } from 'lucide-react';

export const Modules = () => {
  const { isAdmin } = useAuth();
  const { t } = useI18n();
  const [modules, setModules] = useState<BotModule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyModule, setBusyModule] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    loadModules();
  }, []);

  const loadModules = async () => {
    try {
      const data = await api.getModules();
      setModules(data || []);
    } catch (error) {
      console.error('Error loading modules:', error);
      setError(t('modules.errorToggle'));
    } finally {
      setLoading(false);
    }
  };

  const toggleModuleStatus = async (moduleName: string, currentStatus: string) => {
    if (!isAdmin) return;

    setBusyModule(moduleName);
    setError(null);
    setMessage(null);
    try {
      await api.toggleModuleStatus(moduleName, currentStatus !== 'active');
      setModules(prev => prev.map(m =>
        m.name === moduleName ? { ...m, status: currentStatus === 'active' ? 'inactive' : 'active' } : m
      ));
      setMessage(currentStatus === 'active' 
        ? t('modules.moduleDeactivated', { name: moduleName })
        : t('modules.moduleActivated', { name: moduleName })
      );
      setTimeout(() => setMessage(null), 5000);
    } catch (error) {
      console.error('Error toggling module status:', error);
      setError(t('modules.errorToggle'));
      setTimeout(() => setError(null), 5000);
    } finally {
      setBusyModule(null);
    }
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
          {t('modules.title')}
        </h1>
        <p className="oneui-text-muted">{t('modules.subtitle')}</p>
      </div>

      {/* Messages */}
      {error && (
        <div className="oneui-card mb-6 border-l-4" style={{ borderLeftColor: 'var(--oneui-danger)' }}>
          <div className="flex items-center gap-3 text-red-600 dark:text-red-400">
            <XCircle className="w-5 h-5" />
            <p className="font-medium">{error}</p>
          </div>
        </div>
      )}
      {message && (
        <div className="oneui-card mb-6 border-l-4" style={{ borderLeftColor: 'var(--oneui-success)' }}>
          <div className="flex items-center gap-3 text-green-600 dark:text-green-400">
            <CheckCircle2 className="w-5 h-5" />
            <p className="font-medium">{message}</p>
          </div>
        </div>
      )}

      {/* Modules Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {modules.map((module) => {
          const isActive = module.status === 'active';

          return (
            <div key={module.name} className="oneui-card hover:shadow-lg transition-shadow">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${
                    isActive ? 'bg-indigo-100 dark:bg-indigo-900/20' : 'bg-gray-100 dark:bg-gray-800'
                  }`}>
                    <Box className={`w-6 h-6 ${isActive ? 'text-indigo-600 dark:text-indigo-400' : 'text-gray-400'}`} />
                  </div>
                  <div>
                    <h3 className="font-semibold text-lg" style={{ color: 'var(--oneui-text)' }}>
                      {module.name}
                    </h3>
                    <span className={`oneui-badge ${isActive ? 'oneui-badge-success' : 'oneui-badge-danger'}`}>
                      {isActive ? t('common.active') : t('common.inactive')}
                    </span>
                  </div>
                </div>
                <button className="oneui-btn-icon">
                  <MoreVertical className="w-4 h-4" />
                </button>
              </div>

              <p className="text-sm oneui-text-muted mb-4 line-clamp-2">
                {module.description || 'No description available'}
              </p>

              {isAdmin && (
                <button
                  onClick={() => toggleModuleStatus(module.name, module.status)}
                  disabled={busyModule === module.name}
                  className={`oneui-btn w-full ${
                    isActive ? 'oneui-btn-secondary' : 'oneui-btn-primary'
                  }`}
                >
                  {busyModule === module.name ? (
                    <span className="flex items-center justify-center gap-2">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      {t('common.loading')}
                    </span>
                  ) : (
                    <span className="flex items-center justify-center gap-2">
                      {isActive ? (
                        <>
                          <XCircle className="w-4 h-4" />
                          {t('modules.deactivate')}
                        </>
                      ) : (
                        <>
                          <CheckCircle2 className="w-4 h-4" />
                          {t('modules.activate')}
                        </>
                      )}
                    </span>
                  )}
                </button>
              )}
            </div>
          );
        })}
      </div>

      {modules.length === 0 && (
        <div className="oneui-card text-center py-12">
          <Box className="w-16 h-16 mx-auto mb-4 oneui-text-muted opacity-50" />
          <h3 className="text-xl font-bold mb-2" style={{ color: 'var(--oneui-text)' }}>
            {t('modules.noModules')}
          </h3>
          <p className="oneui-text-muted">{t('modules.noModulesDesc')}</p>
        </div>
      )}
    </div>
  );
};
