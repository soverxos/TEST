import { useState, useEffect } from 'react';
import { useI18n } from '../../contexts/I18nContext';
import { api, CommandHistoryItem, FileItem } from '../../api';
import { Database, FileText, Download, Trash2, AlertTriangle, History } from 'lucide-react';

export const Data = () => {
  const { t } = useI18n();
  const [activeTab, setActiveTab] = useState<'history' | 'files' | 'export'>('history');
  const [commandHistory, setCommandHistory] = useState<CommandHistoryItem[]>([]);
  const [files, setFiles] = useState<FileItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (activeTab === 'history') {
      loadCommandHistory();
    } else if (activeTab === 'files') {
      loadFiles();
    } else {
      setLoading(false);
    }
  }, [activeTab]);

  const loadCommandHistory = async () => {
    try {
      setLoading(true);
      const data = await api.getCommandHistory(50);
      setCommandHistory(data);
    } catch (error) {
      console.error('Error loading command history:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadFiles = async () => {
    try {
      setLoading(true);
      const data = await api.getFiles();
      setFiles(data);
    } catch (error) {
      console.error('Error loading files:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      {/* Page Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-2" style={{ color: 'var(--oneui-text)' }}>
          {t('data.title')}
        </h1>
        <p className="oneui-text-muted">{t('data.subtitle')}</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 border-b" style={{ borderColor: 'var(--oneui-border)' }}>
        {[
          { id: 'history', label: t('data.commandHistory'), icon: History },
          { id: 'files', label: t('data.uploadedFiles'), icon: FileText },
          { id: 'export', label: t('data.exportData'), icon: Download },
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

      {/* Command History */}
      {activeTab === 'history' && (
        <div className="oneui-card">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <div className="oneui-spinner"></div>
            </div>
          ) : commandHistory.length === 0 ? (
            <div className="text-center py-8 text-sm oneui-text-muted">
              {t('data.noCommandHistory')}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="oneui-table min-w-full">
                <thead>
                  <tr>
                    <th>{t('data.command')}</th>
                    <th>{t('data.date')}</th>
                    <th>{t('data.status')}</th>
                  </tr>
                </thead>
                <tbody>
                  {commandHistory.map((item) => (
                    <tr key={item.id}>
                      <td>
                        <code className="text-sm font-mono" style={{ color: 'var(--oneui-text)' }}>
                          {item.command}
                        </code>
                      </td>
                      <td className="oneui-text-muted">{item.date}</td>
                      <td>
                        <span className="oneui-badge oneui-badge-success">{t('common.success')}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Files */}
      {activeTab === 'files' && (
        <div className="oneui-card">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <div className="oneui-spinner"></div>
            </div>
          ) : files.length === 0 ? (
            <div className="text-center py-8 text-sm oneui-text-muted">
              {t('data.noFiles')}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="oneui-table min-w-full">
                <thead>
                  <tr>
                    <th>{t('data.fileName')}</th>
                    <th>{t('data.size')}</th>
                    <th>{t('data.uploadDate')}</th>
                    <th>{t('common.actions')}</th>
                  </tr>
                </thead>
                <tbody>
                  {files.map((file) => (
                    <tr key={file.id}>
                      <td className="font-medium" style={{ color: 'var(--oneui-text)' }}>
                        {file.name}
                      </td>
                      <td className="oneui-text-muted">{file.size}</td>
                      <td className="oneui-text-muted">{file.uploadDate}</td>
                      <td>
                        <div className="flex gap-2">
                          <button className="oneui-btn oneui-btn-secondary text-sm">
                            <Download className="w-4 h-4" />
                          </button>
                          <button className="oneui-btn oneui-btn-secondary text-sm">
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Export & Privacy */}
      {activeTab === 'export' && (
        <div className="space-y-6">
          <div className="oneui-card">
            <div className="oneui-card-header">
              <div className="flex items-center gap-3">
                <div className="oneui-stat-icon oneui-stat-icon-primary">
                  <Download className="w-5 h-5" />
                </div>
                <h3 className="oneui-card-title">{t('data.exportData')}</h3>
              </div>
            </div>
            <p className="text-sm oneui-text-muted mb-4">
              Скачайте архив со всеми вашими данными в формате JSON/ZIP.
            </p>
            <button className="oneui-btn oneui-btn-primary">
              {t('data.downloadArchive')}
            </button>
          </div>

          <div className="oneui-card">
            <div className="oneui-card-header">
              <div className="flex items-center gap-3">
                <div className="oneui-stat-icon oneui-stat-icon-danger">
                  <AlertTriangle className="w-5 h-5" />
                </div>
                <h3 className="oneui-card-title">{t('data.privacy')}</h3>
              </div>
            </div>
            <div className="space-y-4">
              <div>
                <p className="text-sm oneui-text-muted mb-3">
                  Очистить всю историю диалогов с ботом. Это действие нельзя отменить.
                </p>
                <button className="oneui-btn oneui-btn-secondary">
                  {t('data.clearHistory')}
                </button>
              </div>
              <div className="pt-4 border-t" style={{ borderColor: 'var(--oneui-border)' }}>
                <p className="text-sm oneui-text-muted mb-3">
                  Удалить аккаунт и все связанные данные. Это действие нельзя отменить.
                </p>
                <button className="oneui-btn oneui-btn-secondary" style={{ borderColor: 'var(--oneui-danger)', color: 'var(--oneui-danger)' }}>
                  {t('data.deleteAccount')}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

