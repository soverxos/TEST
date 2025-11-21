import { useState, useRef, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';
import { Zap, Sun, Moon, User, LogOut, Menu, X } from 'lucide-react';
import { GlassCard } from './ui/GlassCard';

type HeaderProps = {
  onMenuToggle: () => void;
  isMobileMenuOpen: boolean;
};

export const Header = ({ onMenuToggle, isMobileMenuOpen }: HeaderProps) => {
  const { profile, signOut } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const [showDropdown, setShowDropdown] = useState(false);
  const menuButtonRef = useRef<HTMLDivElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        menuButtonRef.current &&
        !menuButtonRef.current.contains(event.target as Node)
      ) {
        setShowDropdown(false);
      }
    };

    if (showDropdown) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => {
        document.removeEventListener('mousedown', handleClickOutside);
      };
    }
  }, [showDropdown]);

  const handleSignOut = async () => {
    await signOut();
    setShowDropdown(false);
  };

  return (
    <header className="sticky top-0 z-50 backdrop-blur-xl">
      <GlassCard className="m-4 p-4 overflow-visible">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={onMenuToggle}
              className="lg:hidden p-2 hover:bg-white/10 rounded-lg transition-colors"
            >
              {isMobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>

            <div className="flex items-center gap-3">
              <div className="logo-container">
                <Zap className="w-8 h-8" />
              </div>
              <div>
                <h1 className="logo-text text-xl font-bold">SwiftDevBot</h1>
                <p className="text-xs text-glass-text-secondary">Control Center</p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={toggleTheme}
              className="p-2 hover:bg-white/10 rounded-lg transition-all hover:scale-110"
              title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
            >
              {theme === 'dark' ? (
                <Sun className="w-5 h-5 text-yellow-400" />
              ) : (
                <Moon className="w-5 h-5 text-blue-600" />
              )}
            </button>

            <div className="relative" ref={menuButtonRef}>
              <button
                onClick={() => setShowDropdown(!showDropdown)}
                className="flex items-center gap-3 p-2 hover:bg-white/10 rounded-lg transition-colors"
              >
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-cyan-400 to-purple-500 flex items-center justify-center">
                  <User className="w-5 h-5 text-white" />
                </div>
                <div className="hidden md:block text-left">
                  <p className="text-sm font-medium text-glass-text">{profile?.username}</p>
                  <p className="text-xs text-glass-text-secondary capitalize">{profile?.role}</p>
                </div>
              </button>

              {showDropdown && (
                <>
                  <div
                    className="fixed inset-0 z-[90]"
                    onClick={() => setShowDropdown(false)}
                  />
                  <div 
                    ref={dropdownRef}
                    className="absolute right-0 mt-2 w-48 z-[100]"
                    style={{
                      position: 'absolute',
                      top: '100%',
                      right: 0,
                    }}
                  >
                    <GlassCard className="p-2 shadow-2xl">
                      <button
                        onClick={handleSignOut}
                        className="w-full flex items-center gap-2 px-3 py-2 text-sm text-glass-text hover:bg-white/10 rounded-lg transition-colors"
                      >
                        <LogOut className="w-4 h-4" />
                        Sign Out
                      </button>
                    </GlassCard>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </GlassCard>
    </header>
  );
};
