import { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { useI18n } from '../../contexts/I18nContext';
import { User, Shield, Save, CheckCircle2 } from 'lucide-react';

export const Settings = () => {
  const { profile } = useAuth();
  const { t } = useI18n();
  const [formData, setFormData] = useState({
    username: profile?.username || '',
  });
  const [saved, setSaved] = useState(false);
  const [notifications, setNotifications] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <div>
      {/* Page Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-2" style={{ color: 'var(--oneui-text)' }}>
          {t('sidebar.settings')}
        </h1>
        <p className="oneui-text-muted">Manage your account and preferences</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Profile Card */}
        <div className="oneui-card">
          <div className="text-center">
            <div className="w-24 h-24 mx-auto mb-4 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
              <User className="w-12 h-12 text-white" />
            </div>
            <h3 className="text-xl font-bold mb-1" style={{ color: 'var(--oneui-text)' }}>
              {profile?.username || 'User'}
            </h3>
            <p className="oneui-text-muted text-sm mb-4 capitalize">{profile?.role || 'user'}</p>
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full oneui-badge-danger">
              <Shield className="w-4 h-4" />
              <span className="text-xs font-semibold">{profile?.role?.toUpperCase() || 'USER'}</span>
            </div>
          </div>
        </div>

        {/* Profile Information */}
        <div className="lg:col-span-2">
          <div className="oneui-card">
            <div className="oneui-card-header">
              <h3 className="oneui-card-title">Profile Information</h3>
            </div>
            <form onSubmit={handleSave} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2" style={{ color: 'var(--oneui-text)' }}>
                  Username
                </label>
                <input
                  type="text"
                  value={formData.username}
                  onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                  className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  style={{
                    backgroundColor: 'var(--oneui-bg-alt)',
                    borderColor: 'var(--oneui-border)',
                    color: 'var(--oneui-text)',
                  }}
                  placeholder="Enter your username"
                />
              </div>

              <div className="flex items-center gap-3 pt-2">
                <button type="submit" className="oneui-btn oneui-btn-primary flex items-center gap-2">
                  <Save className="w-4 h-4" />
                  Save Changes
                </button>
                {saved && (
                  <div className="flex items-center gap-2 text-green-600 dark:text-green-400">
                    <CheckCircle2 className="w-5 h-5" />
                    <span className="text-sm font-medium">Settings saved!</span>
                  </div>
                )}
              </div>
            </form>
          </div>
        </div>
      </div>

      {/* Preferences */}
      <div className="oneui-card mt-6">
        <div className="oneui-card-header">
          <h3 className="oneui-card-title">Preferences</h3>
        </div>
        <div className="space-y-4">
          {[
            {
              label: 'Email Notifications',
              description: 'Receive email updates about bot activity',
              checked: notifications,
              onChange: setNotifications,
            },
            {
              label: 'Auto-refresh Dashboard',
              description: 'Automatically update dashboard data',
              checked: autoRefresh,
              onChange: setAutoRefresh,
            },
          ].map((pref) => (
            <div
              key={pref.label}
              className="flex items-center justify-between p-4 rounded-lg"
              style={{ backgroundColor: 'var(--oneui-bg-alt)' }}
            >
              <div className="flex-1">
                <p className="font-medium mb-1" style={{ color: 'var(--oneui-text)' }}>
                  {pref.label}
                </p>
                <p className="text-sm oneui-text-muted">{pref.description}</p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  className="sr-only peer"
                  checked={pref.checked}
                  onChange={(e) => pref.onChange(e.target.checked)}
                />
                <div className="w-11 h-6 bg-gray-300 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-indigo-300 dark:peer-focus:ring-indigo-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all dark:after:border-gray-600 peer-checked:bg-indigo-600"></div>
              </label>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
