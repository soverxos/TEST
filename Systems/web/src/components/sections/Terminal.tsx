import { useState, useRef, useEffect } from 'react';
import { useI18n } from '../../contexts/I18nContext';
import { Terminal as TerminalIcon, Send, Trash2, ChevronUp } from 'lucide-react';

type CommandHistoryItem = {
  id: string;
  command: string;
  output: string;
  timestamp: Date;
};

export const Terminal = () => {
  const { t } = useI18n();
  const [command, setCommand] = useState('');
  const [history, setHistory] = useState<CommandHistoryItem[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const terminalRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [history]);

  const executeCommand = async () => {
    if (!command.trim()) return;

    const commandText = command.trim();
    
    // Add command to history immediately (with loading state)
    const loadingItem: CommandHistoryItem = {
      id: Date.now().toString(),
      command: commandText,
      output: 'Executing...',
      timestamp: new Date(),
    };
    setHistory([...history, loadingItem]);
    setCommand('');
    setHistoryIndex(-1);

    try {
      const { api } = await import('../../api');
      const result = await api.executeTerminalCommand(commandText);
      
      // Update the last item with actual result
      setHistory(prev => {
        const updated = [...prev];
        const lastIndex = updated.length - 1;
        if (lastIndex >= 0 && updated[lastIndex].id === loadingItem.id) {
          updated[lastIndex] = {
            ...updated[lastIndex],
            output: result.output,
            timestamp: new Date(result.timestamp),
          };
        }
        return updated;
      });
    } catch (error: any) {
      // Update with error
      setHistory(prev => {
        const updated = [...prev];
        const lastIndex = updated.length - 1;
        if (lastIndex >= 0 && updated[lastIndex].id === loadingItem.id) {
          updated[lastIndex] = {
            ...updated[lastIndex],
            output: `Error: ${error.message || 'Failed to execute command'}`,
          };
        }
        return updated;
      });
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      executeCommand();
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (history.length > 0) {
        const newIndex = historyIndex === -1 ? history.length - 1 : Math.max(0, historyIndex - 1);
        setHistoryIndex(newIndex);
        setCommand(history[newIndex].command);
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (historyIndex >= 0) {
        const newIndex = historyIndex + 1;
        if (newIndex >= history.length) {
          setHistoryIndex(-1);
          setCommand('');
        } else {
          setHistoryIndex(newIndex);
          setCommand(history[newIndex].command);
        }
      }
    }
  };

  const clearHistory = () => {
    setHistory([]);
    setCommand('');
  };

  return (
    <div>
      {/* Page Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-2" style={{ color: 'var(--oneui-text)' }}>
          {t('terminal.title')}
        </h1>
        <p className="oneui-text-muted">{t('terminal.subtitle')}</p>
      </div>

      {/* Terminal */}
      <div className="oneui-card">
        <div className="oneui-card-header">
          <div className="flex items-center justify-between w-full">
            <div className="flex items-center gap-3">
              <div className="oneui-stat-icon oneui-stat-icon-primary">
                <TerminalIcon className="w-5 h-5" />
              </div>
              <h3 className="oneui-card-title">SwiftDevBot Terminal</h3>
            </div>
            <button onClick={clearHistory} className="oneui-btn oneui-btn-secondary text-sm">
              <Trash2 className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Terminal Output */}
        <div
          ref={terminalRef}
          className="h-96 overflow-y-auto p-4 font-mono text-sm rounded-lg"
          style={{
            backgroundColor: '#1a1a1a',
            color: '#00ff00',
            fontFamily: 'monospace',
          }}
        >
          {history.length === 0 ? (
            <div className="oneui-text-muted">
              {t('terminal.noHistory')}
              <br />
              <span className="text-xs">Type a command and press Enter to execute.</span>
            </div>
          ) : (
            history.map((item) => (
              <div key={item.id} className="mb-4">
                <div className="mb-1">
                  <span style={{ color: '#00ff00' }}>$ </span>
                  <span style={{ color: '#ffffff' }}>{item.command}</span>
                </div>
                <div className="ml-4 text-gray-300 whitespace-pre-wrap">{item.output}</div>
                <div className="text-xs text-gray-500 mt-1">
                  {item.timestamp.toLocaleTimeString()}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Terminal Input */}
        <div className="mt-4 flex gap-2">
          <div className="flex-1 relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-green-400 font-mono">$</span>
            <input
              ref={inputRef}
              type="text"
              value={command}
              onChange={(e) => setCommand(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={t('terminal.placeholder')}
              className="w-full pl-8 pr-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono"
              style={{
                backgroundColor: 'var(--oneui-bg-alt)',
                borderColor: 'var(--oneui-border)',
                color: 'var(--oneui-text)',
              }}
            />
          </div>
          <button onClick={executeCommand} className="oneui-btn oneui-btn-primary">
            <Send className="w-4 h-4" />
          </button>
        </div>

        {/* Help */}
        <div className="mt-4 p-3 rounded-lg text-xs" style={{ backgroundColor: 'var(--oneui-bg-alt)' }}>
          <p className="oneui-text-muted mb-2">
            <strong>Tips:</strong> Use ↑/↓ arrows to navigate command history. Commands are executed as if sent to the bot.
          </p>
        </div>
      </div>
    </div>
  );
};

