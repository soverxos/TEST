import { useEffect, useState } from 'react';
import { api, LiveMetricsData } from '../../api';
import { useI18n } from '../../contexts/I18nContext';
import { Zap, Clock, AlertTriangle, TrendingUp } from 'lucide-react';

export const PerformanceWidget = () => {
  const { t } = useI18n();
  const [metrics, setMetrics] = useState<LiveMetricsData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadMetrics();
    const interval = setInterval(loadMetrics, 5000);
    return () => clearInterval(interval);
  }, []);

  const loadMetrics = async () => {
    try {
      const data = await api.getLiveMetrics();
      setMetrics(data);
    } catch (error) {
      console.error('Error loading metrics:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading || !metrics) {
    return <div className="text-center py-4 oneui-text-muted">Loading...</div>;
  }

  const performanceItems = [
    {
      icon: Zap,
      label: t('home.performance.rps') || 'RPS',
      value: metrics.rps.toFixed(1),
      color: 'primary',
    },
    {
      icon: Clock,
      label: t('home.performance.responseTime') || 'Response Time',
      value: `${metrics.responseTime.toFixed(0)}ms`,
      color: metrics.responseTime > 100 ? 'warning' : 'success',
    },
    {
      icon: AlertTriangle,
      label: t('home.performance.errorRate') || 'Error Rate',
      value: `${metrics.errorRate.toFixed(1)}%`,
      color: metrics.errorRate > 3 ? 'danger' : metrics.errorRate > 1 ? 'warning' : 'success',
    },
    {
      icon: TrendingUp,
      label: t('home.performance.queueSize') || 'Queue Size',
      value: metrics.queueSize.toString(),
      color: metrics.queueSize > 100 ? 'warning' : 'info',
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-4">
      {performanceItems.map((item, index) => {
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
            <p className="text-2xl font-bold" style={{ color: `var(--oneui-${item.color})` }}>
              {item.value}
            </p>
          </div>
        );
      })}
    </div>
  );
};

