import { BotStats } from '../../api';
import { Zap, Users, TrendingUp, Activity, ArrowUpRight, ArrowDownRight } from 'lucide-react';

interface StatsWidgetProps {
  stats: BotStats;
  showChange?: boolean;
}

export const StatsWidget = ({ stats, showChange = true }: StatsWidgetProps) => {
  const statCards = [
    {
      label: 'Активные модули',
      value: stats.active_modules || 0,
      icon: Zap,
      iconClass: 'oneui-stat-icon-primary',
      change: '+2.5%',
      changePositive: true,
    },
    {
      label: 'Всего пользователей',
      value: stats.total_users || 0,
      icon: Users,
      iconClass: 'oneui-stat-icon-success',
      change: '+3.8%',
      changePositive: true,
    },
    {
      label: 'Взаимодействий сегодня',
      value: stats.messages_today || 0,
      icon: TrendingUp,
      iconClass: 'oneui-stat-icon-warning',
      change: '+1.7%',
      changePositive: true,
    },
    {
      label: 'Статус системы',
      value: 'ONLINE',
      icon: Activity,
      iconClass: 'oneui-stat-icon-success',
      change: '100%',
      changePositive: true,
    },
  ];

  return (
    <div className="oneui-stats-grid">
      {statCards.map((card, index) => {
        const Icon = card.icon;
        return (
          <div key={index} className="oneui-stat-card">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="oneui-stat-label">{card.label}</div>
                <div className="oneui-stat-value">{card.value}</div>
                {showChange && (
                  <div className="flex items-center gap-1 mt-2 text-sm" style={{ color: card.changePositive ? 'var(--oneui-success)' : 'var(--oneui-danger)' }}>
                    {card.changePositive ? (
                      <ArrowUpRight className="w-4 h-4" />
                    ) : (
                      <ArrowDownRight className="w-4 h-4" />
                    )}
                    <span>{card.change}</span>
                  </div>
                )}
              </div>
              <div className={card.iconClass}>
                <Icon className="w-6 h-6" />
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};

