import { GlassCard } from '../ui/GlassCard';
import { Activity, Cpu, HardDrive, Wifi, Zap } from 'lucide-react';

export const Monitoring = () => {
  const metrics = [
    { label: 'CPU Usage', value: 45, icon: Cpu, color: 'from-cyan-400 to-blue-500' },
    { label: 'Memory', value: 62, icon: Activity, color: 'from-purple-400 to-pink-500' },
    { label: 'Disk I/O', value: 28, icon: HardDrive, color: 'from-green-400 to-emerald-500' },
    { label: 'Network', value: 71, icon: Wifi, color: 'from-orange-400 to-red-500' },
  ];

  const requests = Array.from({ length: 50 }, () => Math.random() * 100);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-glass-text mb-2">System Monitoring</h2>
        <p className="text-glass-text-secondary">Real-time performance metrics and health status</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {metrics.map((metric) => {
          const Icon = metric.icon;
          return (
            <GlassCard key={metric.label} hover glow className="p-6">
              <div className="flex items-start justify-between mb-4">
                <div className={`p-3 rounded-xl bg-gradient-to-br ${metric.color} bg-opacity-20`}>
                  <Icon className="w-6 h-6 text-white" />
                </div>
                <span className="text-2xl font-bold text-glass-text">{metric.value}%</span>
              </div>
              <p className="text-glass-text-secondary text-sm mb-2">{metric.label}</p>
              <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                <div
                  className={`h-full bg-gradient-to-r ${metric.color} rounded-full transition-all duration-500`}
                  style={{ width: `${metric.value}%` }}
                />
              </div>
            </GlassCard>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <GlassCard className="p-6" glow>
          <h3 className="text-xl font-bold text-glass-text mb-4">Request Rate</h3>
          <div className="h-48 flex items-end gap-1">
            {requests.map((height, i) => (
              <div
                key={i}
                className="flex-1 bg-gradient-to-t from-cyan-500 to-purple-500 rounded-t transition-all hover:opacity-80"
                style={{ height: `${height}%`, minHeight: '2px' }}
              />
            ))}
          </div>
          <div className="flex justify-between mt-4 text-xs text-glass-text-secondary">
            <span>0s</span>
            <span>25s</span>
            <span>50s</span>
          </div>
        </GlassCard>

        <GlassCard className="p-6" glow>
          <h3 className="text-xl font-bold text-glass-text mb-4">Response Times</h3>
          <div className="space-y-4">
            {[
              { endpoint: '/api/messages', time: 45, color: 'bg-green-500' },
              { endpoint: '/api/users', time: 67, color: 'bg-yellow-500' },
              { endpoint: '/api/modules', time: 32, color: 'bg-green-500' },
              { endpoint: '/api/stats', time: 89, color: 'bg-orange-500' },
            ].map((endpoint) => (
              <div key={endpoint.endpoint}>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-glass-text font-mono">{endpoint.endpoint}</span>
                  <span className="text-sm font-semibold text-glass-text">{endpoint.time}ms</span>
                </div>
                <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${endpoint.color} rounded-full transition-all duration-500`}
                    style={{ width: `${endpoint.time}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </GlassCard>
      </div>

      <GlassCard className="p-6" glow>
        <h3 className="text-xl font-bold text-glass-text mb-6">Active Connections</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[
            { label: 'WebSocket Connections', value: 127, icon: Zap, change: '+12' },
            { label: 'Database Connections', value: 34, icon: HardDrive, change: '+3' },
            { label: 'API Requests/min', value: 1453, icon: Activity, change: '+89' },
          ].map((stat) => {
            const Icon = stat.icon;
            return (
              <div key={stat.label} className="flex items-center gap-4">
                <div className="p-3 rounded-xl bg-cyan-500/20">
                  <Icon className="w-6 h-6 text-cyan-400" />
                </div>
                <div>
                  <p className="text-glass-text-secondary text-sm">{stat.label}</p>
                  <div className="flex items-baseline gap-2">
                    <p className="text-2xl font-bold text-glass-text">{stat.value}</p>
                    <span className="text-sm text-green-400 font-semibold">{stat.change}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </GlassCard>
    </div>
  );
};
