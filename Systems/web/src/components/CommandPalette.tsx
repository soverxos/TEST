import { useEffect, useState, useRef } from 'react';
import { useNavigation } from '../contexts/NavigationContext';
import { Search, Command, ArrowRight } from 'lucide-react';

type CommandItem = {
  id: string;
  label: string;
  description: string;
  action: () => void;
  category: string;
  keywords: string[];
};

export const CommandPalette = ({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) => {
  const { navigateTo } = useNavigation();
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const commands: CommandItem[] = [
    { id: 'mission-control', label: 'Mission Control', description: 'Open real-time monitoring dashboard', action: () => navigateTo('missionControl'), category: 'Navigation', keywords: ['mission', 'control', 'monitoring', 'dashboard'] },
    { id: 'users', label: 'User Management', description: 'Manage users and permissions', action: () => navigateTo('users'), category: 'Navigation', keywords: ['users', 'user', 'manage'] },
    { id: 'modules', label: 'Modules', description: 'Manage bot modules', action: () => navigateTo('modules'), category: 'Navigation', keywords: ['modules', 'module', 'plugins'] },
    { id: 'core-management', label: 'Core Management', description: 'Configure core settings and services', action: () => navigateTo('coreManagement'), category: 'Navigation', keywords: ['core', 'config', 'settings', 'services'] },
    { id: 'logs', label: 'View Logs', description: 'Open system logs viewer', action: () => navigateTo('logs'), category: 'Navigation', keywords: ['logs', 'log', 'view'] },
    { id: 'terminal', label: 'Terminal', description: 'Open web terminal', action: () => navigateTo('terminal'), category: 'Tools', keywords: ['terminal', 'console', 'shell'] },
    { id: 'restart-bot', label: 'Restart Bot', description: 'Restart the bot process', action: () => { console.log('Restart bot'); onClose(); }, category: 'Actions', keywords: ['restart', 'reboot', 'bot'] },
    { id: 'clear-cache', label: 'Clear Cache', description: 'Clear Redis cache', action: () => { console.log('Clear cache'); onClose(); }, category: 'Actions', keywords: ['clear', 'cache', 'redis'] },
  ];

  const filteredCommands = query
    ? commands.filter(cmd =>
        cmd.label.toLowerCase().includes(query.toLowerCase()) ||
        cmd.description.toLowerCase().includes(query.toLowerCase()) ||
        cmd.keywords.some(k => k.toLowerCase().includes(query.toLowerCase()))
      )
    : commands;

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;

      if (e.key === 'Escape') {
        onClose();
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex(prev => Math.min(prev + 1, filteredCommands.length - 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex(prev => Math.max(prev - 1, 0));
      } else if (e.key === 'Enter' && filteredCommands[selectedIndex]) {
        e.preventDefault();
        filteredCommands[selectedIndex].action();
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, selectedIndex, filteredCommands, onClose]);

  if (!isOpen) return null;

  return (
    <>
      <div
        className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50"
        onClick={onClose}
      />
      <div
        className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-2xl z-50"
        style={{ maxHeight: '80vh' }}
      >
        <div className="oneui-card shadow-2xl">
          <div className="flex items-center gap-3 mb-4">
            <Search className="w-5 h-5" style={{ color: 'var(--oneui-text-muted)' }} />
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Type a command or search..."
              className="flex-1 bg-transparent border-none outline-none text-lg"
              style={{ color: 'var(--oneui-text)' }}
            />
            <div className="flex items-center gap-1 px-2 py-1 rounded text-xs" style={{ backgroundColor: 'var(--oneui-bg-alt)' }}>
              <Command className="w-3 h-3" />
              <span>K</span>
            </div>
          </div>

          <div className="max-h-96 overflow-y-auto">
            {filteredCommands.length === 0 ? (
              <div className="text-center py-8 oneui-text-muted">
                No commands found
              </div>
            ) : (
              <div className="space-y-1">
                {filteredCommands.map((cmd, index) => (
                  <button
                    key={cmd.id}
                    onClick={() => {
                      cmd.action();
                      onClose();
                    }}
                    className={`w-full text-left p-3 rounded-lg flex items-center justify-between transition-colors ${
                      index === selectedIndex
                        ? 'bg-indigo-500/20 border border-indigo-500/50'
                        : 'hover:bg-gray-100 dark:hover:bg-gray-800'
                    }`}
                    onMouseEnter={() => setSelectedIndex(index)}
                  >
                    <div className="flex-1">
                      <div className="font-medium mb-1" style={{ color: 'var(--oneui-text)' }}>
                        {cmd.label}
                      </div>
                      <div className="text-sm oneui-text-muted">{cmd.description}</div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs px-2 py-1 rounded" style={{ backgroundColor: 'var(--oneui-bg-alt)' }}>
                        {cmd.category}
                      </span>
                      <ArrowRight className="w-4 h-4 oneui-text-muted" />
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
};

