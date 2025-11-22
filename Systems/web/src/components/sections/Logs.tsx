import { useEffect, useState } from 'react';
import { api, BotLog } from '../../api';
import { GlassCard } from '../ui/GlassCard';
import { AlertCircle, CheckCircle, Info, AlertTriangle } from 'lucide-react';

export const Logs = () => {
  const [logs, setLogs] = useState<BotLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>('all');

  useEffect(() => {
    loadLogs();
    // Set up polling for live updates
    const interval = setInterval(() => {
      loadLogs();
    }, 5000); // Update every 5 seconds
    
    return () => clearInterval(interval);
  }, [filter]);

  const loadLogs = async () => {
    try {
      const data = await api.streamLogs(100, filter === 'all' ? undefined : filter);
      setLogs(data || []);
    } catch (error) {
      console.error('Error loading logs:', error);
    } finally {
      setLoading(false);
    }
  };

  const getLogIcon = (level: string) => {
    switch (level) {
      case 'success':
        return CheckCircle;
      case 'error':
        return AlertCircle;
      case 'warning':
        return AlertTriangle;
      default:
        return Info;
    }
  };

  const getLogColor = (level: string) => {
    switch (level) {
      case 'success':
        return 'text-green-400 bg-green-500/10 border-green-500/30';
      case 'error':
        return 'text-red-400 bg-red-500/10 border-red-500/30';
      case 'warning':
        return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30';
      default:
        return 'text-blue-400 bg-blue-500/10 border-blue-500/30';
    }
  };

  const formatDate = (date: string) => {
    try {
      return new Date(date).toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
    } catch {
      return date;
    }
  };

  const filters = [
    { value: 'all', label: 'All Logs' },
    { value: 'info', label: 'Info' },
    { value: 'success', label: 'Success' },
    { value: 'warning', label: 'Warning' },
    { value: 'error', label: 'Error' },
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
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h2 className="text-3xl font-bold text-glass-text mb-2">System Logs</h2>
          <p className="text-glass-text-secondary">Real-time system activity and events</p>
        </div>
        <div className="flex gap-2">
          {filters.map((f) => (
            <button
              key={f.value}
              onClick={() => setFilter(f.value)}
              className={`
                px-4 py-2 rounded-lg text-sm font-medium transition-all
                ${filter === f.value
                  ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                  : 'bg-white/5 text-glass-text-secondary hover:bg-white/10'
                }
              `}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      <GlassCard className="p-6" glow>
        <div className="space-y-2">
          {logs.map((log, index) => {
            const Icon = getLogIcon(log.level);
            const colorClass = getLogColor(log.level);

            return (
              <div
                key={index}
                className="flex items-start gap-4 p-4 rounded-lg bg-white/5 hover:bg-white/10 transition-colors"
              >
                <div className={`p-2 rounded-lg ${colorClass}`}>
                  <Icon className="w-5 h-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <p className="text-glass-text font-medium">{log.message}</p>
                    <span className="text-xs text-glass-text-secondary whitespace-nowrap">
                      {formatDate(log.timestamp)}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`text-xs px-2 py-1 rounded-md capitalize ${colorClass}`}>
                      {log.level}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {logs.length === 0 && (
          <div className="text-center py-12">
            <Info className="w-16 h-16 mx-auto mb-4 text-glass-text-secondary" />
            <h3 className="text-xl font-bold text-glass-text mb-2">No logs found</h3>
            <p className="text-glass-text-secondary">
              {filter === 'all' ? 'No logs available' : `No ${filter} logs found`}
            </p>
          </div>
        )}
      </GlassCard>
    </div>
  );
};
