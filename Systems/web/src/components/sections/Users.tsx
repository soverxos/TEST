import { useEffect, useState } from 'react';
import { api, BotUser } from '../../api';
import { useAuth } from '../../contexts/AuthContext';
import { useI18n } from '../../contexts/I18nContext';
import { User, Shield, Ban, CheckCircle2, XCircle, Loader2, MoreVertical } from 'lucide-react';

export const Users = () => {
  const { isAdmin } = useAuth();
  const { t } = useI18n();
  const [users, setUsers] = useState<BotUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyUserIds, setBusyUserIds] = useState<number[]>([]);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    try {
      const data = await api.getUsers();
      setUsers(data || []);
    } catch (error) {
      console.error('Error loading users:', error);
      setError(t('users.errorToggle'));
    } finally {
      setLoading(false);
    }
  };

  const toggleBlockStatus = async (userId: number, currentStatus: boolean) => {
    if (!isAdmin) return;
    setBusyUserIds(prev => [...prev, userId]);
    setError(null);
    setMessage(null);
    try {
      await api.toggleUserBlockStatus(userId, !currentStatus);
      setUsers(prev => prev.map(u => (u.id === userId ? { ...u, is_blocked: !currentStatus } : u)));
      setMessage(!currentStatus 
        ? t('users.userBlocked', { id: userId })
        : t('users.userUnblocked', { id: userId })
      );
      setTimeout(() => setMessage(null), 5000);
    } catch (error) {
      console.error('Error toggling block status:', error);
      setError(t('users.errorToggle'));
      setTimeout(() => setError(null), 5000);
    } finally {
      setBusyUserIds(prev => prev.filter(id => id !== userId));
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="oneui-spinner"></div>
      </div>
    );
  }

  return (
    <div>
      {/* Page Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-2" style={{ color: 'var(--oneui-text)' }}>
          {t('users.title')}
        </h1>
        <p className="oneui-text-muted">{t('users.subtitle')}</p>
      </div>

      {/* Messages */}
      {error && (
        <div className="oneui-card mb-6 border-l-4" style={{ borderLeftColor: 'var(--oneui-danger)' }}>
          <div className="flex items-center gap-3 text-red-600 dark:text-red-400">
            <XCircle className="w-5 h-5" />
            <p className="font-medium">{error}</p>
          </div>
        </div>
      )}
      {message && (
        <div className="oneui-card mb-6 border-l-4" style={{ borderLeftColor: 'var(--oneui-success)' }}>
          <div className="flex items-center gap-3 text-green-600 dark:text-green-400">
            <CheckCircle2 className="w-5 h-5" />
            <p className="font-medium">{message}</p>
          </div>
        </div>
      )}

      {/* Users Table */}
      <div className="oneui-card">
        <div className="overflow-x-auto -mx-1.5 sm:mx-0">
          <table className="oneui-table min-w-full">
            <thead>
              <tr>
                <th>{t('users.userId')}</th>
                <th>Username</th>
                <th>{t('users.role')}</th>
                <th>{t('common.status')}</th>
                {isAdmin && <th>{t('common.actions')}</th>}
              </tr>
            </thead>
            <tbody>
              {users.map((user) => {
                const isBlocked = (user as never)['is_blocked'] || false;
                const roleColor = user.role === 'admin' ? 'oneui-badge-danger' : 
                                 user.role === 'moderator' ? 'oneui-badge-warning' : 
                                 'oneui-badge-info';

                return (
                  <tr key={user.id}>
                    <td>
                      <span className="font-mono font-semibold">#{user.id}</span>
                    </td>
                    <td>
                      <div className="flex items-center gap-2 sm:gap-3">
                        <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-xs sm:text-sm font-semibold flex-shrink-0">
                          {user.username?.[0]?.toUpperCase() || 'U'}
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="font-medium truncate" style={{ color: 'var(--oneui-text)' }}>
                            {user.username || `User ${user.id}`}
                          </div>
                          {user.username && (
                            <div className="text-xs oneui-text-muted truncate">@{user.username}</div>
                          )}
                        </div>
                      </div>
                    </td>
                    <td>
                      {user.role && (
                        <span className={`oneui-badge ${roleColor}`}>
                          {user.role.toUpperCase()}
                        </span>
                      )}
                    </td>
                    <td>
                      <span className={`oneui-badge ${isBlocked ? 'oneui-badge-danger' : 'oneui-badge-success'}`}>
                        {isBlocked ? t('common.inactive') : t('common.active')}
                      </span>
                    </td>
                    {isAdmin && (
                      <td>
                        <button
                          onClick={() => toggleBlockStatus(user.id, isBlocked)}
                          disabled={busyUserIds.includes(user.id)}
                          className={`oneui-btn ${isBlocked ? 'oneui-btn-primary' : 'oneui-btn-secondary'} flex items-center gap-1 sm:gap-2`}
                          style={{ padding: '0.375rem 0.5rem', fontSize: '0.75rem' }}
                        >
                          {busyUserIds.includes(user.id) ? (
                            <Loader2 className="w-3 h-3 sm:w-4 sm:h-4 animate-spin" />
                          ) : isBlocked ? (
                            <>
                              <CheckCircle2 className="w-3 h-3 sm:w-4 sm:h-4" />
                              <span className="hidden sm:inline">{t('users.unblockUser')}</span>
                            </>
                          ) : (
                            <>
                              <Ban className="w-3 h-3 sm:w-4 sm:h-4" />
                              <span className="hidden sm:inline">{t('users.blockUser')}</span>
                            </>
                          )}
                        </button>
                      </td>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {users.length === 0 && (
        <div className="oneui-card text-center py-12">
          <User className="w-16 h-16 mx-auto mb-4 oneui-text-muted opacity-50" />
          <h3 className="text-xl font-bold mb-2" style={{ color: 'var(--oneui-text)' }}>
            {t('users.noUsers')}
          </h3>
          <p className="oneui-text-muted">{t('users.noUsersDesc')}</p>
        </div>
      )}
    </div>
  );
};
