import { useEffect, useState } from 'react';
import { api, BotStats } from '../../api';
import { useI18n } from '../../contexts/I18nContext';
import { Users, UserPlus, Activity, TrendingUp } from 'lucide-react';

export const UserStatsWidget = () => {
  const { t } = useI18n();
  const [stats, setStats] = useState<BotStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStats();
    const interval = setInterval(loadStats, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadStats = async () => {
    try {
      const data = await api.getStats();
      setStats(data);
    } catch (error) {
      console.error('Error loading stats:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading || !stats) {
    return <div className="text-center py-4 oneui-text-muted">Loading...</div>;
  }

  const statsItems = [
    {
      icon: Users,
      label: t('home.userStats.totalUsers') || 'Total Users',
      value: stats.total_users || 0,
      color: 'primary',
    },
    {
      icon: UserPlus,
      label: t('home.userStats.newToday') || 'New Today',
      value: 0, // Would need API endpoint for this
      color: 'success',
    },
    {
      icon: Activity,
      label: t('home.userStats.active24h') || 'Active (24h)',
      value: 0, // Would need API endpoint for this
      color: 'info',
    },
    {
      icon: TrendingUp,
      label: t('home.userStats.growth') || 'Growth',
      value: '+5.2%',
      color: 'success',
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-4">
      {statsItems.map((item, index) => {
        const Icon = item.icon;
        return (
          <div
            key={index}
            className="p-4 rounded-lg"
            style={{ backgroundColor: 'var(--oneui-bg-alt)' }}
          >
            <div className="flex items-center gap-2 mb-2">
              <Icon className="w-4 h-4" style={{ color: `var(--oneui-${item.color})` }} />
              <span className="text-xs oneui-text-muted">{item.label}</span>
            </div>
            <p className="text-2xl font-bold" style={{ color: 'var(--oneui-text)' }}>
              {item.value}
            </p>
          </div>
        );
      })}
    </div>
  );
};

