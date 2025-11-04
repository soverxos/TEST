import { useEffect, useState } from 'react';
import { api, BotUser } from '../../lib/api';
import { useAuth } from '../../contexts/AuthContext';
import { GlassCard } from '../ui/GlassCard';
import { GlassButton } from '../ui/GlassButton';
import { User, Shield, Ban } from 'lucide-react';

export const Users = () => {
  const { isAdmin } = useAuth();
  const [users, setUsers] = useState<BotUser[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    try {
      const data = await api.getUsers();
      setUsers(data || []);
    } catch (error) {
      console.error('Error loading users:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleBlockStatus = async (userId: number, currentStatus: boolean) => {
    if (!isAdmin) return;

    // TODO: Implement user block/unblock API endpoint
    setUsers(users.map(u => u.id === userId ? { ...u, is_blocked: !currentStatus } : u));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="loading-spinner"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-glass-text mb-2">Bot Users</h2>
        <p className="text-glass-text-secondary">Manage users interacting with your bot</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {users.map((user) => (
          <GlassCard key={user.id} hover className="p-6">
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-full bg-gradient-to-br from-cyan-400 to-purple-500 flex items-center justify-center">
                  {user.avatar ? (
                    <span className="text-white font-semibold">{user.avatar}</span>
                  ) : (
                    <User className="w-6 h-6 text-white" />
                  )}
                </div>
                <div>
                  <h3 className="font-bold text-glass-text">{user.username || `User ${user.id}`}</h3>
                  {user.username && (
                    <p className="text-sm text-glass-text-secondary">@{user.username}</p>
                  )}
                </div>
              </div>
              {(user as never)['is_blocked'] ? (
                <Ban className="w-5 h-5 text-red-400" />
              ) : (
                <Shield className="w-5 h-5 text-green-400" />
              )}
            </div>

            <div className="space-y-2 mb-4">
              <div className="flex items-center justify-between text-sm">
                <span className="text-glass-text-secondary">ID</span>
                <span className="text-glass-text font-mono">{user.id}</span>
              </div>
              {user.role && (
                <div className="flex items-center justify-between text-sm">
                  <span className="text-glass-text-secondary">Role</span>
                  <span className="text-glass-text font-semibold capitalize">{user.role}</span>
                </div>
              )}
            </div>

            {isAdmin && (
              <GlassButton
                variant={(user as never)['is_blocked'] ? 'primary' : 'danger'}
                size="sm"
                className="w-full"
                onClick={() => toggleBlockStatus(user.id, (user as never)['is_blocked'] || false)}
              >
                {(user as never)['is_blocked'] ? 'Unblock User' : 'Block User'}
              </GlassButton>
            )}
          </GlassCard>
        ))}
      </div>

      {users.length === 0 && (
        <GlassCard className="p-12 text-center">
          <User className="w-16 h-16 mx-auto mb-4 text-glass-text-secondary" />
          <h3 className="text-xl font-bold text-glass-text mb-2">No users yet</h3>
          <p className="text-glass-text-secondary">Users will appear here once they interact with your bot</p>
        </GlassCard>
      )}
    </div>
  );
};
