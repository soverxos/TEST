import { useState, useEffect } from 'react';
import { useI18n } from '../../contexts/I18nContext';
import { Clock, Globe } from 'lucide-react';

interface TimeZone {
  name: string;
  city: string;
  offset: number;
}

export const TimeWidget = () => {
  const { t } = useI18n();
  const [currentTime, setCurrentTime] = useState(new Date());
  const [timeZones] = useState<TimeZone[]>([
    { name: 'UTC', city: 'UTC', offset: 0 },
    { name: 'Europe/Moscow', city: 'Moscow', offset: 3 },
    { name: 'America/New_York', city: 'New York', offset: -5 },
    { name: 'Asia/Tokyo', city: 'Tokyo', offset: 9 },
  ]);

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const getTimeInZone = (offset: number) => {
    const utc = currentTime.getTime() + currentTime.getTimezoneOffset() * 60000;
    const localTime = new Date(utc + offset * 3600000);
    return localTime;
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    });
  };

  const formatDate = (date: Date) => {
    return date.toLocaleDateString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
    });
  };

  return (
    <div className="space-y-4">
      {/* Main Clock */}
      <div className="text-center">
        <div className="flex items-center justify-center gap-2 mb-2">
          <Clock className="w-5 h-5" style={{ color: 'var(--oneui-primary)' }} />
          <span className="text-sm font-semibold" style={{ color: 'var(--oneui-text)' }}>
            {timeZones[1].city}
          </span>
        </div>
        <div className="text-4xl font-bold mb-1" style={{ color: 'var(--oneui-text)' }}>
          {formatTime(getTimeInZone(timeZones[1].offset))}
        </div>
        <div className="text-sm oneui-text-muted">
          {formatDate(getTimeInZone(timeZones[1].offset))}
        </div>
      </div>

      {/* Other Time Zones */}
      <div className="pt-3 border-t space-y-2" style={{ borderColor: 'var(--oneui-border)' }}>
        <div className="flex items-center gap-2 mb-2">
          <Globe className="w-4 h-4 oneui-text-muted" />
          <span className="text-xs font-semibold oneui-text-muted">
            {t('home.time.otherZones') || 'Other Time Zones'}
          </span>
        </div>
        {timeZones.filter(tz => tz.city !== timeZones[1].city).map((tz, index) => {
          const time = getTimeInZone(tz.offset);
          return (
            <div
              key={index}
              className="flex items-center justify-between p-2 rounded-lg"
              style={{ backgroundColor: 'var(--oneui-bg-alt)' }}
            >
              <div>
                <p className="text-xs font-medium" style={{ color: 'var(--oneui-text)' }}>
                  {tz.city}
                </p>
                <p className="text-xs oneui-text-muted">
                  {tz.offset >= 0 ? '+' : ''}{tz.offset} UTC
                </p>
              </div>
              <div className="text-right">
                <p className="text-sm font-semibold" style={{ color: 'var(--oneui-text)' }}>
                  {formatTime(time)}
                </p>
                <p className="text-xs oneui-text-muted">
                  {formatDate(time)}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

