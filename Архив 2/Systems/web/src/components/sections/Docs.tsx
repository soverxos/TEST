import { GlassCard } from '../ui/GlassCard';
import { BookOpen, Code, Rocket, Shield, Zap } from 'lucide-react';

export const Docs = () => {
  const sections = [
    {
      icon: Rocket,
      title: 'Getting Started',
      description: 'Quick start guide to set up and configure your bot',
      color: 'from-cyan-400 to-blue-500',
    },
    {
      icon: Code,
      title: 'API Reference',
      description: 'Complete documentation of available API endpoints',
      color: 'from-purple-400 to-pink-500',
    },
    {
      icon: Zap,
      title: 'Module Development',
      description: 'Learn how to create custom modules for your bot',
      color: 'from-green-400 to-emerald-500',
    },
    {
      icon: Shield,
      title: 'Security Best Practices',
      description: 'Guidelines for keeping your bot secure',
      color: 'from-orange-400 to-red-500',
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-glass-text mb-2">Documentation</h2>
        <p className="text-glass-text-secondary">Learn how to use and customize SwiftDevBot</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {sections.map((section) => {
          const Icon = section.icon;
          return (
            <GlassCard key={section.title} hover glow className="p-6 cursor-pointer">
              <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${section.color} flex items-center justify-center mb-4`}>
                <Icon className="w-6 h-6 text-white" />
              </div>
              <h3 className="text-xl font-bold text-glass-text mb-2">{section.title}</h3>
              <p className="text-glass-text-secondary">{section.description}</p>
            </GlassCard>
          );
        })}
      </div>

      <GlassCard className="p-8" glow>
        <div className="flex items-start gap-4">
          <BookOpen className="w-8 h-8 text-cyan-400 flex-shrink-0" />
          <div>
            <h3 className="text-2xl font-bold text-glass-text mb-4">About SwiftDevBot</h3>
            <div className="space-y-4 text-glass-text-secondary">
              <p>
                SwiftDevBot is a powerful, modular Telegram bot designed for developers.
                It provides a comprehensive set of tools and features to streamline your
                development workflow.
              </p>
              <p>
                The bot is built with modern technologies and follows best practices for
                security, scalability, and maintainability. Each module can be independently
                activated or deactivated based on your needs.
              </p>
              <p>
                This dashboard provides full control over your bot's functionality,
                allowing you to monitor activity, manage users, and configure settings
                in real-time.
              </p>
            </div>
          </div>
        </div>
      </GlassCard>
    </div>
  );
};
