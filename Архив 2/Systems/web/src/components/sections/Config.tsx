import { useState } from 'react';
import { GlassCard } from '../ui/GlassCard';
import { GlassInput } from '../ui/GlassInput';
import { GlassButton } from '../ui/GlassButton';
import { Sliders, Database, Key, Globe } from 'lucide-react';

export const Config = () => {
  const [config, setConfig] = useState({
    botToken: '••••••••••••••••••••',
    apiUrl: 'https://api.telegram.org',
    webhookUrl: 'https://your-domain.com/webhook',
    maxRetries: '3',
    timeout: '30',
  });

  const [saved, setSaved] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  const configSections = [
    {
      icon: Key,
      title: 'Authentication',
      fields: [
        { key: 'botToken', label: 'Bot Token', type: 'password' },
      ],
    },
    {
      icon: Globe,
      title: 'API Configuration',
      fields: [
        { key: 'apiUrl', label: 'API URL', type: 'text' },
        { key: 'webhookUrl', label: 'Webhook URL', type: 'text' },
      ],
    },
    {
      icon: Sliders,
      title: 'Performance',
      fields: [
        { key: 'maxRetries', label: 'Max Retries', type: 'number' },
        { key: 'timeout', label: 'Timeout (seconds)', type: 'number' },
      ],
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-glass-text mb-2">Core Configuration</h2>
        <p className="text-glass-text-secondary">Manage bot's core settings and parameters</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {[
          { icon: Database, label: 'Database', value: 'Connected', color: 'text-green-400' },
          { icon: Key, label: 'API Status', value: 'Active', color: 'text-cyan-400' },
          { icon: Globe, label: 'Webhook', value: 'Running', color: 'text-purple-400' },
        ].map((status) => {
          const Icon = status.icon;
          return (
            <GlassCard key={status.label} hover className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-glass-text-secondary text-sm mb-1">{status.label}</p>
                  <p className={`text-xl font-bold ${status.color}`}>{status.value}</p>
                </div>
                <Icon className={`w-8 h-8 ${status.color}`} />
              </div>
            </GlassCard>
          );
        })}
      </div>

      <form onSubmit={handleSave} className="space-y-6">
        {configSections.map((section) => {
          const Icon = section.icon;
          return (
            <GlassCard key={section.title} className="p-6" glow>
              <div className="flex items-center gap-3 mb-6">
                <div className="p-2 rounded-lg bg-cyan-500/20">
                  <Icon className="w-5 h-5 text-cyan-400" />
                </div>
                <h3 className="text-xl font-bold text-glass-text">{section.title}</h3>
              </div>
              <div className="space-y-4">
                {section.fields.map((field) => (
                  <GlassInput
                    key={field.key}
                    label={field.label}
                    type={field.type}
                    value={config[field.key as keyof typeof config]}
                    onChange={(e) => setConfig({ ...config, [field.key]: e.target.value })}
                  />
                ))}
              </div>
            </GlassCard>
          );
        })}

        <div className="flex items-center gap-3">
          <GlassButton type="submit" variant="primary" size="lg">
            Save Configuration
          </GlassButton>
          {saved && (
            <span className="text-green-400 text-sm font-medium">Configuration saved!</span>
          )}
        </div>
      </form>
    </div>
  );
};
