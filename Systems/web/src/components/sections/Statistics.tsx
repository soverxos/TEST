import { useEffect, useState } from 'react';
import { api } from '../../lib/api';
import { GlassCard } from '../ui/GlassCard';
import { TrendingUp, TrendingDown, Activity } from 'lucide-react';

type StatData = {
  name: string;
  value: number;
  change: number;
};

export const Statistics = () => {
  const [stats, setStats] = useState<StatData[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStatistics();
  }, []);

  const loadStatistics = async () => {
    try {
      // Get stats from API
      const botStats = await api.getStats();
      
      // Transform to display format
      const statsData: StatData[] = [
        {
          name: 'Messages Today',
          value: botStats.messages_today || 0,
          change: 5.2, // Mock change
        },
        {
          name: 'Total Users',
          value: botStats.total_users || 0,
          change: 2.1,
        },
        {
          name: 'Active Modules',
          value: botStats.active_modules || 0,
          change: 0,
        },
        {
          name: 'Total Modules',
          value: botStats.total_modules || 0,
          change: 0,
        },
      ];
      
      setStats(statsData);
    } catch (error) {
      console.error('Error loading statistics:', error);
    } finally {
      setLoading(false);
    }
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
      <div>
        <h2 className="text-3xl font-bold text-glass-text mb-2">Statistics</h2>
        <p className="text-glass-text-secondary">Real-time analytics and metrics</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {stats.map((stat) => {
          const isPositive = stat.change >= 0;
          return (
            <GlassCard key={stat.name} hover glow className="p-6">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <p className="text-glass-text-secondary text-sm mb-1">
                    {stat.name}
                  </p>
                  <p className="text-3xl font-bold text-glass-text">
                    {stat.value.toLocaleString()}
                  </p>
                </div>
                <Activity className="w-6 h-6 text-cyan-400" />
              </div>
              {stat.change !== 0 && (
                <div className="flex items-center gap-2">
                  {isPositive ? (
                    <TrendingUp className="w-4 h-4 text-green-400" />
                  ) : (
                    <TrendingDown className="w-4 h-4 text-red-400" />
                  )}
                  <span
                    className={`text-sm font-semibold ${
                      isPositive ? 'text-green-400' : 'text-red-400'
                    }`}
                  >
                    {isPositive ? '+' : ''}{stat.change.toFixed(1)}%
                  </span>
                  <span className="text-xs text-glass-text-secondary">vs previous</span>
                </div>
              )}
            </GlassCard>
          );
        })}
      </div>

      <GlassCard className="p-6" glow>
        <h3 className="text-xl font-bold text-glass-text mb-4">Activity Chart</h3>
        <div className="h-64 flex items-end gap-2">
          {Array.from({ length: 24 }).map((_, i) => {
            const height = Math.random() * 100;
            return (
              <div
                key={i}
                className="flex-1 bg-gradient-to-t from-cyan-500 to-purple-500 rounded-t-lg transition-all hover:opacity-80 cursor-pointer"
                style={{ height: `${height}%`, minHeight: '4px' }}
                title={`Hour ${i}: ${Math.floor(height)}%`}
              />
            );
          })}
        </div>
        <div className="flex justify-between mt-4 text-xs text-glass-text-secondary">
          <span>00:00</span>
          <span>06:00</span>
          <span>12:00</span>
          <span>18:00</span>
          <span>24:00</span>
        </div>
      </GlassCard>
    </div>
  );
};
