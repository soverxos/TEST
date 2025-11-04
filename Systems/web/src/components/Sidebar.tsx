import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { GlassCard } from './ui/GlassCard';
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
  ChevronDown,
  ChevronRight,
} from 'lucide-react';

type MenuItem = {
  id: string;
  label: string;
  icon: React.ElementType;
  adminOnly?: boolean;
};

const userMenuItems: MenuItem[] = [
  { id: 'home', label: 'Home', icon: Home },
  { id: 'modules', label: 'Modules', icon: Box },
  { id: 'users', label: 'Users', icon: Users },
  { id: 'statistics', label: 'Statistics', icon: BarChart3 },
  { id: 'logs', label: 'Logs', icon: FileText },
  { id: 'settings', label: 'Settings', icon: Settings },
  { id: 'docs', label: 'Documentation', icon: BookOpen },
];

const adminMenuItems: MenuItem[] = [
  { id: 'config', label: 'Core Config', icon: Sliders },
  { id: 'services', label: 'Services', icon: Server },
  { id: 'monitoring', label: 'Monitoring', icon: Activity },
];

type SidebarProps = {
  activeSection: string;
  onSectionChange: (section: string) => void;
  isMobileOpen: boolean;
  onClose: () => void;
};

export const Sidebar = ({ activeSection, onSectionChange, isMobileOpen, onClose }: SidebarProps) => {
  const { isAdmin, profile } = useAuth();
  const [adminMenuOpen, setAdminMenuOpen] = useState(false);
  
  // Debug logging
  console.log('Sidebar render - isAdmin:', isAdmin, 'profile:', profile);

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

      <aside
        className={`
          fixed lg:sticky top-0 left-0 h-screen z-40 lg:z-20
          transform transition-transform duration-300 ease-in-out
          ${isMobileOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
        `}
      >
        <div className="h-full p-4">
          <GlassCard className="h-full p-4 w-64 flex flex-col">
            <nav className="flex-1 space-y-2">
              {/* User menu items */}
              {userMenuItems.map((item) => {
                const Icon = item.icon;
                const isActive = activeSection === item.id;

                return (
                  <button
                    key={item.id}
                    onClick={() => handleItemClick(item.id)}
                    className={`
                      w-full flex items-center gap-3 px-4 py-3 rounded-xl
                      transition-all duration-200 group
                      ${isActive
                        ? 'bg-gradient-to-r from-cyan-500/20 to-purple-500/20 border-l-4 border-cyan-400'
                        : 'hover:bg-white/10 hover:translate-x-1'
                      }
                    `}
                  >
                    <Icon
                      className={`
                        w-5 h-5 transition-colors
                        ${isActive
                          ? 'text-cyan-400'
                          : 'text-glass-text-secondary group-hover:text-glass-text'
                        }
                      `}
                    />
                    <span
                      className={`
                        font-medium text-sm
                        ${isActive
                          ? 'text-glass-text'
                          : 'text-glass-text-secondary group-hover:text-glass-text'
                        }
                      `}
                    >
                      {item.label}
                    </span>
                  </button>
                );
              })}

              {/* Admin section - only for admins */}
              {isAdmin ? (
                <div className="mt-4 pt-4 border-t border-white/10">
                  <div className="text-xs text-purple-300/50 mb-2 px-4">Admin Panel</div>
                  <button
                    onClick={() => setAdminMenuOpen(!adminMenuOpen)}
                    className={`
                      w-full flex items-center gap-3 px-4 py-3 rounded-xl
                      transition-all duration-200 group
                      bg-gradient-to-r from-purple-500/20 to-pink-500/20 border border-purple-400/30
                      hover:from-purple-500/30 hover:to-pink-500/30
                    `}
                  >
                    <Shield className="w-5 h-5 text-purple-300" />
                    <span className="font-medium text-sm text-purple-300 flex-1 text-left">
                      Администрирование
                    </span>
                    {adminMenuOpen ? (
                      <ChevronDown className="w-4 h-4 text-purple-300" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-purple-300" />
                    )}
                  </button>

                  {adminMenuOpen && (
                    <div className="mt-2 space-y-1 ml-4 border-l-2 border-purple-400/30 pl-2">
                      {adminMenuItems.map((item) => {
                        const Icon = item.icon;
                        const isActive = activeSection === item.id;

                        return (
                          <button
                            key={item.id}
                            onClick={() => handleItemClick(item.id)}
                            className={`
                              w-full flex items-center gap-3 px-4 py-2 rounded-lg
                              transition-all duration-200 group
                              ${isActive
                                ? 'bg-gradient-to-r from-purple-500/30 to-pink-500/30 border-l-2 border-purple-400'
                                : 'hover:bg-white/10 hover:translate-x-1'
                              }
                            `}
                          >
                            <Icon
                              className={`
                                w-4 h-4 transition-colors
                                ${isActive
                                  ? 'text-purple-300'
                                  : 'text-glass-text-secondary group-hover:text-purple-300'
                                }
                              `}
                            />
                            <span
                              className={`
                                font-medium text-xs
                                ${isActive
                                  ? 'text-purple-300'
                                  : 'text-glass-text-secondary group-hover:text-purple-300'
                                }
                              `}
                            >
                              {item.label}
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>
              ) : (
                <div className="mt-4 pt-4 border-t border-white/10">
                  <div className="text-xs text-red-300/50 px-4">
                    Debug: isAdmin = {String(isAdmin)}, role = {profile?.role || 'undefined'}
                  </div>
                </div>
              )}
            </nav>

          </GlassCard>
        </div>
      </aside>
    </>
  );
};
