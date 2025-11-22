import { useEffect, useState } from 'react';
import { api, BotModule } from '../../api';
import { useI18n } from '../../contexts/I18nContext';
import { Box, TrendingUp } from 'lucide-react';

export const TopModulesWidget = () => {
  const { t } = useI18n();
  const [modules, setModules] = useState<BotModule[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadModules();
    const interval = setInterval(loadModules, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadModules = async () => {
    try {
      const data = await api.getModules(false);
      // Sort by status (active first) and take top 5
      const sorted = (data || [])
        .sort((a, b) => {
          if (a.status === 'active' && b.status !== 'active') return -1;
          if (a.status !== 'active' && b.status === 'active') return 1;
          return 0;
        })
        .slice(0, 5);
      setModules(sorted);
    } catch (error) {
      console.error('Error loading modules:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="text-center py-4 oneui-text-muted">Loading...</div>;
  }

  if (modules.length === 0) {
    return (
      <div className="text-center py-8">
        <Box className="w-12 h-12 mx-auto mb-2 oneui-text-muted" />
        <p className="text-sm oneui-text-muted">{t('home.noModules') || 'No modules available'}</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {modules.map((module, index) => (
        <div
          key={module.name}
          className="flex items-center justify-between p-3 rounded-lg"
          style={{ backgroundColor: 'var(--oneui-bg-alt)' }}
        >
          <div className="flex items-center gap-3 flex-1 min-w-0">
            <div className={`w-2 h-2 rounded-full ${
              module.status === 'active' ? 'bg-green-500' : 'bg-gray-400'
            }`} />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate" style={{ color: 'var(--oneui-text)' }}>
                {module.name}
              </p>
              {module.description && (
                <p className="text-xs oneui-text-muted truncate">{module.description}</p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            {index < 3 && (
              <TrendingUp className="w-4 h-4" style={{ color: 'var(--oneui-success)' }} />
            )}
            <span className={`text-xs px-2 py-1 rounded ${
              module.status === 'active'
                ? 'bg-green-500/20 text-green-500'
                : 'bg-gray-500/20 text-gray-500'
            }`}>
              {module.status}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
};

