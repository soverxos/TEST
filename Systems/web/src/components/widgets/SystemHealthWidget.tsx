interface SystemHealthWidgetProps {
  metrics?: Array<{
    label: string;
    value: number;
    color: 'primary' | 'success' | 'info' | 'warning' | 'danger';
  }>;
}

export const SystemHealthWidget = ({ metrics = [] }: SystemHealthWidgetProps) => {
  const defaultMetrics = [
    { label: 'Использование CPU', value: 45, color: 'primary' as const },
    { label: 'Память', value: 62, color: 'success' as const },
    { label: 'Сеть', value: 28, color: 'info' as const },
    { label: 'Хранилище', value: 71, color: 'warning' as const },
  ];

  const items = metrics.length > 0 ? metrics : defaultMetrics;

  return (
    <div className="space-y-5">
      {items.map((metric, index) => (
        <div key={index}>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium" style={{ color: 'var(--oneui-text)' }}>
              {metric.label}
            </span>
            <span className="text-sm font-semibold" style={{ color: `var(--oneui-${metric.color})` }}>
              {metric.value}%
            </span>
          </div>
          <div className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-700"
              style={{
                width: `${metric.value}%`,
                backgroundColor: `var(--oneui-${metric.color})`,
              }}
            ></div>
          </div>
        </div>
      ))}
    </div>
  );
};

