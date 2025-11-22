import { useState } from 'react';
import { useI18n } from '../../contexts/I18nContext';
import { Bell, Mail, Smartphone, Clock } from 'lucide-react';

export const Notifications = () => {
  const { t } = useI18n();
  const [channels, setChannels] = useState({
    telegram: true,
    email: false,
    push: true,
  });

  const [notificationTypes, setNotificationTypes] = useState({
    news: true,
    security: true,
    tasks: true,
    marketing: false,
  });

  const [doNotDisturb, setDoNotDisturb] = useState(false);
  const [schedule, setSchedule] = useState({ from: '22:00', to: '08:00' });

  return (
    <div>
      {/* Page Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-2" style={{ color: 'var(--oneui-text)' }}>
          {t('notifications.title')}
        </h1>
        <p className="oneui-text-muted">{t('notifications.subtitle')}</p>
      </div>

      {/* Delivery Channels */}
      <div className="oneui-card mb-6">
        <div className="oneui-card-header">
          <h3 className="oneui-card-title">{t('notifications.channels')}</h3>
        </div>
        <div className="space-y-4">
          {[
            { key: 'telegram', label: t('notifications.telegram'), icon: Bell },
            { key: 'email', label: t('notifications.email'), icon: Mail },
            { key: 'push', label: t('notifications.push'), icon: Smartphone },
          ].map((channel) => {
            const Icon = channel.icon;
            return (
              <div
                key={channel.key}
                className="flex items-center justify-between p-4 rounded-lg"
                style={{ backgroundColor: 'var(--oneui-bg-alt)' }}
              >
                <div className="flex items-center gap-3">
                  <Icon className="w-5 h-5" style={{ color: 'var(--oneui-text-muted)' }} />
                  <span className="font-medium" style={{ color: 'var(--oneui-text)' }}>
                    {channel.label}
                  </span>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    className="sr-only peer"
                    checked={channels[channel.key as keyof typeof channels]}
                    onChange={(e) =>
                      setChannels({ ...channels, [channel.key]: e.target.checked })
                    }
                  />
                  <div className="w-11 h-6 bg-gray-300 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-indigo-300 dark:peer-focus:ring-indigo-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all dark:after:border-gray-600 peer-checked:bg-indigo-600"></div>
                </label>
              </div>
            );
          })}
        </div>
      </div>

      {/* Notification Types */}
      <div className="oneui-card mb-6">
        <div className="oneui-card-header">
          <h3 className="oneui-card-title">{t('notifications.types')}</h3>
        </div>
        <div className="space-y-4">
          {[
            { key: 'news', label: t('notifications.news') },
            { key: 'security', label: t('notifications.security') },
            { key: 'tasks', label: t('notifications.tasks') },
            { key: 'marketing', label: t('notifications.marketing') },
          ].map((type) => (
            <div
              key={type.key}
              className="flex items-center justify-between p-4 rounded-lg"
              style={{ backgroundColor: 'var(--oneui-bg-alt)' }}
            >
              <span className="font-medium" style={{ color: 'var(--oneui-text)' }}>
                {type.label}
              </span>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  className="sr-only peer"
                  checked={notificationTypes[type.key as keyof typeof notificationTypes]}
                  onChange={(e) =>
                    setNotificationTypes({
                      ...notificationTypes,
                      [type.key]: e.target.checked,
                    })
                  }
                />
                <div className="w-11 h-6 bg-gray-300 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-indigo-300 dark:peer-focus:ring-indigo-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all dark:after:border-gray-600 peer-checked:bg-indigo-600"></div>
              </label>
            </div>
          ))}
        </div>
      </div>

      {/* Do Not Disturb */}
      <div className="oneui-card">
        <div className="oneui-card-header">
          <div className="flex items-center gap-3">
            <Clock className="w-5 h-5" style={{ color: 'var(--oneui-text-muted)' }} />
            <h3 className="oneui-card-title">{t('notifications.doNotDisturb')}</h3>
          </div>
        </div>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="font-medium" style={{ color: 'var(--oneui-text)' }}>
              {t('notifications.doNotDisturb')}
            </span>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                className="sr-only peer"
                checked={doNotDisturb}
                onChange={(e) => setDoNotDisturb(e.target.checked)}
              />
              <div className="w-11 h-6 bg-gray-300 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-indigo-300 dark:peer-focus:ring-indigo-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all dark:after:border-gray-600 peer-checked:bg-indigo-600"></div>
            </label>
          </div>
          {doNotDisturb && (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2" style={{ color: 'var(--oneui-text)' }}>
                  {t('notifications.schedule')} (от)
                </label>
                <input
                  type="time"
                  value={schedule.from}
                  onChange={(e) => setSchedule({ ...schedule, from: e.target.value })}
                  className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  style={{
                    backgroundColor: 'var(--oneui-bg-alt)',
                    borderColor: 'var(--oneui-border)',
                    color: 'var(--oneui-text)',
                  }}
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2" style={{ color: 'var(--oneui-text)' }}>
                  {t('notifications.schedule')} (до)
                </label>
                <input
                  type="time"
                  value={schedule.to}
                  onChange={(e) => setSchedule({ ...schedule, to: e.target.value })}
                  className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  style={{
                    backgroundColor: 'var(--oneui-bg-alt)',
                    borderColor: 'var(--oneui-border)',
                    color: 'var(--oneui-text)',
                  }}
                />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

