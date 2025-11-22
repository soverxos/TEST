import { useState, useEffect } from 'react';
import { api, Service } from '../../api';
import { Server, Play, Pause, RotateCw, AlertCircle } from 'lucide-react';

export const Services = () => {
  const [services, setServices] = useState<Service[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadServices();
    const interval = setInterval(loadServices, 10000); // Refresh every 10 seconds
    return () => clearInterval(interval);
  }, []);

  const loadServices = async () => {
    try {
      const data = await api.getServices();
      setServices(data);
    } catch (error) {
      console.error('Error loading services:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleServiceAction = async (id: string, action: 'start' | 'stop' | 'restart') => {
    try {
      await api.serviceAction(id, action);
      // Reload services to get updated status
      await loadServices();
    } catch (error: any) {
      console.error('Error performing service action:', error);
      alert(`Failed to ${action} service: ${error.message || error}`);
    }
  };

  const runningCount = services.filter(s => s.status === 'running').length;
  const stoppedCount = services.filter(s => s.status === 'stopped').length;

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
          Service Management
        </h1>
        <p className="oneui-text-muted">Control and monitor bot services</p>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
        {[
          { label: 'Total Services', value: services.length, color: 'oneui-text-primary' },
          { label: 'Running', value: runningCount, color: 'oneui-text-success' },
          { label: 'Stopped', value: stoppedCount, color: 'oneui-text-danger' },
          { label: 'Health', value: '98%', color: 'oneui-text-primary' },
        ].map((stat) => (
          <div key={stat.label} className="oneui-card">
            <p className="text-sm oneui-text-muted mb-1">{stat.label}</p>
            <p className={`text-2xl font-bold ${stat.color}`}>{stat.value}</p>
          </div>
        ))}
      </div>

      {/* Services List */}
      <div className="space-y-4">
        {services.map((service) => (
          <div key={service.id} className="oneui-card">
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-start gap-4 flex-1">
                <div className="oneui-stat-icon oneui-stat-icon-primary">
                  <Server className="w-6 h-6" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="text-lg font-bold" style={{ color: 'var(--oneui-text)' }}>
                      {service.name}
                    </h3>
                    <span className={`oneui-badge ${
                      service.status === 'running' ? 'oneui-badge-success' :
                      service.status === 'stopped' ? 'oneui-badge-danger' :
                      'oneui-badge-warning'
                    }`}>
                      {service.status}
                    </span>
                  </div>
                  <p className="oneui-text-muted text-sm mb-3">{service.description}</p>
                  <div className="flex gap-6 text-sm">
                    <div>
                      <span className="oneui-text-muted">Uptime: </span>
                      <span className="font-medium" style={{ color: 'var(--oneui-text)' }}>
                        {service.uptime}
                      </span>
                    </div>
                    <div>
                      <span className="oneui-text-muted">Memory: </span>
                      <span className="font-medium" style={{ color: 'var(--oneui-text)' }}>
                        {service.memory}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="flex gap-2">
                {service.status === 'stopped' ? (
                  <button
                    onClick={() => handleServiceAction(service.id, 'start')}
                    className="oneui-btn oneui-btn-primary"
                    style={{ padding: '0.5rem' }}
                  >
                    <Play className="w-4 h-4" />
                  </button>
                ) : (
                  <button
                    onClick={() => handleServiceAction(service.id, 'stop')}
                    className="oneui-btn oneui-btn-secondary"
                    style={{ padding: '0.5rem' }}
                    disabled={service.status === 'restarting'}
                  >
                    <Pause className="w-4 h-4" />
                  </button>
                )}
                <button
                  onClick={() => handleServiceAction(service.id, 'restart')}
                  className="oneui-btn oneui-btn-secondary"
                  style={{ padding: '0.5rem' }}
                  disabled={service.status === 'stopped' || service.status === 'restarting'}
                >
                  <RotateCw className={`w-4 h-4 ${service.status === 'restarting' ? 'animate-spin' : ''}`} />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Warning */}
      <div className="oneui-card mt-6 border-l-4" style={{ borderLeftColor: 'var(--oneui-warning)' }}>
        <div className="flex items-start gap-3">
          <AlertCircle className="w-6 h-6 text-orange-500 flex-shrink-0 mt-1" />
          <div>
            <h3 className="text-lg font-bold mb-2" style={{ color: 'var(--oneui-warning)' }}>
              Warning
            </h3>
            <p className="oneui-text-muted">
              Stopping critical services may affect bot functionality. Always ensure proper backups
              before making changes to production services.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
