import { useEffect, useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { useI18n } from '../../contexts/I18nContext';
import { useNavigation } from '../../contexts/NavigationContext';
import { api, BotStats } from '../../api';
import { getFullName, getInitials } from '../../utils/userDisplay';
import { User, Shield, Zap, TrendingUp, Activity, AlertCircle, MessageSquare, Folder, Key, Grid } from 'lucide-react';

export const UserDashboard = () => {
  const { profile } = useAuth();
  const { t } = useI18n();
  const { navigateTo } = useNavigation();
  const [stats, setStats] = useState<BotStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      const botStats: BotStats = await api.getStats();
      setStats(botStats);
      
      // Also load modules count (only user plugins)
      try {
        const modules = await api.getModules(false);
        const activeModules = modules.filter(m => m.status === 'active' && !m.is_system_module).length;
        // Update stats with actual active user modules count
        if (stats) {
          setStats({ ...botStats, active_modules: activeModules });
        }
      } catch (err) {
        console.error('Error loading modules for stats:', err);
      }
    } catch (error) {
      console.error('Error loading stats:', error);
    } finally {
      setLoading(false);
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
          {t('userDashboard.welcome', { name: getFullName(profile) })}
        </h1>
        <p className="oneui-text-muted">{t('userDashboard.subtitle')}</p>
      </div>

      {/* Account Status Widget */}
      <div className="oneui-card mb-6">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-xl font-semibold flex-shrink-0">
            {getInitials(profile)}
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-bold mb-1" style={{ color: 'var(--oneui-text)' }}>
              {getFullName(profile)}
            </h3>
            <div className="flex items-center gap-3 flex-wrap">
              <span className={`oneui-badge ${profile?.role === 'admin' ? 'oneui-badge-danger' : 'oneui-badge-info'}`}>
                {profile?.role?.toUpperCase() || 'USER'}
              </span>
              <span className="oneui-badge oneui-badge-success">
                {t('userDashboard.accountActive')}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="mb-6">
        <h2 className="text-lg font-semibold mb-4" style={{ color: 'var(--oneui-text)' }}>
          {t('userDashboard.quickActions')}
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { icon: Zap, label: t('userDashboard.myModules'), color: 'oneui-stat-icon-primary', action: 'modulesHub' },
            { icon: Folder, label: t('userDashboard.myData'), color: 'oneui-stat-icon-success', action: 'data' },
            { icon: Key, label: t('userDashboard.apiKeys'), color: 'oneui-stat-icon-warning', action: 'developer' },
            { icon: Shield, label: t('userDashboard.security'), color: 'oneui-stat-icon-danger', action: 'security' },
          ].map((action) => {
            const Icon = action.icon;
            return (
              <button
                key={action.action}
                className="oneui-card hover:shadow-lg transition-all text-left"
                onClick={() => navigateTo(action.action)}
              >
                <div className={`oneui-stat-icon ${action.color} mb-3`}>
                  <Icon className="w-6 h-6" />
                </div>
                <p className="text-sm font-medium" style={{ color: 'var(--oneui-text)' }}>
                  {action.label}
                </p>
              </button>
            );
          })}
        </div>
      </div>

      {/* Stats Grid */}
      <div className="oneui-stats-grid mb-6">
        {[
          {
            labelKey: 'userDashboard.activeModules',
            value: stats?.active_modules || 0,
            icon: Zap,
            iconClass: 'oneui-stat-icon-primary',
            change: '+2',
            changePositive: true,
          },
          {
            labelKey: 'userDashboard.totalCommands',
            value: stats?.messages_today || 0,
            icon: Activity,
            iconClass: 'oneui-stat-icon-success',
            change: '+15%',
            changePositive: true,
          },
          {
            labelKey: 'userDashboard.storageUsed',
            value: '45%',
            icon: Folder,
            iconClass: 'oneui-stat-icon-warning',
            change: '2.3 GB',
            changePositive: false,
          },
        ].map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.labelKey} className="oneui-stat-card">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="oneui-stat-label">{t(stat.labelKey)}</div>
                  <div className="oneui-stat-value">{stat.value}</div>
                </div>
                <div className={`oneui-stat-icon ${stat.iconClass}`}>
                  <Icon className="w-6 h-6" />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Recent Activity & Announcements */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Activity */}
        <div className="oneui-card">
          <div className="oneui-card-header">
            <h3 className="oneui-card-title">{t('userDashboard.recentActivity')}</h3>
          </div>
          <div className="space-y-3">
            {[
              { action: t('userDashboard.activity.command'), details: '/start', time: '2 min ago', icon: MessageSquare },
              { action: t('userDashboard.activity.fileUpload'), details: 'document.pdf', time: '15 min ago', icon: Folder },
              { action: t('userDashboard.activity.settings'), details: t('userDashboard.activity.settingsChanged'), time: '1 hour ago', icon: Shield },
            ].map((activity, index) => {
              const Icon = activity.icon;
              return (
                <div
                  key={index}
                  className="flex items-center gap-3 p-3 rounded-lg"
                  style={{ backgroundColor: 'var(--oneui-bg-alt)' }}
                >
                  <div className="oneui-stat-icon oneui-stat-icon-primary">
                    <Icon className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate" style={{ color: 'var(--oneui-text)' }}>
                      {activity.action}
                    </p>
                    <p className="text-xs oneui-text-muted truncate">{activity.details}</p>
                  </div>
                  <span className="text-xs oneui-text-muted whitespace-nowrap">{activity.time}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* System Announcements */}
        <div className="oneui-card">
          <div className="oneui-card-header">
            <h3 className="oneui-card-title">{t('userDashboard.announcements')}</h3>
          </div>
          <div className="space-y-3">
            <div className="p-4 rounded-lg border-l-4" style={{
              backgroundColor: 'rgba(99, 102, 241, 0.1)',
              borderLeftColor: 'var(--oneui-primary)',
            }}>
              <div className="flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-indigo-500 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-medium mb-1" style={{ color: 'var(--oneui-text)' }}>
                    {t('userDashboard.announcement.newFeatures')}
                  </p>
                  <p className="text-xs oneui-text-muted">
                    {t('userDashboard.announcement.newFeaturesDesc')}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

