interface ActivityWidgetProps {
  activities?: Array<{
    action: string;
    module: string;
    time: string;
    color: 'success' | 'info' | 'warning' | 'error';
  }>;
}

export const ActivityWidget = ({ activities = [] }: ActivityWidgetProps) => {
  const defaultActivities = [
    { action: 'Module activated', module: 'AI Chat', time: '2 minutes ago', color: 'success' as const },
    { action: 'User registered', module: 'System', time: '15 minutes ago', color: 'info' as const },
    { action: 'Code review completed', module: 'Code Review', time: '1 hour ago', color: 'success' as const },
    { action: 'Analytics updated', module: 'Analytics', time: '2 hours ago', color: 'info' as const },
  ];

  const items = activities.length > 0 ? activities : defaultActivities;

  const colorMap = {
    success: 'bg-green-500',
    info: 'bg-blue-500',
    warning: 'bg-yellow-500',
    error: 'bg-red-500',
  };

  return (
    <div className="space-y-3">
      {items.map((activity, index) => (
        <div
          key={index}
          className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
          style={{ backgroundColor: 'var(--oneui-bg-alt)' }}
        >
          <div className="flex items-center gap-3">
            <div className={`w-2 h-2 rounded-full ${colorMap[activity.color]}`}></div>
            <div>
              <p className="text-sm font-medium" style={{ color: 'var(--oneui-text)' }}>
                {activity.action}
              </p>
              <p className="text-xs oneui-text-muted">{activity.module}</p>
            </div>
          </div>
          <span className="text-xs oneui-text-muted">{activity.time}</span>
        </div>
      ))}
    </div>
  );
};

