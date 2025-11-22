import { useState, useEffect } from 'react';
import { useI18n } from '../../contexts/I18nContext';
import { api, Session } from '../../api';
import { Shield, Lock, Monitor, History, LogOut, CheckCircle2, XCircle } from 'lucide-react';

export const Security = () => {
  const { t } = useI18n();
  const [showChangePassword, setShowChangePassword] = useState(false);
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadSessions();
  }, []);

  const loadSessions = async () => {
    try {
      const data = await api.getSessions();
      setSessions(data);
    } catch (error) {
      console.error('Error loading sessions:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleTerminateSession = async (sessionId: string) => {
    try {
      await api.terminateSession(sessionId);
      await loadSessions();
    } catch (error: any) {
      console.error('Error terminating session:', error);
      alert(`Failed to terminate session: ${error.message || error}`);
    }
  };

  const handleTerminateAll = async () => {
    if (!confirm(t('security.confirmTerminateAll'))) return;
    try {
      for (const session of sessions) {
        if (!session.current) {
          await api.terminateSession(session.id);
        }
      }
      await loadSessions();
    } catch (error: any) {
      console.error('Error terminating all sessions:', error);
      alert(`Failed to terminate sessions: ${error.message || error}`);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      alert(t('security.passwordsDoNotMatch'));
      return;
    }
    if (newPassword.length < 8) {
      alert(t('security.passwordTooShort'));
      return;
    }
    try {
      await api.setupCloudPassword(newPassword);
      alert(t('security.passwordChanged'));
      setShowChangePassword(false);
      setNewPassword('');
      setConfirmPassword('');
    } catch (error: any) {
      console.error('Error changing password:', error);
      alert(`Failed to change password: ${error.message || error}`);
    }
  };

  return (
    <div>
      {/* Page Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-2" style={{ color: 'var(--oneui-text)' }}>
          {t('security.title')}
        </h1>
        <p className="oneui-text-muted">{t('security.subtitle')}</p>
      </div>

      {/* Cloud Password */}
      <div className="oneui-card mb-6">
        <div className="oneui-card-header">
          <div className="flex items-center gap-3">
            <div className="oneui-stat-icon oneui-stat-icon-primary">
              <Lock className="w-5 h-5" />
            </div>
            <h3 className="oneui-card-title">{t('security.cloudPassword')}</h3>
          </div>
        </div>
        <div className="space-y-4">
          <p className="text-sm oneui-text-muted">
            Облачный пароль используется для дополнительной защиты доступа к веб-панели.
          </p>
          {!showChangePassword ? (
            <button
              onClick={() => setShowChangePassword(true)}
              className="oneui-btn oneui-btn-primary"
            >
              {t('security.changePassword')}
            </button>
          ) : (
            <form onSubmit={handleChangePassword} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2" style={{ color: 'var(--oneui-text)' }}>
                  Новый пароль
                </label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  style={{
                    backgroundColor: 'var(--oneui-bg-alt)',
                    borderColor: 'var(--oneui-border)',
                    color: 'var(--oneui-text)',
                  }}
                  minLength={8}
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2" style={{ color: 'var(--oneui-text)' }}>
                  Подтвердите пароль
                </label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  style={{
                    backgroundColor: 'var(--oneui-bg-alt)',
                    borderColor: 'var(--oneui-border)',
                    color: 'var(--oneui-text)',
                  }}
                  minLength={8}
                  required
                />
              </div>
              <div className="flex gap-3">
                <button type="submit" className="oneui-btn oneui-btn-primary">
                  {t('common.save')}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowChangePassword(false);
                    setNewPassword('');
                    setConfirmPassword('');
                  }}
                  className="oneui-btn oneui-btn-secondary"
                >
                  {t('common.cancel')}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>

      {/* Active Sessions */}
      <div className="oneui-card mb-6">
        <div className="oneui-card-header">
          <div className="flex items-center justify-between w-full">
            <div className="flex items-center gap-3">
              <div className="oneui-stat-icon oneui-stat-icon-success">
                <Monitor className="w-5 h-5" />
              </div>
              <h3 className="oneui-card-title">{t('security.activeSessions')}</h3>
            </div>
            <button 
              onClick={handleTerminateAll}
              className="oneui-btn oneui-btn-secondary text-sm"
              disabled={sessions.filter(s => !s.current).length === 0}
            >
              {t('security.terminateAll')}
            </button>
          </div>
        </div>
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <div className="oneui-spinner"></div>
          </div>
        ) : sessions.length === 0 ? (
          <div className="text-center py-8 text-sm oneui-text-muted">
            {t('security.noSessions')}
          </div>
        ) : (
          <div className="space-y-3">
            {sessions.map((session) => (
            <div
              key={session.id}
              className="p-4 rounded-lg border"
              style={{
                backgroundColor: session.current ? 'rgba(99, 102, 241, 0.05)' : 'var(--oneui-bg-alt)',
                borderColor: 'var(--oneui-border)',
              }}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="font-medium" style={{ color: 'var(--oneui-text)' }}>
                      {session.device}
                    </span>
                    {session.current && (
                      <span className="oneui-badge oneui-badge-success text-xs">
                        {t('security.currentSession')}
                      </span>
                    )}
                  </div>
                  <div className="space-y-1 text-sm oneui-text-muted">
                    <div className="flex items-center gap-2">
                      <span>{t('security.location')}:</span>
                      <span>{session.location}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span>{t('security.lastActivity')}:</span>
                      <span>{session.lastActivity}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span>IP:</span>
                      <span className="font-mono">{session.ip}</span>
                    </div>
                  </div>
                </div>
                {!session.current && (
                  <button 
                    onClick={() => handleTerminateSession(session.id)}
                    className="oneui-btn oneui-btn-secondary text-sm"
                  >
                    {t('security.terminateSession')}
                  </button>
                )}
              </div>
            </div>
          ))}
          </div>
        )}
      </div>

      {/* Session History */}
      <div className="oneui-card">
        <div className="oneui-card-header">
          <div className="flex items-center gap-3">
            <div className="oneui-stat-icon oneui-stat-icon-primary">
              <History className="w-5 h-5" />
            </div>
            <h3 className="oneui-card-title">{t('security.sessionHistory')}</h3>
          </div>
        </div>
        <div className="text-sm oneui-text-muted">
          <p>История входов в веб-панель будет отображаться здесь.</p>
        </div>
      </div>
    </div>
  );
};

