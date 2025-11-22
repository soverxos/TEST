import { useState, useEffect } from 'react';
import { useI18n } from '../../contexts/I18nContext';
import { api, Broadcast, BroadcastProgress } from '../../api';
import { Send, Clock, Users, Filter, History, Play, Calendar, AlertCircle, CheckCircle2, XCircle } from 'lucide-react';

export const BroadcastStudio = () => {
  const { t } = useI18n();
  const [activeTab, setActiveTab] = useState<'create' | 'history'>('create');
  const [message, setMessage] = useState('');
  const [targetType, setTargetType] = useState<'all' | 'admins' | 'active' | 'language'>('all');
  const [targetValue, setTargetValue] = useState<string>('');
  const [scheduleTime, setScheduleTime] = useState<string>('');
  const [sending, setSending] = useState(false);
  const [broadcasts, setBroadcasts] = useState<Broadcast[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeBroadcastId, setActiveBroadcastId] = useState<string | null>(null);
  const [progress, setProgress] = useState<BroadcastProgress | null>(null);

  useEffect(() => {
    if (activeTab === 'history') {
      loadBroadcasts();
    }
  }, [activeTab]);

  useEffect(() => {
    if (activeBroadcastId) {
      const interval = setInterval(async () => {
        try {
          const prog = await api.getBroadcastProgress(activeBroadcastId);
          setProgress(prog);
          if (prog.status === 'completed' || prog.status === 'failed') {
            setActiveBroadcastId(null);
            clearInterval(interval);
            await loadBroadcasts();
          }
        } catch (error) {
          console.error('Error loading progress:', error);
        }
      }, 2000);
      return () => clearInterval(interval);
    }
  }, [activeBroadcastId]);

  const loadBroadcasts = async () => {
    try {
      setLoading(true);
      const data = await api.getBroadcasts();
      setBroadcasts(data || []);
    } catch (error) {
      console.error('Error loading broadcasts:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSend = async () => {
    if (!message.trim()) {
      alert(t('broadcast.messageRequired') || 'Message is required');
      return;
    }

    if ((targetType === 'active' || targetType === 'inactive' || targetType === 'new_users') && !targetValue) {
      alert(t('broadcast.daysRequired') || 'Number of days is required');
      return;
    }

    if (targetType === 'language' && !targetValue) {
      alert(t('broadcast.languageRequired') || 'Language code is required');
      return;
    }

    if (targetType === 'role' && !targetValue) {
      alert(t('broadcast.roleRequired') || 'Role is required');
      return;
    }

    if (targetType === 'active_status' && !targetValue) {
      alert(t('broadcast.activeStatusRequired') || 'Active status is required');
      return;
    }

    try {
      setSending(true);
      const broadcast = await api.createBroadcast({
        message: message.trim(),
        target_type: targetType,
        target_value: (targetType === 'active' || targetType === 'inactive' || targetType === 'new_users') 
          ? parseInt(targetValue) 
          : targetValue || undefined,
        schedule_time: scheduleTime || null,
      });
      
      setBroadcasts([broadcast, ...broadcasts]);
      setMessage('');
      setTargetType('all');
      setTargetValue('');
      setScheduleTime('');
      
      // Show result message
      if (broadcast.status === 'completed') {
        alert(`${t('broadcast.broadcastCreated') || 'Broadcast created successfully'}\n${broadcast.sent_count || 0} messages sent successfully.`);
      } else if (broadcast.status === 'completed_with_errors') {
        alert(`${t('broadcast.broadcastCreated') || 'Broadcast created successfully'}\n${broadcast.sent_count || 0} messages sent, ${broadcast.error_count || 0} errors.`);
      } else if (broadcast.status === 'queued') {
        alert(`${t('broadcast.broadcastCreated') || 'Broadcast created successfully'}\nBroadcast scheduled for ${new Date(broadcast.schedule_time || '').toLocaleString()}.`);
      } else {
        alert(broadcast.note || t('broadcast.broadcastCreated') || 'Broadcast created successfully');
      }
    } catch (error: any) {
      alert(`Failed to create broadcast: ${error.message || error}`);
    } finally {
      setSending(false);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return CheckCircle2;
      case 'failed':
        return XCircle;
      case 'sending':
        return Clock;
      default:
        return AlertCircle;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'oneui-badge-success';
      case 'failed':
        return 'oneui-badge-danger';
      case 'sending':
        return 'oneui-badge-warning';
      default:
        return 'oneui-badge-secondary';
    }
  };

  return (
    <div>
      {/* Page Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-2" style={{ color: 'var(--oneui-text)' }}>
          {t('broadcast.title') || 'Broadcast Studio'}
        </h1>
        <p className="oneui-text-muted">
          {t('broadcast.subtitle') || 'Create and send messages to users'}
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 border-b" style={{ borderColor: 'var(--oneui-border)' }}>
        {[
          { id: 'create', label: t('broadcast.create') || 'Create Broadcast', icon: Send },
          { id: 'history', label: t('broadcast.history') || 'History', icon: History },
        ].map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`px-4 py-2 flex items-center gap-2 border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                  : 'border-transparent oneui-text-muted hover:text-indigo-600 dark:hover:text-indigo-400'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span className="font-medium">{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Create Broadcast */}
      {activeTab === 'create' && (
        <div className="space-y-6">
          {/* Message Editor */}
          <div className="oneui-card">
            <div className="oneui-card-header">
              <div className="flex items-center gap-3">
                <div className="oneui-stat-icon oneui-stat-icon-primary">
                  <Send className="w-5 h-5" />
                </div>
                <h3 className="oneui-card-title">{t('broadcast.messageEditor') || 'Message Editor'}</h3>
              </div>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2" style={{ color: 'var(--oneui-text)' }}>
                  {t('broadcast.message') || 'Message'}
                </label>
                <textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  rows={8}
                  className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  style={{
                    backgroundColor: 'var(--oneui-bg-alt)',
                    borderColor: 'var(--oneui-border)',
                    color: 'var(--oneui-text)',
                  }}
                  placeholder={t('broadcast.messagePlaceholder') || 'Enter your message here...'}
                />
                <p className="text-xs oneui-text-muted mt-1">
                  {t('broadcast.messageNote') || 'Supports Markdown formatting. Use /help for formatting guide.'}
                </p>
              </div>
            </div>
          </div>

          {/* Targeting */}
          <div className="oneui-card">
            <div className="oneui-card-header">
              <div className="flex items-center gap-3">
                <div className="oneui-stat-icon oneui-stat-icon-primary">
                  <Filter className="w-5 h-5" />
                </div>
                <h3 className="oneui-card-title">{t('broadcast.targeting') || 'Targeting'}</h3>
              </div>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2" style={{ color: 'var(--oneui-text)' }}>
                  {t('broadcast.targetType') || 'Target Type'}
                </label>
                <select
                  value={targetType}
                  onChange={(e) => {
                    setTargetType(e.target.value as any);
                    setTargetValue('');
                  }}
                  className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  style={{
                    backgroundColor: 'var(--oneui-bg-alt)',
                    borderColor: 'var(--oneui-border)',
                    color: 'var(--oneui-text)',
                  }}
                >
                  <option value="all">{t('broadcast.targetAll') || 'All Users'}</option>
                  <option value="admins">{t('broadcast.targetAdmins') || 'Administrators Only'}</option>
                  <option value="role">{t('broadcast.targetRole') || 'By Role'}</option>
                  <option value="active">{t('broadcast.targetActive') || 'Active Users (Last N days)'}</option>
                  <option value="inactive">{t('broadcast.targetInactive') || 'Inactive Users (No activity for N days)'}</option>
                  <option value="new_users">{t('broadcast.targetNewUsers') || 'New Users (Registered in last N days)'}</option>
                  <option value="language">{t('broadcast.targetLanguage') || 'By Language'}</option>
                  <option value="active_status">{t('broadcast.targetActiveStatus') || 'By Active Status'}</option>
                </select>
              </div>

              {targetType === 'role' && (
                <div>
                  <label className="block text-sm font-medium mb-2" style={{ color: 'var(--oneui-text)' }}>
                    {t('broadcast.role') || 'Role'}
                  </label>
                  <select
                    value={targetValue}
                    onChange={(e) => setTargetValue(e.target.value)}
                    className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    style={{
                      backgroundColor: 'var(--oneui-bg-alt)',
                      borderColor: 'var(--oneui-border)',
                      color: 'var(--oneui-text)',
                    }}
                  >
                    <option value="">{t('broadcast.selectRole') || 'Select Role'}</option>
                    <option value="User">{t('broadcast.roleUser') || 'User'}</option>
                    <option value="Moderator">{t('broadcast.roleModerator') || 'Moderator'}</option>
                    <option value="Admin">{t('broadcast.roleAdmin') || 'Admin'}</option>
                    <option value="SuperAdmin">{t('broadcast.roleSuperAdmin') || 'Super Admin'}</option>
                  </select>
                </div>
              )}

              {targetType === 'active' && (
                <div>
                  <label className="block text-sm font-medium mb-2" style={{ color: 'var(--oneui-text)' }}>
                    {t('broadcast.days') || 'Days'}
                  </label>
                  <input
                    type="number"
                    value={targetValue}
                    onChange={(e) => setTargetValue(e.target.value)}
                    min="1"
                    max="365"
                    placeholder="7"
                    className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    style={{
                      backgroundColor: 'var(--oneui-bg-alt)',
                      borderColor: 'var(--oneui-border)',
                      color: 'var(--oneui-text)',
                    }}
                  />
                  <p className="text-xs oneui-text-muted mt-1">
                    {t('broadcast.activeDaysNote') || 'Users who were active in the last N days'}
                  </p>
                </div>
              )}

              {targetType === 'inactive' && (
                <div>
                  <label className="block text-sm font-medium mb-2" style={{ color: 'var(--oneui-text)' }}>
                    {t('broadcast.days') || 'Days'}
                  </label>
                  <input
                    type="number"
                    value={targetValue}
                    onChange={(e) => setTargetValue(e.target.value)}
                    min="1"
                    max="365"
                    placeholder="30"
                    className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    style={{
                      backgroundColor: 'var(--oneui-bg-alt)',
                      borderColor: 'var(--oneui-border)',
                      color: 'var(--oneui-text)',
                    }}
                  />
                  <p className="text-xs oneui-text-muted mt-1">
                    {t('broadcast.inactiveDaysNote') || 'Users who have not been active for N days'}
                  </p>
                </div>
              )}

              {targetType === 'new_users' && (
                <div>
                  <label className="block text-sm font-medium mb-2" style={{ color: 'var(--oneui-text)' }}>
                    {t('broadcast.days') || 'Days'}
                  </label>
                  <input
                    type="number"
                    value={targetValue}
                    onChange={(e) => setTargetValue(e.target.value)}
                    min="1"
                    max="365"
                    placeholder="30"
                    className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    style={{
                      backgroundColor: 'var(--oneui-bg-alt)',
                      borderColor: 'var(--oneui-border)',
                      color: 'var(--oneui-text)',
                    }}
                  />
                  <p className="text-xs oneui-text-muted mt-1">
                    {t('broadcast.newUsersDaysNote') || 'Users registered in the last N days'}
                  </p>
                </div>
              )}

              {targetType === 'language' && (
                <div>
                  <label className="block text-sm font-medium mb-2" style={{ color: 'var(--oneui-text)' }}>
                    {t('broadcast.language') || 'Language Code'}
                  </label>
                  <select
                    value={targetValue}
                    onChange={(e) => setTargetValue(e.target.value)}
                    className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    style={{
                      backgroundColor: 'var(--oneui-bg-alt)',
                      borderColor: 'var(--oneui-border)',
                      color: 'var(--oneui-text)',
                    }}
                  >
                    <option value="">{t('broadcast.selectLanguage') || 'Select Language'}</option>
                    <option value="ru">Русский</option>
                    <option value="en">English</option>
                    <option value="ua">Українська</option>
                  </select>
                </div>
              )}

              {targetType === 'active_status' && (
                <div>
                  <label className="block text-sm font-medium mb-2" style={{ color: 'var(--oneui-text)' }}>
                    {t('broadcast.activeStatus') || 'Active Status'}
                  </label>
                  <select
                    value={targetValue}
                    onChange={(e) => setTargetValue(e.target.value)}
                    className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    style={{
                      backgroundColor: 'var(--oneui-bg-alt)',
                      borderColor: 'var(--oneui-border)',
                      color: 'var(--oneui-text)',
                    }}
                  >
                    <option value="">{t('broadcast.selectActiveStatus') || 'Select Status'}</option>
                    <option value="active">{t('broadcast.statusActive') || 'Active Users'}</option>
                    <option value="inactive">{t('broadcast.statusInactive') || 'Inactive Users'}</option>
                  </select>
                </div>
              )}
            </div>
          </div>

          {/* Scheduling */}
          <div className="oneui-card">
            <div className="oneui-card-header">
              <div className="flex items-center gap-3">
                <div className="oneui-stat-icon oneui-stat-icon-primary">
                  <Calendar className="w-5 h-5" />
                </div>
                <h3 className="oneui-card-title">{t('broadcast.scheduling') || 'Scheduling'}</h3>
              </div>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2" style={{ color: 'var(--oneui-text)' }}>
                  {t('broadcast.sendTime') || 'Send Time'}
                </label>
                <input
                  type="datetime-local"
                  value={scheduleTime}
                  onChange={(e) => setScheduleTime(e.target.value)}
                  className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  style={{
                    backgroundColor: 'var(--oneui-bg-alt)',
                    borderColor: 'var(--oneui-border)',
                    color: 'var(--oneui-text)',
                  }}
                />
                <p className="text-xs oneui-text-muted mt-1">
                  {t('broadcast.scheduleNote') || 'Leave empty to send immediately'}
                </p>
              </div>
            </div>
          </div>

          {/* Send Button */}
          <div className="flex justify-end">
            <button
              onClick={handleSend}
              disabled={sending || !message.trim()}
              className="oneui-btn oneui-btn-primary flex items-center gap-2"
            >
              <Play className="w-4 h-4" />
              {sending ? (t('common.saving') || 'Sending...') : (t('broadcast.send') || 'Send Broadcast')}
            </button>
          </div>

          {/* Live Progress */}
          {activeBroadcastId && progress && (
            <div className="oneui-card">
              <div className="oneui-card-header">
                <h3 className="oneui-card-title">{t('broadcast.progress') || 'Broadcast Progress'}</h3>
              </div>
              <div className="space-y-4">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium" style={{ color: 'var(--oneui-text)' }}>
                      {t('broadcast.sent') || 'Sent'}: {progress.sent} / {progress.total}
                    </span>
                    <span className={`oneui-badge ${getStatusColor(progress.status)}`}>
                      {progress.status}
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                    <div
                      className="bg-indigo-600 h-2 rounded-full transition-all"
                      style={{
                        width: progress.total > 0 ? `${(progress.sent / progress.total) * 100}%` : '0%'
                      }}
                    />
                  </div>
                </div>
                {progress.errors > 0 && (
                  <div className="text-sm oneui-text-muted">
                    {t('broadcast.errors') || 'Errors'}: {progress.errors}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* History */}
      {activeTab === 'history' && (
        <div className="oneui-card">
          <div className="oneui-card-header">
            <div className="flex items-center justify-between w-full">
              <div className="flex items-center gap-3">
                <div className="oneui-stat-icon oneui-stat-icon-primary">
                  <History className="w-5 h-5" />
                </div>
                <h3 className="oneui-card-title">{t('broadcast.history') || 'Broadcast History'}</h3>
              </div>
              <button
                onClick={loadBroadcasts}
                className="oneui-btn oneui-btn-secondary text-sm flex items-center gap-2"
              >
                <RefreshCw className="w-4 h-4" />
                {t('common.refresh') || 'Refresh'}
              </button>
            </div>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-8">
              <div className="oneui-spinner"></div>
            </div>
          ) : broadcasts.length === 0 ? (
            <div className="text-center py-12">
              <History className="w-16 h-16 mx-auto mb-4 oneui-text-muted" />
              <h3 className="text-xl font-bold mb-2" style={{ color: 'var(--oneui-text)' }}>
                {t('broadcast.noBroadcasts') || 'No broadcasts'}
              </h3>
              <p className="oneui-text-muted">
                {t('broadcast.noBroadcastsDesc') || 'No broadcasts have been sent yet.'}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="oneui-table min-w-full">
                <thead>
                  <tr>
                    <th>{t('broadcast.id') || 'ID'}</th>
                    <th>{t('broadcast.message') || 'Message'}</th>
                    <th>{t('broadcast.target') || 'Target'}</th>
                    <th>{t('broadcast.recipients') || 'Recipients'}</th>
                    <th>{t('broadcast.status') || 'Status'}</th>
                    <th>{t('broadcast.created') || 'Created'}</th>
                  </tr>
                </thead>
                <tbody>
                  {broadcasts.map((broadcast) => {
                    const StatusIcon = getStatusIcon(broadcast.status);
                    return (
                      <tr key={broadcast.id}>
                        <td>
                          <code className="text-sm font-mono" style={{ color: 'var(--oneui-text)' }}>
                            {broadcast.id}
                          </code>
                        </td>
                        <td className="oneui-text-muted">
                          <div className="max-w-xs truncate" title={broadcast.message}>
                            {broadcast.message}
                          </div>
                        </td>
                        <td>
                          <span className="oneui-badge oneui-badge-info">
                            {broadcast.target_type}
                          </span>
                        </td>
                        <td className="oneui-text-muted">
                          <div className="flex items-center gap-1">
                            <Users className="w-4 h-4" />
                            {broadcast.sent_count !== undefined ? (
                              <span>{broadcast.sent_count} / {broadcast.target_count}</span>
                            ) : (
                              <span>{broadcast.target_count}</span>
                            )}
                          </div>
                        </td>
                        <td>
                          <div className="flex items-center gap-2">
                            <StatusIcon className="w-4 h-4" />
                            <span className={`oneui-badge ${getStatusColor(broadcast.status)}`}>
                              {broadcast.status}
                            </span>
                          </div>
                        </td>
                        <td className="oneui-text-muted text-sm">
                          {new Date(broadcast.created_at).toLocaleString()}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

