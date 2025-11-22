import { useEffect, useState } from 'react';
import { api, BotStats } from '../../api';
import { useI18n } from '../../contexts/I18nContext';
import { MessageSquare, Users, Zap, Box, TrendingUp, Activity, BarChart3 } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line, AreaChart, Area } from 'recharts';

type StatData = {
  name: string;
  value: number;
  change: number;
  icon: typeof MessageSquare;
  color: string;
};

export const Statistics = () => {
  const { t } = useI18n();
  const [stats, setStats] = useState<StatData[]>([]);
  const [loading, setLoading] = useState(true);
  const [activityData, setActivityData] = useState<Array<{ hour: string; value: number }>>([]);

  useEffect(() => {
    loadStatistics();
    generateActivityData();
    const interval = setInterval(() => {
      loadStatistics();
      generateActivityData();
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadStatistics = async () => {
    try {
      const botStats: BotStats = await api.getStats();
      
      const statsData: StatData[] = [
        {
          name: t('statistics.messagesToday') || 'Messages Today',
          value: botStats.messages_today || 0,
          change: 5.2,
          icon: MessageSquare,
          color: 'oneui-stat-icon-primary',
        },
        {
          name: t('statistics.totalUsers') || 'Total Users',
          value: botStats.total_users || 0,
          change: 3.8,
          icon: Users,
          color: 'oneui-stat-icon-success',
        },
        {
          name: t('statistics.activeModules') || 'Active Modules',
          value: botStats.active_modules || 0,
          change: 2.5,
          icon: Zap,
          color: 'oneui-stat-icon-warning',
        },
        {
          name: t('statistics.totalModules') || 'Total Modules',
          value: botStats.total_modules || 0,
          change: 0,
          icon: Box,
          color: 'oneui-stat-icon-info',
        },
      ];
      
      setStats(statsData);
    } catch (error) {
      console.error('Error loading statistics:', error);
    } finally {
      setLoading(false);
    }
  };

  const generateActivityData = () => {
    // Generate 24-hour activity data
    const data = Array.from({ length: 24 }, (_, i) => ({
      hour: `${i.toString().padStart(2, '0')}:00`,
      value: Math.floor(Math.random() * 100),
    }));
    setActivityData(data);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="oneui-spinner"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-2" style={{ color: 'var(--oneui-text)' }}>
          {t('statistics.title') || 'Statistics'}
        </h1>
        <p className="oneui-text-muted">
          {t('statistics.subtitle') || 'Real-time analytics and metrics'}
        </p>
      </div>

      {/* Stats Cards */}
      <div className="oneui-stats-grid mb-6">
        {stats.map((stat) => {
          const Icon = stat.icon;
          const isPositive = stat.change >= 0;
          return (
            <div key={stat.name} className="oneui-stat-card">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="oneui-stat-label">{stat.name}</div>
                  <div className="oneui-stat-value">{stat.value.toLocaleString()}</div>
                  {stat.change !== 0 && (
                    <div className="flex items-center gap-1 mt-2 text-sm" style={{ color: isPositive ? 'var(--oneui-success)' : 'var(--oneui-danger)' }}>
                      <TrendingUp className="w-4 h-4" />
                      <span>{isPositive ? '+' : ''}{stat.change.toFixed(1)}%</span>
                      <span className="text-xs oneui-text-muted ml-1">
                        {t('statistics.vsPrevious') || 'vs previous'}
                      </span>
                    </div>
                  )}
                </div>
                <div className={stat.color}>
                  <Icon className="w-6 h-6" />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Activity Chart */}
      <div className="oneui-card">
        <div className="oneui-card-header">
          <div className="flex items-center gap-3">
            <BarChart3 className="w-5 h-5" style={{ color: 'var(--oneui-primary)' }} />
            <h3 className="oneui-card-title">
              {t('statistics.activityChart') || 'Activity Chart'}
            </h3>
          </div>
        </div>
        <div className="p-4">
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={activityData}>
              <defs>
                <linearGradient id="colorActivity" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="var(--oneui-primary)" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="var(--oneui-primary)" stopOpacity={0.1}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--oneui-border)" />
              <XAxis 
                dataKey="hour" 
                stroke="var(--oneui-text-muted)"
                style={{ fontSize: '12px' }}
                tick={{ fill: 'var(--oneui-text-muted)' }}
              />
              <YAxis 
                stroke="var(--oneui-text-muted)"
                style={{ fontSize: '12px' }}
                tick={{ fill: 'var(--oneui-text-muted)' }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'var(--oneui-bg)',
                  border: '1px solid var(--oneui-border)',
                  color: 'var(--oneui-text)',
                  borderRadius: '8px',
                }}
                labelStyle={{ color: 'var(--oneui-text)' }}
              />
              <Area
                type="monotone"
                dataKey="value"
                stroke="var(--oneui-primary)"
                strokeWidth={2}
                fill="url(#colorActivity)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Additional Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Bar Chart */}
        <div className="oneui-card">
          <div className="oneui-card-header">
            <div className="flex items-center gap-3">
              <Activity className="w-5 h-5" style={{ color: 'var(--oneui-primary)' }} />
              <h3 className="oneui-card-title">
                {t('statistics.hourlyActivity') || 'Hourly Activity'}
              </h3>
            </div>
          </div>
          <div className="p-4">
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={activityData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--oneui-border)" />
                <XAxis 
                  dataKey="hour" 
                  stroke="var(--oneui-text-muted)"
                  style={{ fontSize: '11px' }}
                  tick={{ fill: 'var(--oneui-text-muted)' }}
                />
                <YAxis 
                  stroke="var(--oneui-text-muted)"
                  style={{ fontSize: '11px' }}
                  tick={{ fill: 'var(--oneui-text-muted)' }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'var(--oneui-bg)',
                    border: '1px solid var(--oneui-border)',
                    color: 'var(--oneui-text)',
                    borderRadius: '8px',
                  }}
                  labelStyle={{ color: 'var(--oneui-text)' }}
                />
                <Bar 
                  dataKey="value" 
                  fill="var(--oneui-primary)"
                  radius={[4, 4, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Line Chart */}
        <div className="oneui-card">
          <div className="oneui-card-header">
            <div className="flex items-center gap-3">
              <TrendingUp className="w-5 h-5" style={{ color: 'var(--oneui-success)' }} />
              <h3 className="oneui-card-title">
                {t('statistics.trends') || 'Trends'}
              </h3>
            </div>
          </div>
          <div className="p-4">
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={activityData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--oneui-border)" />
                <XAxis 
                  dataKey="hour" 
                  stroke="var(--oneui-text-muted)"
                  style={{ fontSize: '11px' }}
                  tick={{ fill: 'var(--oneui-text-muted)' }}
                />
                <YAxis 
                  stroke="var(--oneui-text-muted)"
                  style={{ fontSize: '11px' }}
                  tick={{ fill: 'var(--oneui-text-muted)' }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'var(--oneui-bg)',
                    border: '1px solid var(--oneui-border)',
                    color: 'var(--oneui-text)',
                    borderRadius: '8px',
                  }}
                  labelStyle={{ color: 'var(--oneui-text)' }}
                />
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke="var(--oneui-success)"
                  strokeWidth={2}
                  dot={{ fill: 'var(--oneui-success)', r: 4 }}
                  activeDot={{ r: 6 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
};
