import { useEffect, useState } from 'react';
import { api, BotLog } from '../../api';
import { useI18n } from '../../contexts/I18nContext';
import { AlertCircle, XCircle, AlertTriangle, Info } from 'lucide-react';

export const RecentErrorsWidget = () => {
  const { t } = useI18n();
  const [errors, setErrors] = useState<BotLog[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadErrors();
    const interval = setInterval(loadErrors, 10000);
    return () => clearInterval(interval);
  }, []);

  const loadErrors = async () => {
    try {
      const logs = await api.getLogs(5, 'error');
      setErrors(logs || []);
    } catch (error) {
      console.error('Error loading errors:', error);
    } finally {
      setLoading(false);
    }
  };

  const getIcon = (level: string) => {
    switch (level) {
      case 'error':
        return XCircle;
      case 'warning':
        return AlertTriangle;
      default:
        return Info;
    }
  };

  const getColor = (level: string) => {
    switch (level) {
      case 'error':
        return 'text-red-500';
      case 'warning':
        return 'text-yellow-500';
      default:
        return 'text-blue-500';
    }
  };

  if (loading) {
    return <div className="text-center py-4 oneui-text-muted">Loading...</div>;
  }

  if (errors.length === 0) {
    return (
      <div className="text-center py-8">
        <AlertCircle className="w-12 h-12 mx-auto mb-2 oneui-text-muted" />
        <p className="text-sm oneui-text-muted">{t('home.noErrors') || 'No recent errors'}</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {errors.map((error, index) => {
        const Icon = getIcon(error.level);
        return (
          <div
            key={index}
            className="flex items-start gap-3 p-3 rounded-lg"
            style={{ backgroundColor: 'var(--oneui-bg-alt)' }}
          >
            <Icon className={`w-5 h-5 flex-shrink-0 ${getColor(error.level)}`} />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate" style={{ color: 'var(--oneui-text)' }}>
                {error.message}
              </p>
              <p className="text-xs oneui-text-muted mt-1">
                {new Date(error.timestamp).toLocaleString()}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
};

