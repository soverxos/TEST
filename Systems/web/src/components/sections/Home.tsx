import { useEffect, useState } from 'react';
import { api, BotStats } from '../../api';
import { useI18n } from '../../contexts/I18nContext';
import { Settings } from 'lucide-react';
import { WidgetContainer } from '../widgets/WidgetContainer';
import { StatsWidget } from '../widgets/StatsWidget';
import { ActivityWidget } from '../widgets/ActivityWidget';
import { SystemHealthWidget } from '../widgets/SystemHealthWidget';
import { QuickActionsWidget } from '../widgets/QuickActionsWidget';
import { RecentErrorsWidget } from '../widgets/RecentErrorsWidget';
import { TopModulesWidget } from '../widgets/TopModulesWidget';
import { UserStatsWidget } from '../widgets/UserStatsWidget';
import { ServicesStatusWidget } from '../widgets/ServicesStatusWidget';
import { PerformanceWidget } from '../widgets/PerformanceWidget';
import { SystemAnnouncementsWidget } from '../widgets/SystemAnnouncementsWidget';
import { UptimeWidget } from '../widgets/UptimeWidget';
import { WeatherWidget } from '../widgets/WeatherWidget';
import { CalendarWidget } from '../widgets/CalendarWidget';
import { NotesWidget } from '../widgets/NotesWidget';
import { TasksWidget } from '../widgets/TasksWidget';
import { TimeWidget } from '../widgets/TimeWidget';
import { GitHubWidget } from '../widgets/GitHubWidget';
import { ToolsWidget } from '../widgets/ToolsWidget';
import { WidgetSettings, WidgetConfig, WidgetType } from '../widgets/WidgetSettings';

const WIDGET_STORAGE_KEY = 'sdb_home_widgets_config';

const DEFAULT_WIDGETS: WidgetConfig[] = [
  { id: 'stats', type: 'stats', title: 'Статистика', enabled: true, order: 0 },
  { id: 'activity', type: 'activity', title: 'Последняя активность', enabled: true, order: 1 },
  { id: 'systemHealth', type: 'systemHealth', title: 'Состояние системы', enabled: true, order: 2 },
  { id: 'quickActions', type: 'custom', title: 'Быстрые действия', enabled: true, order: 3 },
  { id: 'recentErrors', type: 'custom', title: 'Последние ошибки', enabled: false, order: 4 },
  { id: 'topModules', type: 'custom', title: 'Топ модулей', enabled: false, order: 5 },
  { id: 'userStats', type: 'custom', title: 'Статистика пользователей', enabled: false, order: 6 },
  { id: 'servicesStatus', type: 'custom', title: 'Статус сервисов', enabled: false, order: 7 },
  { id: 'performance', type: 'custom', title: 'Производительность', enabled: false, order: 8 },
  { id: 'announcements', type: 'custom', title: 'Объявления', enabled: false, order: 9 },
  { id: 'uptime', type: 'custom', title: 'Время работы', enabled: false, order: 10 },
  { id: 'weather', type: 'custom', title: 'Погода', enabled: false, order: 11 },
  { id: 'calendar', type: 'custom', title: 'Календарь', enabled: false, order: 12 },
  { id: 'notes', type: 'custom', title: 'Заметки', enabled: false, order: 13 },
  { id: 'tasks', type: 'custom', title: 'Задачи', enabled: false, order: 14 },
  { id: 'time', type: 'custom', title: 'Время', enabled: false, order: 15 },
  { id: 'github', type: 'custom', title: 'GitHub', enabled: false, order: 16 },
  { id: 'tools', type: 'custom', title: 'Инструменты', enabled: false, order: 17 },
];

export const Home = () => {
  const { t } = useI18n();
  const [botStats, setBotStats] = useState<BotStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [widgets, setWidgets] = useState<WidgetConfig[]>(DEFAULT_WIDGETS);
  const [enabledWidgetIds, setEnabledWidgetIds] = useState<string[]>(['stats', 'activity', 'systemHealth', 'quickActions']);
  const [showSettings, setShowSettings] = useState(false);
  const [draggedWidgetId, setDraggedWidgetId] = useState<string | null>(null);
  const [dragOverWidgetId, setDragOverWidgetId] = useState<string | null>(null);

  useEffect(() => {
    // Load widget configuration from localStorage
    const savedConfig = localStorage.getItem(WIDGET_STORAGE_KEY);
    if (savedConfig) {
      try {
        const config = JSON.parse(savedConfig);
        setWidgets(config.widgets || DEFAULT_WIDGETS);
        setEnabledWidgetIds(config.enabledIds || ['stats', 'activity', 'systemHealth']);
      } catch (e) {
        console.error('Error loading widget config:', e);
      }
    }

    loadStats();
    const interval = setInterval(loadStats, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadStats = async () => {
    try {
      const stats: BotStats = await api.getStats();
      setBotStats(stats);
    } catch (error) {
      console.error('Error loading stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const saveWidgetConfig = (enabledIds: string[]) => {
    const config = {
      widgets: widgets,
      enabledIds: enabledIds,
    };
    localStorage.setItem(WIDGET_STORAGE_KEY, JSON.stringify(config));
    setEnabledWidgetIds(enabledIds);
  };

  const removeWidget = (id: string) => {
    const newEnabled = enabledWidgetIds.filter(w => w !== id);
    saveWidgetConfig(newEnabled);
  };

  const handleDragStart = (e: React.DragEvent, widgetId: string) => {
    setDraggedWidgetId(widgetId);
  };

  const handleDragOver = (e: React.DragEvent, widgetId: string) => {
    e.preventDefault();
    if (draggedWidgetId && draggedWidgetId !== widgetId) {
      setDragOverWidgetId(widgetId);
    }
  };

  const handleDrop = (e: React.DragEvent, targetWidgetId: string) => {
    e.preventDefault();
    if (!draggedWidgetId || draggedWidgetId === targetWidgetId) {
      setDraggedWidgetId(null);
      setDragOverWidgetId(null);
      return;
    }

    const draggedIndex = enabledWidgetIds.indexOf(draggedWidgetId);
    const targetIndex = enabledWidgetIds.indexOf(targetWidgetId);

    if (draggedIndex === -1 || targetIndex === -1) {
      setDraggedWidgetId(null);
      setDragOverWidgetId(null);
      return;
    }

    const newOrder = [...enabledWidgetIds];
    newOrder.splice(draggedIndex, 1);
    newOrder.splice(targetIndex, 0, draggedWidgetId);

    saveWidgetConfig(newOrder);
    setDraggedWidgetId(null);
    setDragOverWidgetId(null);
  };

  const handleDragEnd = () => {
    setDraggedWidgetId(null);
    setDragOverWidgetId(null);
  };

  const renderWidget = (widgetId: string) => {
    const widget = widgets.find(w => w.id === widgetId);
    if (!widget) return null;

    const isDragging = draggedWidgetId === widgetId;
    const isDragOver = dragOverWidgetId === widgetId;

    switch (widget.type) {
      case 'stats':
        return (
          <WidgetContainer
            key={widget.id}
            id={widget.id}
            title={widget.title}
            onRemove={() => removeWidget(widget.id)}
            isDragging={isDragging}
            onDragStart={(e) => handleDragStart(e, widget.id)}
            onDragOver={(e) => handleDragOver(e, widget.id)}
            onDrop={(e) => handleDrop(e, widget.id)}
            onDragEnd={handleDragEnd}
          >
            {botStats ? <StatsWidget stats={botStats} /> : <div className="text-center py-8 oneui-text-muted">Loading...</div>}
          </WidgetContainer>
        );
      case 'activity':
        return (
          <WidgetContainer
            key={widget.id}
            id={widget.id}
            title={widget.title}
            onRemove={() => removeWidget(widget.id)}
            isDragging={isDragging}
            onDragStart={(e) => handleDragStart(e, widget.id)}
            onDragOver={(e) => handleDragOver(e, widget.id)}
            onDrop={(e) => handleDrop(e, widget.id)}
            onDragEnd={handleDragEnd}
          >
            <ActivityWidget />
          </WidgetContainer>
        );
      case 'systemHealth':
        return (
          <WidgetContainer
            key={widget.id}
            id={widget.id}
            title={widget.title}
            onRemove={() => removeWidget(widget.id)}
            isDragging={isDragging}
            onDragStart={(e) => handleDragStart(e, widget.id)}
            onDragOver={(e) => handleDragOver(e, widget.id)}
            onDrop={(e) => handleDrop(e, widget.id)}
            onDragEnd={handleDragEnd}
          >
            <SystemHealthWidget />
          </WidgetContainer>
        );
      case 'custom':
        // Render custom widgets based on id
        if (widget.id === 'quickActions') {
          return (
            <WidgetContainer
              key={widget.id}
              id={widget.id}
              title={widget.title}
              onRemove={() => removeWidget(widget.id)}
              isDragging={isDragging}
              onDragStart={(e) => handleDragStart(e, widget.id)}
              onDragOver={(e) => handleDragOver(e, widget.id)}
              onDrop={(e) => handleDrop(e, widget.id)}
              onDragEnd={handleDragEnd}
            >
              <QuickActionsWidget />
            </WidgetContainer>
          );
        }
        if (widget.id === 'recentErrors') {
          return (
            <WidgetContainer
              key={widget.id}
              id={widget.id}
              title={widget.title}
              onRemove={() => removeWidget(widget.id)}
              isDragging={isDragging}
              onDragStart={(e) => handleDragStart(e, widget.id)}
              onDragOver={(e) => handleDragOver(e, widget.id)}
              onDrop={(e) => handleDrop(e, widget.id)}
              onDragEnd={handleDragEnd}
            >
              <RecentErrorsWidget />
            </WidgetContainer>
          );
        }
        if (widget.id === 'topModules') {
          return (
            <WidgetContainer
              key={widget.id}
              id={widget.id}
              title={widget.title}
              onRemove={() => removeWidget(widget.id)}
              isDragging={isDragging}
              onDragStart={(e) => handleDragStart(e, widget.id)}
              onDragOver={(e) => handleDragOver(e, widget.id)}
              onDrop={(e) => handleDrop(e, widget.id)}
              onDragEnd={handleDragEnd}
            >
              <TopModulesWidget />
            </WidgetContainer>
          );
        }
        if (widget.id === 'userStats') {
          return (
            <WidgetContainer
              key={widget.id}
              id={widget.id}
              title={widget.title}
              onRemove={() => removeWidget(widget.id)}
              isDragging={isDragging}
              onDragStart={(e) => handleDragStart(e, widget.id)}
              onDragOver={(e) => handleDragOver(e, widget.id)}
              onDrop={(e) => handleDrop(e, widget.id)}
              onDragEnd={handleDragEnd}
            >
              <UserStatsWidget />
            </WidgetContainer>
          );
        }
        if (widget.id === 'servicesStatus') {
          return (
            <WidgetContainer
              key={widget.id}
              id={widget.id}
              title={widget.title}
              onRemove={() => removeWidget(widget.id)}
              isDragging={isDragging}
              onDragStart={(e) => handleDragStart(e, widget.id)}
              onDragOver={(e) => handleDragOver(e, widget.id)}
              onDrop={(e) => handleDrop(e, widget.id)}
              onDragEnd={handleDragEnd}
            >
              <ServicesStatusWidget />
            </WidgetContainer>
          );
        }
        if (widget.id === 'performance') {
          return (
            <WidgetContainer
              key={widget.id}
              id={widget.id}
              title={widget.title}
              onRemove={() => removeWidget(widget.id)}
              isDragging={isDragging}
              onDragStart={(e) => handleDragStart(e, widget.id)}
              onDragOver={(e) => handleDragOver(e, widget.id)}
              onDrop={(e) => handleDrop(e, widget.id)}
              onDragEnd={handleDragEnd}
            >
              <PerformanceWidget />
            </WidgetContainer>
          );
        }
        if (widget.id === 'announcements') {
          return (
            <WidgetContainer
              key={widget.id}
              id={widget.id}
              title={widget.title}
              onRemove={() => removeWidget(widget.id)}
              isDragging={isDragging}
              onDragStart={(e) => handleDragStart(e, widget.id)}
              onDragOver={(e) => handleDragOver(e, widget.id)}
              onDrop={(e) => handleDrop(e, widget.id)}
              onDragEnd={handleDragEnd}
            >
              <SystemAnnouncementsWidget />
            </WidgetContainer>
          );
        }
        if (widget.id === 'uptime') {
          return (
            <WidgetContainer
              key={widget.id}
              id={widget.id}
              title={widget.title}
              onRemove={() => removeWidget(widget.id)}
              isDragging={isDragging}
              onDragStart={(e) => handleDragStart(e, widget.id)}
              onDragOver={(e) => handleDragOver(e, widget.id)}
              onDrop={(e) => handleDrop(e, widget.id)}
              onDragEnd={handleDragEnd}
            >
              <UptimeWidget />
            </WidgetContainer>
          );
        }
        if (widget.id === 'weather') {
          return (
            <WidgetContainer
              key={widget.id}
              id={widget.id}
              title={widget.title}
              onRemove={() => removeWidget(widget.id)}
              isDragging={isDragging}
              onDragStart={(e) => handleDragStart(e, widget.id)}
              onDragOver={(e) => handleDragOver(e, widget.id)}
              onDrop={(e) => handleDrop(e, widget.id)}
              onDragEnd={handleDragEnd}
            >
              <WeatherWidget />
            </WidgetContainer>
          );
        }
        if (widget.id === 'calendar') {
          return (
            <WidgetContainer
              key={widget.id}
              id={widget.id}
              title={widget.title}
              onRemove={() => removeWidget(widget.id)}
              isDragging={isDragging}
              onDragStart={(e) => handleDragStart(e, widget.id)}
              onDragOver={(e) => handleDragOver(e, widget.id)}
              onDrop={(e) => handleDrop(e, widget.id)}
              onDragEnd={handleDragEnd}
            >
              <CalendarWidget />
            </WidgetContainer>
          );
        }
        if (widget.id === 'notes') {
          return (
            <WidgetContainer
              key={widget.id}
              id={widget.id}
              title={widget.title}
              onRemove={() => removeWidget(widget.id)}
              isDragging={isDragging}
              onDragStart={(e) => handleDragStart(e, widget.id)}
              onDragOver={(e) => handleDragOver(e, widget.id)}
              onDrop={(e) => handleDrop(e, widget.id)}
              onDragEnd={handleDragEnd}
            >
              <NotesWidget />
            </WidgetContainer>
          );
        }
        if (widget.id === 'tasks') {
          return (
            <WidgetContainer
              key={widget.id}
              id={widget.id}
              title={widget.title}
              onRemove={() => removeWidget(widget.id)}
              isDragging={isDragging}
              onDragStart={(e) => handleDragStart(e, widget.id)}
              onDragOver={(e) => handleDragOver(e, widget.id)}
              onDrop={(e) => handleDrop(e, widget.id)}
              onDragEnd={handleDragEnd}
            >
              <TasksWidget />
            </WidgetContainer>
          );
        }
        if (widget.id === 'time') {
          return (
            <WidgetContainer
              key={widget.id}
              id={widget.id}
              title={widget.title}
              onRemove={() => removeWidget(widget.id)}
              isDragging={isDragging}
              onDragStart={(e) => handleDragStart(e, widget.id)}
              onDragOver={(e) => handleDragOver(e, widget.id)}
              onDrop={(e) => handleDrop(e, widget.id)}
              onDragEnd={handleDragEnd}
            >
              <TimeWidget />
            </WidgetContainer>
          );
        }
        if (widget.id === 'github') {
          return (
            <WidgetContainer
              key={widget.id}
              id={widget.id}
              title={widget.title}
              onRemove={() => removeWidget(widget.id)}
              isDragging={isDragging}
              onDragStart={(e) => handleDragStart(e, widget.id)}
              onDragOver={(e) => handleDragOver(e, widget.id)}
              onDrop={(e) => handleDrop(e, widget.id)}
              onDragEnd={handleDragEnd}
            >
              <GitHubWidget />
            </WidgetContainer>
          );
        }
        if (widget.id === 'tools') {
          return (
            <WidgetContainer
              key={widget.id}
              id={widget.id}
              title={widget.title}
              onRemove={() => removeWidget(widget.id)}
              isDragging={isDragging}
              onDragStart={(e) => handleDragStart(e, widget.id)}
              onDragOver={(e) => handleDragOver(e, widget.id)}
              onDrop={(e) => handleDrop(e, widget.id)}
              onDragEnd={handleDragEnd}
            >
              <ToolsWidget />
            </WidgetContainer>
          );
        }
        return null;
    }
  };

  if (loading && !botStats) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="oneui-spinner"></div>
      </div>
    );
  }

  const enabledWidgets = enabledWidgetIds
    .map(id => widgets.find(w => w.id === id))
    .filter((w): w is WidgetConfig => w !== undefined);

  return (
    <div>
      {/* Page Header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold mb-2" style={{ color: 'var(--oneui-text)' }}>
            {t('home.title')}
          </h1>
          <p className="oneui-text-muted">{t('home.subtitle')}</p>
        </div>
        <button
          onClick={() => setShowSettings(true)}
          className="oneui-btn oneui-btn-secondary flex items-center gap-2"
          title={t('home.customize') || 'Customize widgets'}
        >
          <Settings className="w-4 h-4" />
          {t('home.customize') || 'Customize'}
        </button>
      </div>

      {/* Widgets Grid */}
      <div className="space-y-6">
        {enabledWidgets.length === 0 ? (
          <div className="oneui-card text-center py-12">
            <p className="oneui-text-muted mb-4">{t('home.noWidgets') || 'No widgets enabled'}</p>
            <button
              onClick={() => setShowSettings(true)}
              className="oneui-btn oneui-btn-primary"
            >
              {t('home.addWidgets') || 'Add Widgets'}
            </button>
          </div>
        ) : (
          enabledWidgets.map(widget => renderWidget(widget.id))
        )}
      </div>

      {/* Widget Settings Modal */}
      {showSettings && (
        <WidgetSettings
          availableWidgets={widgets}
          enabledWidgets={enabledWidgetIds}
          onClose={() => setShowSettings(false)}
          onSave={saveWidgetConfig}
        />
      )}
    </div>
  );
};
