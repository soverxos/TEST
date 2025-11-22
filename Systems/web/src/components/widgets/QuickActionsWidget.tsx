import { useI18n } from '../../contexts/I18nContext';
import { useAuth } from '../../contexts/AuthContext';
import { useNavigation } from '../../contexts/NavigationContext';
import { Grid, Database, Key, Shield, Settings, BarChart3, Bell, HelpCircle } from 'lucide-react';

export const QuickActionsWidget = () => {
  const { t } = useI18n();
  const { isAdmin } = useAuth();
  const { navigateTo } = useNavigation();

  // Actions for regular users
  const userActions = [
    { icon: Grid, label: t('home.quickActions.myModules') || 'Мои модули', section: 'modulesHub', color: 'primary' },
    { icon: Database, label: t('home.quickActions.myData') || 'Мои данные', section: 'data', color: 'success' },
    { icon: Key, label: t('home.quickActions.apiKeys') || 'API Ключи', section: 'developer', color: 'warning' },
    { icon: Shield, label: t('home.quickActions.security') || 'Безопасность', section: 'security', color: 'danger' },
  ];

  // Additional actions for admins
  const adminActions = [
    { icon: BarChart3, label: t('home.quickActions.statistics') || 'Статистика', section: 'statistics', color: 'info' },
    { icon: Bell, label: t('home.quickActions.notifications') || 'Уведомления', section: 'notifications', color: 'primary' },
    { icon: Settings, label: t('home.quickActions.settings') || 'Настройки', section: 'settings', color: 'secondary' },
    { icon: HelpCircle, label: t('home.quickActions.support') || 'Поддержка', section: 'support', color: 'info' },
  ];

  const actions = isAdmin ? [...userActions, ...adminActions] : userActions;

  const handleClick = (section: string) => {
    try {
      navigateTo(section);
    } catch (error) {
      console.error('Navigation error:', error);
    }
  };

  const getColorClass = (color: string) => {
    const colorMap: Record<string, string> = {
      primary: 'var(--oneui-primary)',
      success: 'var(--oneui-success)',
      warning: 'var(--oneui-warning)',
      danger: 'var(--oneui-danger)',
      info: 'var(--oneui-info)',
      secondary: 'var(--oneui-secondary)',
    };
    return colorMap[color] || colorMap.primary;
  };

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {actions.map((action, index) => {
        const Icon = action.icon;
        const iconColor = getColorClass(action.color);
        return (
          <button
            key={index}
            onClick={() => handleClick(action.section)}
            className="flex flex-col items-center gap-2 p-4 rounded-lg border transition-all hover:bg-gray-50 dark:hover:bg-gray-800 hover:border-indigo-500 cursor-pointer"
            style={{
              backgroundColor: 'var(--oneui-bg-alt)',
              borderColor: 'var(--oneui-border)',
            }}
          >
            <div className="p-2 rounded-lg" style={{ backgroundColor: iconColor, opacity: 0.1 }}>
              <Icon className="w-5 h-5" style={{ color: iconColor }} />
            </div>
            <span className="text-xs font-medium text-center" style={{ color: 'var(--oneui-text)' }}>
              {action.label}
            </span>
          </button>
        );
      })}
    </div>
  );
};
