import { useState, useRef, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';
import { useI18n } from '../contexts/I18nContext';
import { getFullName, getInitials } from '../utils/userDisplay';
import { Bell, Search, Sun, Moon, User, LogOut, Menu, X, Globe, Settings } from 'lucide-react';

type HeaderProps = {
  onMenuToggle: () => void;
  isMobileMenuOpen: boolean;
};

export const Header = ({ onMenuToggle, isMobileMenuOpen }: HeaderProps) => {
  const { profile, signOut } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const { locale, setLocale, availableLocales, t } = useI18n();
  const [showUserDropdown, setShowUserDropdown] = useState(false);
  const [showLangDropdown, setShowLangDropdown] = useState(false);
  const [langDropdownPosition, setLangDropdownPosition] = useState({ top: 0, right: 0 });
  const userButtonRef = useRef<HTMLDivElement>(null);
  const userDropdownRef = useRef<HTMLDivElement>(null);
  const langButtonRef = useRef<HTMLDivElement>(null);
  const langDropdownRef = useRef<HTMLDivElement>(null);

  // Calculate dropdown position for language selector
  useEffect(() => {
    if (showLangDropdown && langButtonRef.current) {
      const updatePosition = () => {
        if (langButtonRef.current) {
          const rect = langButtonRef.current.getBoundingClientRect();
          setLangDropdownPosition({
            top: rect.bottom + 8,
            right: window.innerWidth - rect.right,
          });
        }
      };
      
      updatePosition();
      window.addEventListener('resize', updatePosition);
      window.addEventListener('scroll', updatePosition, true);
      
      return () => {
        window.removeEventListener('resize', updatePosition);
        window.removeEventListener('scroll', updatePosition, true);
      };
    }
  }, [showLangDropdown]);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        userDropdownRef.current &&
        !userDropdownRef.current.contains(event.target as Node) &&
        userButtonRef.current &&
        !userButtonRef.current.contains(event.target as Node)
      ) {
        setShowUserDropdown(false);
      }
      if (
        langDropdownRef.current &&
        !langDropdownRef.current.contains(event.target as Node) &&
        langButtonRef.current &&
        !langButtonRef.current.contains(event.target as Node)
      ) {
        setShowLangDropdown(false);
      }
    };

    if (showUserDropdown || showLangDropdown) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => {
        document.removeEventListener('mousedown', handleClickOutside);
      };
    }
  }, [showUserDropdown, showLangDropdown]);

  const handleSignOut = async () => {
    await signOut();
    setShowUserDropdown(false);
  };

  const localeNames: Record<string, string> = {
    en: 'English',
    ru: 'Русский',
    ua: 'Українська',
  };

  return (
    <header className="oneui-header" style={{ width: '100%', maxWidth: '100%' }}>
      <div className="oneui-header-left flex-1 min-w-0">
            <button
              onClick={onMenuToggle}
          className="oneui-btn-icon lg:hidden"
          aria-label="Toggle menu"
        >
          {isMobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>

        <div className="min-w-0 flex-1">
          <h1 className="oneui-header-title truncate">{t('common.welcome')}</h1>
          <p className="oneui-header-subtitle hidden sm:block">{t('common.controlCenter')}</p>
        </div>
      </div>

      <div className="oneui-header-right flex-shrink-0">
        {/* Search */}
        <div className="hidden md:flex items-center relative">
          <Search className="absolute left-3 w-4 h-4 pointer-events-none" style={{ color: 'var(--oneui-text-muted)' }} />
          <input
            type="text"
            placeholder={t('common.search')}
            className="pl-10 pr-4 py-2 bg-transparent border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent w-48 lg:w-64"
            style={{
              backgroundColor: 'var(--oneui-bg-alt)',
              color: 'var(--oneui-text)',
              borderColor: 'var(--oneui-border)',
            }}
          />
        </div>

        {/* Language Selector */}
        <div className="oneui-dropdown" ref={langButtonRef}>
          <button
            onClick={() => setShowLangDropdown(!showLangDropdown)}
            className="oneui-btn-icon"
            title="Change language"
          >
            <Globe className="w-5 h-5" />
            </button>

          {showLangDropdown && (
            <>
              <div
                className="fixed inset-0 z-[90]"
                onClick={() => setShowLangDropdown(false)}
              />
              <div 
                ref={langDropdownRef} 
                className="oneui-dropdown-menu oneui-dropdown-menu-mobile" 
                style={{ 
                  position: 'fixed',
                  top: `${langDropdownPosition.top}px`,
                  right: `${Math.max(langDropdownPosition.right, 12)}px`,
                  left: 'auto',
                  zIndex: 10000,
                }}
              >
                {availableLocales.map((loc) => (
                  <div
                    key={loc}
                    onClick={() => {
                      setLocale(loc);
                      setShowLangDropdown(false);
                    }}
                    className={`oneui-dropdown-item ${locale === loc ? 'bg-indigo-50 dark:bg-indigo-900/20' : ''}`}
                  >
                    <span>{localeNames[loc]}</span>
                    {locale === loc && (
                      <span className="ml-auto text-indigo-600 dark:text-indigo-400">✓</span>
                    )}
              </div>
                ))}
              </div>
            </>
          )}
          </div>

        {/* Theme Toggle */}
            <button
              onClick={toggleTheme}
          className="oneui-btn-icon"
          title={t('header.switchTheme')}
            >
              {theme === 'dark' ? (
            <Sun className="w-5 h-5" />
              ) : (
            <Moon className="w-5 h-5" />
              )}
            </button>

        {/* Notifications */}
        <button className="oneui-btn-icon relative" title="Notifications">
          <Bell className="w-5 h-5" />
          <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
        </button>

        {/* User Menu */}
        <div className="oneui-dropdown" ref={userButtonRef}>
              <button
            onClick={() => setShowUserDropdown(!showUserDropdown)}
            className="flex items-center gap-2 p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
              >
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-sm font-semibold">
              {getInitials(profile)}
            </div>
            <div className="hidden sm:block text-left">
              <div className="text-xs sm:text-sm font-medium truncate max-w-[120px] lg:max-w-none" style={{ color: 'var(--oneui-text)' }}>
                {getFullName(profile)}
              </div>
              <div className="text-xs truncate max-w-[120px] lg:max-w-none" style={{ color: 'var(--oneui-text-muted)' }}>
                {profile?.role || 'user'}
                </div>
                </div>
              </button>

          {showUserDropdown && (
                <>
                  <div
                    className="fixed inset-0 z-[90]"
                onClick={() => setShowUserDropdown(false)}
                  />
              <div ref={userDropdownRef} className="oneui-dropdown-menu" style={{ right: 0, minWidth: '220px' }}>
                <div className="px-4 py-3 border-b" style={{ borderColor: 'var(--oneui-border)' }}>
                  <div className="text-sm font-medium" style={{ color: 'var(--oneui-text)' }}>
                    {getFullName(profile)}
                  </div>
                  <div className="text-xs mt-1" style={{ color: 'var(--oneui-text-muted)' }}>
                    {profile?.role || 'user'}
                  </div>
                </div>
                <div className="oneui-dropdown-item">
                  <User className="oneui-dropdown-item-icon" />
                  <span>{t('sidebar.settings')}</span>
                </div>
                <div className="oneui-dropdown-item" onClick={handleSignOut}>
                  <LogOut className="oneui-dropdown-item-icon" />
                  <span>{t('header.signOut')}</span>
                </div>
                  </div>
                </>
              )}
            </div>
          </div>
    </header>
  );
};
