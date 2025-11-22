import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { NavigationProvider } from '../contexts/NavigationContext';
import { Header } from '../components/Header';
import { Sidebar } from '../components/Sidebar';
import { CommandPalette } from '../components/CommandPalette';
import { Home } from '../components/sections/Home';
import { MissionControl } from '../components/sections/MissionControl';
import { UserDashboard } from '../components/sections/UserDashboard';
import { Modules } from '../components/sections/Modules';
import { ModulesHub } from '../components/sections/ModulesHub';
import { Users } from '../components/sections/Users';
import { Statistics } from '../components/sections/Statistics';
import { Logs } from '../components/sections/Logs';
import { Settings } from '../components/sections/Settings';
import { Docs } from '../components/sections/Docs';
import { Config } from '../components/sections/Config';
import { CoreManagement } from '../components/sections/CoreManagement';
import { Services } from '../components/sections/Services';
import { Monitoring } from '../components/sections/Monitoring';
import { Security } from '../components/sections/Security';
import { Notifications } from '../components/sections/Notifications';
import { Data } from '../components/sections/Data';
import { Support } from '../components/sections/Support';
import { Developer } from '../components/sections/Developer';
import { Terminal } from '../components/sections/Terminal';
import { CronJobs } from '../components/sections/CronJobs';
import { SecurityOperations } from '../components/sections/SecurityOperations';
import { DatabaseData } from '../components/sections/DatabaseData';
import { BroadcastStudio } from '../components/sections/BroadcastStudio';

const sections = {
  home: Home,
  missionControl: MissionControl,
  modules: Modules,
  modulesHub: ModulesHub,
  users: Users,
  statistics: Statistics,
  logs: Logs,
  settings: Settings,
  docs: Docs,
  config: Config,
  coreManagement: CoreManagement,
  services: Services,
  monitoring: Monitoring,
  security: Security,
  notifications: Notifications,
  data: Data,
  support: Support,
  developer: Developer,
  terminal: Terminal,
  cronJobs: CronJobs,
  securityOperations: SecurityOperations,
  databaseData: DatabaseData,
  broadcastStudio: BroadcastStudio,
};

export const Dashboard = () => {
  const { isAdmin } = useAuth();
  const [activeSection, setActiveSection] = useState('home');
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);

  // Command Palette hotkey (Ctrl+K or Cmd+K)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setIsCommandPaletteOpen(true);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // For regular users, show UserDashboard on home, for admins show Home
  const getActiveComponent = () => {
    if (activeSection === 'home') {
      return isAdmin ? Home : UserDashboard;
    }
    // Mission Control is admin-only
    if (activeSection === 'missionControl' && !isAdmin) {
      return UserDashboard;
    }
    return sections[activeSection as keyof typeof sections] || (isAdmin ? Home : UserDashboard);
  };

  const ActiveComponent = getActiveComponent();

  return (
    <NavigationProvider navigateTo={setActiveSection}>
      <div className="oneui-container">
      <Sidebar
        activeSection={activeSection}
        onSectionChange={setActiveSection}
        isMobileOpen={isMobileMenuOpen}
        onClose={() => setIsMobileMenuOpen(false)}
      />

        <div className="oneui-main">
        <Header
          onMenuToggle={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          isMobileMenuOpen={isMobileMenuOpen}
        />

          <main className="oneui-content">
          <ActiveComponent />
        </main>
        </div>
      </div>
      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
      />
    </NavigationProvider>
  );
};
