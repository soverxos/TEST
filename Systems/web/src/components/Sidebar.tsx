import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useI18n } from '../contexts/I18nContext';
import {
  Home,
  Box,
  Users,
  BarChart3,
  FileText,
  Settings,
  BookOpen,
  Server,
  Activity,
  Sliders,
  Shield,
  ChevronRight,
  ChevronDown,
  Bell,
  Database,
  Key,
  Terminal,
  HelpCircle,
  Grid,
  Rocket,
  Clock,
  ShieldCheck,
  Database as DatabaseIcon,
  Megaphone,
} from 'lucide-react';

type MenuItem = {
  id: string;
  labelKey: string;
  icon: React.ElementType;
  adminOnly?: boolean;
  userOnly?: boolean;
};

// Общие пункты меню (для всех)
const commonMenuItems: MenuItem[] = [
  { id: 'home', labelKey: 'sidebar.home', icon: Home },
  { id: 'modules', labelKey: 'sidebar.modules', icon: Box },
  { id: 'settings', labelKey: 'sidebar.settings', icon: Settings },
];

// Пункты меню для обычных пользователей
const userMenuItems: MenuItem[] = [
  { id: 'home', labelKey: 'sidebar.home', icon: Home },
  { id: 'modules', labelKey: 'sidebar.modulesHub', icon: Grid },
  { id: 'statistics', labelKey: 'sidebar.statistics', icon: BarChart3 },
  { id: 'notifications', labelKey: 'sidebar.notifications', icon: Bell, userOnly: true },
  { id: 'data', labelKey: 'sidebar.data', icon: Database, userOnly: true },
  { id: 'developer', labelKey: 'sidebar.developer', icon: Key, userOnly: true },
  { id: 'terminal', labelKey: 'sidebar.terminal', icon: Terminal, userOnly: true },
  { id: 'security', labelKey: 'sidebar.security', icon: Shield, userOnly: true },
  { id: 'support', labelKey: 'sidebar.support', icon: HelpCircle, userOnly: true },
  { id: 'settings', labelKey: 'sidebar.settings', icon: Settings },
  { id: 'docs', labelKey: 'sidebar.documentation', icon: BookOpen },
];

// Пункты меню для админов (дополнительно к пользовательским)
const adminMenuItems: MenuItem[] = [
  { id: 'missionControl', labelKey: 'sidebar.missionControl', icon: Rocket, adminOnly: true },
  { id: 'users', labelKey: 'sidebar.users', icon: Users, adminOnly: true },
  { id: 'logs', labelKey: 'sidebar.logs', icon: FileText, adminOnly: true },
  { id: 'cronJobs', labelKey: 'sidebar.cronJobs', icon: Clock, adminOnly: true },
  { id: 'securityOperations', labelKey: 'sidebar.securityOperations', icon: ShieldCheck, adminOnly: true },
  { id: 'databaseData', labelKey: 'sidebar.databaseData', icon: DatabaseIcon, adminOnly: true },
  { id: 'broadcastStudio', labelKey: 'sidebar.broadcastStudio', icon: Megaphone, adminOnly: true },
  { id: 'config', labelKey: 'sidebar.coreConfig', icon: Sliders, adminOnly: true },
  { id: 'coreManagement', labelKey: 'sidebar.coreManagement', icon: Settings, adminOnly: true },
  { id: 'services', labelKey: 'sidebar.services', icon: Server, adminOnly: true },
  { id: 'monitoring', labelKey: 'sidebar.monitoring', icon: Activity, adminOnly: true },
];

type SidebarProps = {
  activeSection: string;
  onSectionChange: (section: string) => void;
  isMobileOpen: boolean;
  onClose: () => void;
};

export const Sidebar = ({ activeSection, onSectionChange, isMobileOpen, onClose }: SidebarProps) => {
  const { isAdmin, profile } = useAuth();
  const { t } = useI18n();
  const [userMenuCollapsed, setUserMenuCollapsed] = useState(false);
  const [adminMenuCollapsed, setAdminMenuCollapsed] = useState(false);

  const handleItemClick = (id: string) => {
    onSectionChange(id);
    onClose();
  };

  // Разделяем на пользовательские и админские пункты
  const userItems = userMenuItems;
  const adminItems = isAdmin ? adminMenuItems : [];

  return (
    <>
      {isMobileOpen && (
        <div
          className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40 lg:hidden"
          onClick={onClose}
        />
      )}

      <aside className={`oneui-sidebar ${isMobileOpen ? 'open' : ''}`} style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
        {/* Logo */}
        <div className="oneui-logo" style={{ flexShrink: 0 }}>
          <div className="oneui-logo-text">SwiftDevBot</div>
        </div>

        {/* Navigation - scrollable area */}
        <nav className="oneui-nav" style={{ flex: 1, overflowY: 'auto', minHeight: 0 }}>
          {/* User Menu Section */}
          <div>
            <button
              onClick={() => setUserMenuCollapsed(!userMenuCollapsed)}
              className="w-full flex items-center justify-between px-4 py-2 mb-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
      >
              <span className="text-xs font-semibold uppercase oneui-text-muted">
                {t('sidebar.userMenu')}
              </span>
              {userMenuCollapsed ? (
                <ChevronRight className="w-4 h-4 oneui-text-muted" />
              ) : (
                <ChevronDown className="w-4 h-4 oneui-text-muted" />
              )}
            </button>
            {!userMenuCollapsed && (
              <div className="space-y-1">
                {userItems.map((item) => {
                const Icon = item.icon;
                const isActive = activeSection === item.id;

                return (
                    <div
                    key={item.id}
                    onClick={() => handleItemClick(item.id)}
                      className={`oneui-nav-item ${isActive ? 'active' : ''}`}
                  >
                      <Icon className="oneui-nav-item-icon" />
                      <span className="oneui-nav-item-text">{t(item.labelKey)}</span>
                    </div>
                );
              })}
              </div>
            )}
          </div>

              {/* Admin section - only for admins */}
          {isAdmin && adminItems.length > 0 && (
            <div className="mt-4">
                  <button
                onClick={() => setAdminMenuCollapsed(!adminMenuCollapsed)}
                className="w-full flex items-center justify-between px-4 py-2 mb-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
              >
                <span className="text-xs font-semibold uppercase oneui-text-muted">
                  {t('sidebar.adminPanel')}
                    </span>
                {adminMenuCollapsed ? (
                  <ChevronRight className="w-4 h-4 oneui-text-muted" />
                    ) : (
                  <ChevronDown className="w-4 h-4 oneui-text-muted" />
                    )}
                  </button>
              {!adminMenuCollapsed && (
                <div className="space-y-1">
                  {adminItems.map((item) => {
                        const Icon = item.icon;
                        const isActive = activeSection === item.id;

                        return (
                      <div
                            key={item.id}
                            onClick={() => handleItemClick(item.id)}
                        className={`oneui-nav-item ${isActive ? 'active' : ''}`}
                          >
                        <Icon className="oneui-nav-item-icon" />
                        <span className="oneui-nav-item-text">{t(item.labelKey)}</span>
                      </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}
            </nav>

        {/* Footer - fixed at bottom */}
        <div className="border-t p-4 flex-shrink-0" style={{ borderColor: 'rgba(255, 255, 255, 0.1)' }}>
          <div className="text-xs text-center" style={{ color: 'rgba(255, 255, 255, 0.5)' }}>
            <div className="font-semibold mb-1">SwiftDevBot</div>
            <div>v0.1.0</div>
          </div>
        </div>
      </aside>
    </>
  );
};
