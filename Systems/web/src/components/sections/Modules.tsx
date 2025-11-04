import { useEffect, useState } from 'react';
import { api, BotModule } from '../../lib/api';
import { useAuth } from '../../contexts/AuthContext';
import { GlassCard } from '../ui/GlassCard';
import { GlassButton } from '../ui/GlassButton';
import { Box } from 'lucide-react';

export const Modules = () => {
  const { isAdmin } = useAuth();
  const [modules, setModules] = useState<BotModule[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadModules();
  }, []);

  const loadModules = async () => {
    try {
      const data = await api.getModules();
      setModules(data || []);
    } catch (error) {
      console.error('Error loading modules:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleModuleStatus = async (moduleName: string, currentStatus: string) => {
    if (!isAdmin) return;

    // TODO: Implement module toggle API endpoint
    const newStatus = currentStatus === 'active' ? 'inactive' : 'active';
    setModules(modules.map(m => 
      m.name === moduleName ? { ...m, status: newStatus as 'active' | 'inactive' } : m
    ));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="loading-spinner"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-glass-text mb-2">Bot Modules</h2>
          <p className="text-glass-text-secondary">Manage your bot's functionality modules</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {modules.map((module) => {
          const isActive = module.status === 'active';
          const color = isActive ? '#06b6d4' : '#6b7280';

          return (
            <GlassCard key={module.name} hover glow className="p-6">
              <div className="flex items-start justify-between mb-4">
                <div
                  className="p-3 rounded-xl"
                  style={{
                    backgroundColor: `${color}20`,
                    borderColor: `${color}40`,
                    borderWidth: '1px',
                  }}
                >
                  <Box
                    className="w-6 h-6"
                    style={{ color }}
                  />
                </div>
                <div
                  className={`
                    px-3 py-1 rounded-full text-xs font-semibold
                    ${isActive
                      ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                      : 'bg-gray-500/20 text-gray-400 border border-gray-500/30'
                    }
                  `}
                >
                  {isActive ? 'Active' : 'Inactive'}
                </div>
              </div>

              <h3 className="text-xl font-bold text-glass-text mb-2">{module.name}</h3>
              <p className="text-glass-text-secondary text-sm mb-4 line-clamp-2">
                {module.description}
              </p>

              {isAdmin && (
                <GlassButton
                  variant={isActive ? 'secondary' : 'primary'}
                  size="sm"
                  className="w-full"
                  onClick={() => toggleModuleStatus(module.name, module.status)}
                >
                  {isActive ? 'Deactivate' : 'Activate'}
                </GlassButton>
              )}
            </GlassCard>
          );
        })}
      </div>
    </div>
  );
};
