import { Activity, Cpu, HardDrive, Wifi } from 'lucide-react';

export const Monitoring = () => {
  const metrics = [
    { label: 'CPU Usage', value: 45, icon: Cpu, color: 'oneui-stat-icon-primary' },
    { label: 'Memory', value: 62, icon: Activity, color: 'oneui-stat-icon-success' },
    { label: 'Disk I/O', value: 28, icon: HardDrive, color: 'oneui-stat-icon-warning' },
    { label: 'Network', value: 71, icon: Wifi, color: 'oneui-stat-icon-danger' },
  ];

  const requests = Array.from({ length: 50 }, () => Math.random() * 100);

  return (
    <div>
      {/* Page Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-2" style={{ color: 'var(--oneui-text)' }}>
          System Monitoring
        </h1>
        <p className="oneui-text-muted">Real-time performance metrics and health status</p>
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
        {metrics.map((metric) => {
          const Icon = metric.icon;
          return (
            <div key={metric.label} className="oneui-card">
              <div className="flex items-start justify-between mb-4">
                <div className={`oneui-stat-icon ${metric.color}`}>
                  <Icon className="w-6 h-6" />
                </div>
                <span className="text-2xl font-bold" style={{ color: 'var(--oneui-text)' }}>
                  {metric.value}%
                </span>
              </div>
              <p className="text-sm oneui-text-muted mb-3">{metric.label}</p>
              <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${metric.value}%`,
                    backgroundColor: metric.color.includes('primary') ? 'var(--oneui-primary)' :
                                    metric.color.includes('success') ? 'var(--oneui-success)' :
                                    metric.color.includes('warning') ? 'var(--oneui-warning)' :
                                    'var(--oneui-danger)',
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Request Rate */}
        <div className="oneui-card">
          <div className="oneui-card-header">
            <h3 className="oneui-card-title">Request Rate</h3>
          </div>
          <div className="h-48 flex items-end gap-1">
            {requests.map((height, i) => (
              <div
                key={i}
                className="flex-1 bg-gradient-to-t from-indigo-500 to-purple-600 rounded-t transition-all hover:opacity-80"
                style={{ height: `${height}%`, minHeight: '2px' }}
              />
            ))}
          </div>
          <div className="flex justify-between mt-4 text-xs oneui-text-muted">
            <span>0s</span>
            <span>25s</span>
            <span>50s</span>
          </div>
        </div>

        {/* Response Times */}
        <div className="oneui-card">
          <div className="oneui-card-header">
            <h3 className="oneui-card-title">Response Times</h3>
          </div>
          <div className="space-y-4">
            {[
              { endpoint: '/api/messages', time: 45, color: 'bg-green-500' },
              { endpoint: '/api/users', time: 67, color: 'bg-yellow-500' },
              { endpoint: '/api/modules', time: 32, color: 'bg-green-500' },
              { endpoint: '/api/stats', time: 89, color: 'bg-orange-500' },
            ].map((endpoint) => (
              <div key={endpoint.endpoint}>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-mono" style={{ color: 'var(--oneui-text)' }}>
                    {endpoint.endpoint}
                  </span>
                  <span className="text-sm font-semibold" style={{ color: 'var(--oneui-text)' }}>
                    {endpoint.time}ms
                  </span>
                </div>
                <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${endpoint.color} rounded-full transition-all duration-500`}
                    style={{ width: `${Math.min(endpoint.time, 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
