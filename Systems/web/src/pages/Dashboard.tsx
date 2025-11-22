import { useState } from 'react';
import { Header } from '../components/Header';
import { Sidebar } from '../components/Sidebar';
import { Home } from '../components/sections/Home';
import { Modules } from '../components/sections/Modules';
import { Users } from '../components/sections/Users';
import { Statistics } from '../components/sections/Statistics';
import { Logs } from '../components/sections/Logs';
import { Settings } from '../components/sections/Settings';
import { Docs } from '../components/sections/Docs';
import { Config } from '../components/sections/Config';
import { Services } from '../components/sections/Services';
import { Monitoring } from '../components/sections/Monitoring';

const sections = {
  home: Home,
  modules: Modules,
  users: Users,
  statistics: Statistics,
  logs: Logs,
  settings: Settings,
  docs: Docs,
  config: Config,
  services: Services,
  monitoring: Monitoring,
};

export const Dashboard = () => {
  const [activeSection, setActiveSection] = useState('home');
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const ActiveComponent = sections[activeSection as keyof typeof sections] || Home;

  return (
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
  );
};
