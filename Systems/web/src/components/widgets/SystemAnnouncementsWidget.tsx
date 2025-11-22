import { useI18n } from '../../contexts/I18nContext';
import { Megaphone, Info, AlertCircle } from 'lucide-react';

export const SystemAnnouncementsWidget = () => {
  const { t } = useI18n();

  // In the future, this would fetch from API
  const announcements = [
    {
      type: 'info' as const,
      title: t('home.announcements.maintenance') || 'Scheduled Maintenance',
      message: t('home.announcements.maintenanceDesc') || 'System maintenance scheduled for tomorrow at 2:00 AM',
      date: '2024-01-15',
    },
    {
      type: 'success' as const,
      title: t('home.announcements.update') || 'System Update',
      message: t('home.announcements.updateDesc') || 'New features have been added to the dashboard',
      date: '2024-01-10',
    },
  ];

  const getIcon = (type: string) => {
    switch (type) {
      case 'info':
        return Info;
      case 'warning':
        return AlertCircle;
      default:
        return Megaphone;
    }
  };

  const getColor = (type: string) => {
    switch (type) {
      case 'info':
        return 'text-blue-500';
      case 'warning':
        return 'text-yellow-500';
      case 'success':
        return 'text-green-500';
      default:
        return 'text-gray-500';
    }
  };

  if (announcements.length === 0) {
    return (
      <div className="text-center py-8">
        <Megaphone className="w-12 h-12 mx-auto mb-2 oneui-text-muted" />
        <p className="text-sm oneui-text-muted">{t('home.noAnnouncements') || 'No announcements'}</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {announcements.map((announcement, index) => {
        const Icon = getIcon(announcement.type);
        return (
          <div
            key={index}
            className="p-4 rounded-lg border-l-4"
            style={{
              backgroundColor: 'var(--oneui-bg-alt)',
              borderLeftColor: announcement.type === 'info' ? 'var(--oneui-info)' :
                             announcement.type === 'warning' ? 'var(--oneui-warning)' :
                             'var(--oneui-success)',
            }}
          >
            <div className="flex items-start gap-3">
              <Icon className={`w-5 h-5 flex-shrink-0 mt-0.5 ${getColor(announcement.type)}`} />
              <div className="flex-1">
                <p className="text-sm font-semibold mb-1" style={{ color: 'var(--oneui-text)' }}>
                  {announcement.title}
                </p>
                <p className="text-xs oneui-text-muted mb-2">
                  {announcement.message}
                </p>
                <p className="text-xs oneui-text-muted">
                  {new Date(announcement.date).toLocaleDateString()}
                </p>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};

