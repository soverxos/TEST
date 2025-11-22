import { useI18n } from '../../contexts/I18nContext';
import { BookOpen, Code, Rocket, Shield, Zap, ExternalLink } from 'lucide-react';

export const Docs = () => {
  const { t } = useI18n();
  const sections = [
    {
      icon: Rocket,
      title: 'Getting Started',
      description: 'Quick start guide to set up and configure your bot',
      color: 'oneui-stat-icon-primary',
      link: '#',
    },
    {
      icon: Code,
      title: 'API Reference',
      description: 'Complete documentation of available API endpoints',
      color: 'oneui-stat-icon-success',
      link: '#',
    },
    {
      icon: Zap,
      title: 'Module Development',
      description: 'Learn how to create custom modules for your bot',
      color: 'oneui-stat-icon-warning',
      link: '#',
    },
    {
      icon: Shield,
      title: 'Security Best Practices',
      description: 'Guidelines for keeping your bot secure',
      color: 'oneui-stat-icon-danger',
      link: '#',
    },
  ];

  return (
    <div>
      {/* Page Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-2" style={{ color: 'var(--oneui-text)' }}>
          Documentation
        </h1>
        <p className="oneui-text-muted">Learn how to use and customize SwiftDevBot</p>
      </div>

      {/* Documentation Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        {sections.map((section) => {
          const Icon = section.icon;
          return (
            <div
              key={section.title}
              className="oneui-card hover:shadow-lg transition-all cursor-pointer group"
            >
              <div className="flex items-start gap-4">
                <div className={`${section.color} oneui-stat-icon flex-shrink-0`}>
                  <Icon className="w-6 h-6" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-lg font-bold" style={{ color: 'var(--oneui-text)' }}>
                      {section.title}
                    </h3>
                    <ExternalLink className="w-4 h-4 oneui-text-muted group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors" />
                  </div>
                  <p className="oneui-text-muted text-sm">{section.description}</p>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* About Section */}
      <div className="oneui-card">
        <div className="flex items-start gap-4">
          <div className="oneui-stat-icon oneui-stat-icon-primary flex-shrink-0">
            <BookOpen className="w-6 h-6" />
          </div>
          <div className="flex-1">
            <h3 className="text-xl font-bold mb-4" style={{ color: 'var(--oneui-text)' }}>
              About SwiftDevBot
            </h3>
            <div className="space-y-4 oneui-text-muted">
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
      </div>
    </div>
  );
};
