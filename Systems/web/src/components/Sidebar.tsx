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
} from 'lucide-react';

type MenuItem = {
  id: string;
  labelKey: string;
  icon: React.ElementType;
  adminOnly?: boolean;
};

const userMenuItems: MenuItem[] = [
  { id: 'home', labelKey: 'sidebar.home', icon: Home },
  { id: 'modules', labelKey: 'sidebar.modules', icon: Box },
  { id: 'users', labelKey: 'sidebar.users', icon: Users },
  { id: 'statistics', labelKey: 'sidebar.statistics', icon: BarChart3 },
  { id: 'logs', labelKey: 'sidebar.logs', icon: FileText },
  { id: 'settings', labelKey: 'sidebar.settings', icon: Settings },
  { id: 'docs', labelKey: 'sidebar.documentation', icon: BookOpen },
];

const adminMenuItems: MenuItem[] = [
  { id: 'config', labelKey: 'sidebar.coreConfig', icon: Sliders },
  { id: 'services', labelKey: 'sidebar.services', icon: Server },
  { id: 'monitoring', labelKey: 'sidebar.monitoring', icon: Activity },
];

type SidebarProps = {
  activeSection: string;
  onSectionChange: (section: string) => void;
  isMobileOpen: boolean;
  onClose: () => void;
};

export const Sidebar = ({ activeSection, onSectionChange, isMobileOpen, onClose }: SidebarProps) => {
  const { isAdmin } = useAuth();
  const { t } = useI18n();
  const [adminMenuOpen, setAdminMenuOpen] = useState(true);

  const handleItemClick = (id: string) => {
    onSectionChange(id);
    onClose();
  };

  return (
    <>
      {isMobileOpen && (
        <div
          className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40 lg:hidden"
          onClick={onClose}
        />
      )}

      <aside className={`oneui-sidebar ${isMobileOpen ? 'open' : ''}`}>
        {/* Logo */}
        <div className="oneui-logo">
          <div className="oneui-logo-text">SwiftDevBot</div>
        </div>

        {/* Navigation */}
        <nav className="oneui-nav">
          {/* User Menu Items */}
          {userMenuItems.map((item) => {
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

          {/* Admin Section */}
          {isAdmin && (
            <>
              <div className="oneui-nav-section">{t('sidebar.adminPanel')}</div>
              {adminMenuItems.map((item) => {
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
            </>
          )}
        </nav>

        {/* Footer */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t" style={{ borderColor: 'rgba(255, 255, 255, 0.1)' }}>
          <div className="text-xs text-center" style={{ color: 'rgba(255, 255, 255, 0.5)' }}>
            <div className="font-semibold mb-1">SwiftDevBot</div>
            <div>v0.1.0</div>
          </div>
        </div>
      </aside>
    </>
  );
};
