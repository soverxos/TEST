import { useEffect, useState } from 'react';
import { api, BotStats } from '../../lib/api';
import { GlassCard } from '../ui/GlassCard';
import { Activity, Users, Zap, TrendingUp } from 'lucide-react';

type Stats = {
  activeModules: number;
  totalUsers: number;
  todayInteractions: number;
  systemStatus: 'online' | 'degraded' | 'offline';
};

export const Home = () => {
  const [stats, setStats] = useState<Stats>({
    activeModules: 0,
    totalUsers: 0,
    todayInteractions: 0,
    systemStatus: 'online',
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStats();
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
      label: 'Active Modules',
      value: stats.activeModules,
      icon: Zap,
      color: 'from-cyan-400 to-blue-500',
      bgColor: 'bg-cyan-500/10',
    },
    {
      label: 'Total Users',
      value: stats.totalUsers,
      icon: Users,
      color: 'from-purple-400 to-pink-500',
      bgColor: 'bg-purple-500/10',
    },
    {
      label: 'Today Interactions',
      value: stats.todayInteractions,
      icon: TrendingUp,
      color: 'from-green-400 to-emerald-500',
      bgColor: 'bg-green-500/10',
    },
    {
      label: 'System Status',
      value: stats.systemStatus.toUpperCase(),
      icon: Activity,
      color: 'from-orange-400 to-red-500',
      bgColor: 'bg-orange-500/10',
    },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="loading-spinner"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-glass-text mb-2">Welcome to SwiftDevBot</h2>
        <p className="text-glass-text-secondary">Monitor and control your bot's operations</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((card) => {
          const Icon = card.icon;
          return (
            <GlassCard key={card.label} hover glow className="p-6">
              <div className="flex items-start justify-between mb-4">
                <div className={`p-3 rounded-xl ${card.bgColor}`}>
                  <Icon className={`w-6 h-6 bg-gradient-to-r ${card.color} bg-clip-text text-transparent`} />
                </div>
              </div>
              <div>
                <p className="text-glass-text-secondary text-sm mb-1">{card.label}</p>
                <p className="text-2xl font-bold text-glass-text">{card.value}</p>
              </div>
            </GlassCard>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <GlassCard className="p-6" glow>
          <h3 className="text-xl font-bold text-glass-text mb-4">Recent Activity</h3>
          <div className="space-y-3">
            {[
              { action: 'Module activated', module: 'AI Chat', time: '2 minutes ago' },
              { action: 'User registered', module: 'System', time: '15 minutes ago' },
              { action: 'Code review completed', module: 'Code Review', time: '1 hour ago' },
              { action: 'Analytics updated', module: 'Analytics', time: '2 hours ago' },
            ].map((activity, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-3 rounded-lg bg-white/5 hover:bg-white/10 transition-colors"
              >
                <div>
                  <p className="text-glass-text font-medium">{activity.action}</p>
                  <p className="text-glass-text-secondary text-sm">{activity.module}</p>
                </div>
                <span className="text-xs text-glass-text-secondary">{activity.time}</span>
              </div>
            ))}
          </div>
        </GlassCard>

        <GlassCard className="p-6" glow>
          <h3 className="text-xl font-bold text-glass-text mb-4">System Health</h3>
          <div className="space-y-4">
            {[
              { metric: 'CPU Usage', value: 45, color: 'bg-cyan-500' },
              { metric: 'Memory', value: 62, color: 'bg-purple-500' },
              { metric: 'Network', value: 28, color: 'bg-green-500' },
              { metric: 'Storage', value: 71, color: 'bg-orange-500' },
            ].map((metric) => (
              <div key={metric.metric}>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-glass-text">{metric.metric}</span>
                  <span className="text-sm font-semibold text-glass-text">{metric.value}%</span>
                </div>
                <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${metric.color} rounded-full transition-all duration-500`}
                    style={{ width: `${metric.value}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </GlassCard>
      </div>
    </div>
  );
};
