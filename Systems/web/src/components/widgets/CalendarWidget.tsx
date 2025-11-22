import { useState, useEffect } from 'react';
import { useI18n } from '../../contexts/I18nContext';
import { ChevronLeft, ChevronRight } from 'lucide-react';

interface CalendarEvent {
  id: string;
  title: string;
  date: Date;
  color: string;
}

export const CalendarWidget = () => {
  const { t } = useI18n();
  const [currentDate, setCurrentDate] = useState(new Date());
  const [events, setEvents] = useState<CalendarEvent[]>([]);

  useEffect(() => {
    loadEvents();
  }, [currentDate]);

  const loadEvents = () => {
    // In a real implementation, this would fetch from API
    // For now, we'll use localStorage for events
    const savedEvents = localStorage.getItem('sdb_calendar_events');
    if (savedEvents) {
      try {
        const parsed = JSON.parse(savedEvents).map((e: any) => ({
          ...e,
          date: new Date(e.date),
        }));
        setEvents(parsed.filter((e: CalendarEvent) => 
          e.date.getMonth() === currentDate.getMonth() &&
          e.date.getFullYear() === currentDate.getFullYear()
        ));
      } catch (e) {
        console.error('Error loading events:', e);
      }
    }
  };

  const monthNames = [
    t('home.calendar.january') || 'January',
    t('home.calendar.february') || 'February',
    t('home.calendar.march') || 'March',
    t('home.calendar.april') || 'April',
    t('home.calendar.may') || 'May',
    t('home.calendar.june') || 'June',
    t('home.calendar.july') || 'July',
    t('home.calendar.august') || 'August',
    t('home.calendar.september') || 'September',
    t('home.calendar.october') || 'October',
    t('home.calendar.november') || 'November',
    t('home.calendar.december') || 'December',
  ];

  const dayNames = [
    t('home.calendar.sun') || 'Sun',
    t('home.calendar.mon') || 'Mon',
    t('home.calendar.tue') || 'Tue',
    t('home.calendar.wed') || 'Wed',
    t('home.calendar.thu') || 'Thu',
    t('home.calendar.fri') || 'Fri',
    t('home.calendar.sat') || 'Sat',
  ];

  const getDaysInMonth = (date: Date) => {
    return new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate();
  };

  const getFirstDayOfMonth = (date: Date) => {
    return new Date(date.getFullYear(), date.getMonth(), 1).getDay();
  };

  const prevMonth = () => {
    setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() - 1, 1));
  };

  const nextMonth = () => {
    setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 1));
  };

  const today = new Date();
  const daysInMonth = getDaysInMonth(currentDate);
  const firstDay = getFirstDayOfMonth(currentDate);
  const days = Array.from({ length: daysInMonth }, (_, i) => i + 1);
  const emptyDays = Array.from({ length: firstDay }, (_, i) => i);

  const getEventsForDay = (day: number) => {
    return events.filter(e => e.date.getDate() === day);
  };

  const isToday = (day: number) => {
    return (
      day === today.getDate() &&
      currentDate.getMonth() === today.getMonth() &&
      currentDate.getFullYear() === today.getFullYear()
    );
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <button
          onClick={prevMonth}
          className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded transition-colors"
        >
          <ChevronLeft className="w-5 h-5 oneui-text-muted" />
        </button>
        <h3 className="text-lg font-semibold" style={{ color: 'var(--oneui-text)' }}>
          {monthNames[currentDate.getMonth()]} {currentDate.getFullYear()}
        </h3>
        <button
          onClick={nextMonth}
          className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded transition-colors"
        >
          <ChevronRight className="w-5 h-5 oneui-text-muted" />
        </button>
      </div>

      {/* Calendar Grid */}
      <div className="grid grid-cols-7 gap-1">
        {/* Day names */}
        {dayNames.map((day, i) => (
          <div
            key={i}
            className="text-center text-xs font-medium py-1 oneui-text-muted"
          >
            {day}
          </div>
        ))}

        {/* Empty days */}
        {emptyDays.map((_, i) => (
          <div key={`empty-${i}`} className="aspect-square" />
        ))}

        {/* Days */}
        {days.map((day) => {
          const dayEvents = getEventsForDay(day);
          const isTodayDay = isToday(day);
          return (
            <div
              key={day}
              className={`aspect-square p-1 rounded text-xs cursor-pointer transition-colors ${
                isTodayDay
                  ? 'bg-indigo-500 text-white font-semibold'
                  : 'hover:bg-gray-100 dark:hover:bg-gray-800'
              }`}
            >
              <div className="flex items-center justify-center h-full">
                {day}
              </div>
              {dayEvents.length > 0 && (
                <div className="flex gap-0.5 justify-center mt-0.5">
                  {dayEvents.slice(0, 3).map((event, i) => (
                    <div
                      key={i}
                      className="w-1 h-1 rounded-full"
                      style={{ backgroundColor: event.color || 'var(--oneui-primary)' }}
                    />
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Upcoming Events */}
      {events.length > 0 && (
        <div className="pt-3 border-t" style={{ borderColor: 'var(--oneui-border)' }}>
          <p className="text-xs font-semibold mb-2 oneui-text-muted">
            {t('home.calendar.upcoming') || 'Upcoming Events'}
          </p>
          <div className="space-y-2">
            {events.slice(0, 3).map((event) => (
              <div
                key={event.id}
                className="flex items-center gap-2 text-xs"
                style={{ color: 'var(--oneui-text)' }}
              >
                <div
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: event.color || 'var(--oneui-primary)' }}
                />
                <span className="truncate">{event.title}</span>
                <span className="oneui-text-muted ml-auto">
                  {event.date.toLocaleDateString()}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

