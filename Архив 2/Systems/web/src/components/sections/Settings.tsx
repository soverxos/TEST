import { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { GlassCard } from '../ui/GlassCard';
import { GlassInput } from '../ui/GlassInput';
import { GlassButton } from '../ui/GlassButton';
import { User, Shield } from 'lucide-react';

export const Settings = () => {
  const { profile } = useAuth();
  const [formData, setFormData] = useState({
    username: profile?.username || '',
  });
  const [saved, setSaved] = useState(false);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-glass-text mb-2">Settings</h2>
        <p className="text-glass-text-secondary">Manage your account and preferences</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <GlassCard className="p-6 text-center" hover>
          <div className="w-24 h-24 mx-auto mb-4 rounded-full bg-gradient-to-br from-cyan-400 to-purple-500 flex items-center justify-center">
            <User className="w-12 h-12 text-white" />
          </div>
          <h3 className="text-xl font-bold text-glass-text mb-1">{profile?.username}</h3>
          <p className="text-glass-text-secondary text-sm mb-3 capitalize">{profile?.role}</p>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-purple-500/20 text-purple-300 text-sm font-semibold">
            <Shield className="w-4 h-4" />
            {profile?.role?.toUpperCase()}
          </div>
        </GlassCard>

        <div className="lg:col-span-2">
          <GlassCard className="p-6" glow>
            <h3 className="text-xl font-bold text-glass-text mb-6">Profile Information</h3>
            <form onSubmit={handleSave} className="space-y-4">
              <GlassInput
                label="Username"
                type="text"
                value={formData.username}
                onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                placeholder="Enter your username"
              />

              <div className="flex items-center gap-3 pt-4">
                <GlassButton type="submit" variant="primary">
                  Save Changes
                </GlassButton>
                {saved && (
                  <span className="text-green-400 text-sm font-medium">Settings saved!</span>
                )}
              </div>
            </form>
          </GlassCard>
        </div>
      </div>

      <GlassCard className="p-6">
        <h3 className="text-xl font-bold text-glass-text mb-4">Preferences</h3>
        <div className="space-y-4">
          {[
            { label: 'Email Notifications', description: 'Receive email updates about bot activity' },
            { label: 'Auto-refresh Dashboard', description: 'Automatically update dashboard data' },
            { label: 'Dark Mode by Default', description: 'Always start with dark theme' },
          ].map((pref) => (
            <div key={pref.label} className="flex items-center justify-between p-4 rounded-lg bg-white/5">
              <div>
                <p className="text-glass-text font-medium">{pref.label}</p>
                <p className="text-glass-text-secondary text-sm">{pref.description}</p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input type="checkbox" className="sr-only peer" defaultChecked />
                <div className="w-11 h-6 bg-white/20 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-cyan-500"></div>
              </label>
            </div>
          ))}
        </div>
      </GlassCard>
    </div>
  );
};
