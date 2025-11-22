import { useEffect, useState } from 'react';
import { api, BotStats } from '../../api';
import { useI18n } from '../../contexts/I18nContext';
import { Activity, Users, Zap, TrendingUp, ArrowUpRight, ArrowDownRight } from 'lucide-react';

type Stats = {
  activeModules: number;
  totalUsers: number;
  todayInteractions: number;
  systemStatus: 'online' | 'degraded' | 'offline';
};

export const Home = () => {
  const { t } = useI18n();
  const [stats, setStats] = useState<Stats>({
    activeModules: 0,
    totalUsers: 0,
    todayInteractions: 0,
    systemStatus: 'online',
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStats();
    const interval = setInterval(loadStats, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadStats = async () => {
    try {
      const botStats: BotStats = await api.getStats();
      setStats({
        activeModules: botStats.active_modules || 0,
        totalUsers: botStats.total_users || 0,
        todayInteractions: botStats.messages_today || 0,
        systemStatus: 'online',
      });
    } catch (error) {
      console.error('Error loading stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const statCards = [
    {
      labelKey: 'home.activeModules',
      value: stats.activeModules,
      icon: Zap,
      iconClass: 'oneui-stat-icon-primary',
      change: '+2.5%',
      changePositive: true,
    },
    {
      labelKey: 'home.totalUsers',
      value: stats.totalUsers,
      icon: Users,
      iconClass: 'oneui-stat-icon-success',
      change: '+3.8%',
      changePositive: true,
    },
    {
      labelKey: 'home.todayInteractions',
      value: stats.todayInteractions,
      icon: TrendingUp,
      iconClass: 'oneui-stat-icon-warning',
      change: '+1.7%',
      changePositive: true,
    },
    {
      labelKey: 'home.systemStatus',
      value: stats.systemStatus.toUpperCase(),
      icon: Activity,
      iconClass: 'oneui-stat-icon-success',
      change: '100%',
      changePositive: true,
    },
  ];

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
          {t('home.title')}
        </h1>
        <p className="oneui-text-muted">{t('home.subtitle')}</p>
      </div>

      {/* Stats Grid */}
      <div className="oneui-stats-grid">
        {statCards.map((card) => {
          const Icon = card.icon;
          return (
            <div key={card.labelKey} className="oneui-stat-card">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="oneui-stat-label">{t(card.labelKey)}</div>
                  <div className="oneui-stat-value">{card.value}</div>
                  <div className="flex items-center gap-1 mt-2 text-sm" style={{ color: card.changePositive ? 'var(--oneui-success)' : 'var(--oneui-danger)' }}>
                    {card.changePositive ? (
                      <ArrowUpRight className="w-4 h-4" />
                    ) : (
                      <ArrowDownRight className="w-4 h-4" />
                    )}
                    <span>{card.change}</span>
                  </div>
                </div>
                <div className={card.iconClass}>
                  <Icon className="w-6 h-6" />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Activity */}
        <div className="oneui-card">
          <div className="oneui-card-header">
            <h3 className="oneui-card-title">{t('home.recentActivity')}</h3>
          </div>
          <div className="space-y-3">
            {[
              { action: 'Module activated', module: 'AI Chat', time: '2 minutes ago', color: 'success' },
              { action: 'User registered', module: 'System', time: '15 minutes ago', color: 'info' },
              { action: 'Code review completed', module: 'Code Review', time: '1 hour ago', color: 'success' },
              { action: 'Analytics updated', module: 'Analytics', time: '2 hours ago', color: 'info' },
            ].map((activity, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                style={{ backgroundColor: 'var(--oneui-bg-alt)' }}
              >
                <div className="flex items-center gap-3">
                  <div className={`w-2 h-2 rounded-full ${
                    activity.color === 'success' ? 'bg-green-500' : 'bg-blue-500'
                  }`}></div>
                  <div>
                    <p className="text-sm font-medium" style={{ color: 'var(--oneui-text)' }}>
                      {activity.action}
                    </p>
                    <p className="text-xs oneui-text-muted">{activity.module}</p>
                  </div>
                </div>
                <span className="text-xs oneui-text-muted">{activity.time}</span>
              </div>
            ))}
          </div>
        </div>

        {/* System Health */}
        <div className="oneui-card">
          <div className="oneui-card-header">
            <h3 className="oneui-card-title">{t('home.systemHealth')}</h3>
          </div>
          <div className="space-y-5">
            {[
              { metricKey: 'home.cpuUsage', value: 45, color: 'primary' },
              { metricKey: 'home.memory', value: 62, color: 'success' },
              { metricKey: 'home.network', value: 28, color: 'info' },
              { metricKey: 'home.storage', value: 71, color: 'warning' },
            ].map((metric) => (
              <div key={metric.metricKey}>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium" style={{ color: 'var(--oneui-text)' }}>
                    {t(metric.metricKey)}
                  </span>
                  <span className="text-sm font-semibold" style={{ color: `var(--oneui-${metric.color})` }}>
                    {metric.value}%
                  </span>
                </div>
                <div className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-700"
                    style={{
                      width: `${metric.value}%`,
                      backgroundColor: `var(--oneui-${metric.color})`,
                    }}
                  ></div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
