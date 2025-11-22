import { useEffect, useState } from 'react';
import { api, BotStats } from '../../api';
import { useI18n } from '../../contexts/I18nContext';
import { Clock, Server, Activity } from 'lucide-react';

export const UptimeWidget = () => {
  const { t } = useI18n();
  const [stats, setStats] = useState<BotStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStats();
    const interval = setInterval(loadStats, 60000);
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

  const parseUptime = (uptime: string) => {
    // Parse "5d 12h 34m" format
    const parts = uptime.split(' ');
    let days = 0, hours = 0, minutes = 0;
    
    parts.forEach(part => {
      if (part.endsWith('d')) days = parseInt(part) || 0;
      else if (part.endsWith('h')) hours = parseInt(part) || 0;
      else if (part.endsWith('m')) minutes = parseInt(part) || 0;
    });

    return { days, hours, minutes, formatted: uptime };
  };

  const uptime = parseUptime(stats.uptime || '0m');

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-center">
        <div className="relative w-32 h-32">
          <svg className="transform -rotate-90 w-32 h-32">
            <circle
              cx="64"
              cy="64"
              r="56"
              stroke="var(--oneui-border)"
              strokeWidth="8"
              fill="none"
            />
            <circle
              cx="64"
              cy="64"
              r="56"
              stroke="var(--oneui-success)"
              strokeWidth="8"
              fill="none"
              strokeDasharray={`${2 * Math.PI * 56}`}
              strokeDashoffset={`${2 * Math.PI * 56 * (1 - Math.min(uptime.days / 365, 1))}`}
              strokeLinecap="round"
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <Clock className="w-8 h-8 mb-1" style={{ color: 'var(--oneui-success)' }} />
            <span className="text-xs oneui-text-muted">{uptime.formatted}</span>
          </div>
        </div>
      </div>
      <div className="grid grid-cols-3 gap-2 text-center">
        <div>
          <p className="text-2xl font-bold" style={{ color: 'var(--oneui-text)' }}>
            {uptime.days}
          </p>
          <p className="text-xs oneui-text-muted">{t('home.uptime.days') || 'Days'}</p>
        </div>
        <div>
          <p className="text-2xl font-bold" style={{ color: 'var(--oneui-text)' }}>
            {uptime.hours}
          </p>
          <p className="text-xs oneui-text-muted">{t('home.uptime.hours') || 'Hours'}</p>
        </div>
        <div>
          <p className="text-2xl font-bold" style={{ color: 'var(--oneui-text)' }}>
            {uptime.minutes}
          </p>
          <p className="text-xs oneui-text-muted">{t('home.uptime.minutes') || 'Minutes'}</p>
        </div>
      </div>
    </div>
  );
};

