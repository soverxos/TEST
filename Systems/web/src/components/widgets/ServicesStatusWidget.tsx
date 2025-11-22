import { useEffect, useState } from 'react';
import { api, Service } from '../../api';
import { useI18n } from '../../contexts/I18nContext';
import { CheckCircle2, XCircle, Loader2 } from 'lucide-react';

export const ServicesStatusWidget = () => {
  const { t } = useI18n();
  const [services, setServices] = useState<Service[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadServices();
    const interval = setInterval(loadServices, 15000);
    return () => clearInterval(interval);
  }, []);

  const loadServices = async () => {
    try {
      const data = await api.getServices();
      setServices(data || []);
    } catch (error) {
      console.error('Error loading services:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="text-center py-4 oneui-text-muted">Loading...</div>;
  }

  if (services.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-sm oneui-text-muted">{t('home.noServices') || 'No services available'}</p>
      </div>
    );
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running':
        return CheckCircle2;
      case 'stopped':
        return XCircle;
      case 'restarting':
        return Loader2;
      default:
        return XCircle;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running':
        return 'text-green-500';
      case 'stopped':
        return 'text-red-500';
      case 'restarting':
        return 'text-yellow-500';
      default:
        return 'text-gray-500';
    }
  };

  return (
    <div className="space-y-3">
      {services.slice(0, 5).map((service) => {
        const StatusIcon = getStatusIcon(service.status);
        return (
          <div
            key={service.id}
            className="flex items-center justify-between p-3 rounded-lg"
            style={{ backgroundColor: 'var(--oneui-bg-alt)' }}
          >
            <div className="flex items-center gap-3 flex-1 min-w-0">
              <StatusIcon className={`w-5 h-5 flex-shrink-0 ${getStatusColor(service.status)}`} />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate" style={{ color: 'var(--oneui-text)' }}>
                  {service.name}
                </p>
                {service.description && (
                  <p className="text-xs oneui-text-muted truncate">{service.description}</p>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              <span className={`text-xs px-2 py-1 rounded ${
                service.status === 'running'
                  ? 'bg-green-500/20 text-green-500'
                  : service.status === 'restarting'
                  ? 'bg-yellow-500/20 text-yellow-500'
                  : 'bg-red-500/20 text-red-500'
              }`}>
                {service.status}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
};

