import { useState } from 'react';
import { GlassCard } from '../ui/GlassCard';
import { GlassButton } from '../ui/GlassButton';
import { Server, Play, Pause, RotateCw, AlertCircle } from 'lucide-react';

type ServiceStatus = 'running' | 'stopped' | 'restarting';

type Service = {
  id: string;
  name: string;
  description: string;
  status: ServiceStatus;
  uptime: string;
  memory: string;
};

export const Services = () => {
  const [services, setServices] = useState<Service[]>([
    {
      id: '1',
      name: 'Bot Core',
      description: 'Main bot process and event handler',
      status: 'running',
      uptime: '5d 12h 34m',
      memory: '245 MB',
    },
    {
      id: '2',
      name: 'Message Queue',
      description: 'Asynchronous message processing',
      status: 'running',
      uptime: '5d 12h 34m',
      memory: '128 MB',
    },
    {
      id: '3',
      name: 'Analytics Engine',
      description: 'Real-time data processing',
      status: 'running',
      uptime: '5d 12h 34m',
      memory: '312 MB',
    },
    {
      id: '4',
      name: 'Cache Service',
      description: 'Redis-based caching layer',
      status: 'stopped',
      uptime: '0m',
      memory: '0 MB',
    },
  ]);

  const handleServiceAction = (id: string, action: 'start' | 'stop' | 'restart') => {
    setServices(services.map(s => {
      if (s.id === id) {
        if (action === 'start') return { ...s, status: 'running' as ServiceStatus };
        if (action === 'stop') return { ...s, status: 'stopped' as ServiceStatus };
        if (action === 'restart') {
          setTimeout(() => {
            setServices(prev => prev.map(ps =>
              ps.id === id ? { ...ps, status: 'running' as ServiceStatus } : ps
            ));
          }, 2000);
          return { ...s, status: 'restarting' as ServiceStatus };
        }
      }
      return s;
    }));
  };

  const getStatusColor = (status: ServiceStatus) => {
    switch (status) {
      case 'running':
        return 'text-green-400 bg-green-500/10 border-green-500/30';
      case 'stopped':
        return 'text-red-400 bg-red-500/10 border-red-500/30';
      case 'restarting':
        return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30';
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-glass-text mb-2">Service Management</h2>
        <p className="text-glass-text-secondary">Control and monitor bot services</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[
          { label: 'Total Services', value: services.length, color: 'text-cyan-400' },
          { label: 'Running', value: services.filter(s => s.status === 'running').length, color: 'text-green-400' },
          { label: 'Stopped', value: services.filter(s => s.status === 'stopped').length, color: 'text-red-400' },
          { label: 'Health', value: '98%', color: 'text-purple-400' },
        ].map((stat) => (
          <GlassCard key={stat.label} hover className="p-6">
            <p className="text-glass-text-secondary text-sm mb-1">{stat.label}</p>
            <p className={`text-2xl font-bold ${stat.color}`}>{stat.value}</p>
          </GlassCard>
        ))}
      </div>

      <div className="space-y-4">
        {services.map((service) => (
          <GlassCard key={service.id} className="p-6" glow>
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-start gap-4 flex-1">
                <div className="p-3 rounded-xl bg-cyan-500/20">
                  <Server className="w-6 h-6 text-cyan-400" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="text-xl font-bold text-glass-text">{service.name}</h3>
                    <span className={`px-3 py-1 rounded-full text-xs font-semibold capitalize ${getStatusColor(service.status)}`}>
                      {service.status}
                    </span>
                  </div>
                  <p className="text-glass-text-secondary mb-3">{service.description}</p>
                  <div className="flex gap-4 text-sm">
                    <div>
                      <span className="text-glass-text-secondary">Uptime: </span>
                      <span className="text-glass-text font-medium">{service.uptime}</span>
                    </div>
                    <div>
                      <span className="text-glass-text-secondary">Memory: </span>
                      <span className="text-glass-text font-medium">{service.memory}</span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="flex gap-2">
                {service.status === 'stopped' ? (
                  <GlassButton
                    size="sm"
                    variant="primary"
                    onClick={() => handleServiceAction(service.id, 'start')}
                  >
                    <Play className="w-4 h-4" />
                  </GlassButton>
                ) : (
                  <GlassButton
                    size="sm"
                    variant="danger"
                    onClick={() => handleServiceAction(service.id, 'stop')}
                    disabled={service.status === 'restarting'}
                  >
                    <Pause className="w-4 h-4" />
                  </GlassButton>
                )}
                <GlassButton
                  size="sm"
                  variant="secondary"
                  onClick={() => handleServiceAction(service.id, 'restart')}
                  disabled={service.status === 'stopped' || service.status === 'restarting'}
                >
                  <RotateCw className={`w-4 h-4 ${service.status === 'restarting' ? 'animate-spin' : ''}`} />
                </GlassButton>
              </div>
            </div>
          </GlassCard>
        ))}
      </div>

      <GlassCard className="p-6 bg-orange-500/5 border-orange-500/20">
        <div className="flex items-start gap-3">
          <AlertCircle className="w-6 h-6 text-orange-400 flex-shrink-0 mt-1" />
          <div>
            <h3 className="text-lg font-bold text-orange-400 mb-2">Warning</h3>
            <p className="text-glass-text-secondary">
              Stopping critical services may affect bot functionality. Always ensure proper backups
              before making changes to production services.
            </p>
          </div>
        </div>
      </GlassCard>
    </div>
  );
};
