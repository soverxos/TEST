import { useState, useEffect } from 'react';
import { useI18n } from '../../contexts/I18nContext';
import { api, Token } from '../../api';
import { Key, Plus, Copy, Trash2, ExternalLink, AlertCircle, CheckCircle2 } from 'lucide-react';

export const Developer = () => {
  const { t } = useI18n();
  const [tokens, setTokens] = useState<Token[]>([]);
  const [showGenerateForm, setShowGenerateForm] = useState(false);
  const [newTokenName, setNewTokenName] = useState('');
  const [generatedToken, setGeneratedToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    loadTokens();
  }, []);

  const loadTokens = async () => {
    try {
      setLoading(true);
      const data = await api.getTokens();
      setTokens(data);
    } catch (error) {
      console.error('Error loading tokens:', error);
    } finally {
      setLoading(false);
    }
  };

  const generateToken = async () => {
    if (!newTokenName.trim()) return;
    try {
      setGenerating(true);
      const result = await api.createToken(newTokenName);
      setTokens([...tokens, result]);
      setGeneratedToken(result.token);
      setNewTokenName('');
      setShowGenerateForm(false);
    } catch (error: any) {
      console.error('Error generating token:', error);
      alert(`Failed to generate token: ${error.message || error}`);
    } finally {
      setGenerating(false);
    }
  };

  const copyToken = (token: string) => {
    navigator.clipboard.writeText(token);
  };

  const revokeToken = async (id: string) => {
    if (!confirm(t('developer.confirmRevoke'))) return;
    try {
      await api.revokeToken(id);
      setTokens(tokens.filter((t) => t.id !== id));
    } catch (error: any) {
      console.error('Error revoking token:', error);
      alert(`Failed to revoke token: ${error.message || error}`);
    }
  };

  return (
    <div>
      {/* Page Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-2" style={{ color: 'var(--oneui-text)' }}>
          {t('developer.title')}
        </h1>
        <p className="oneui-text-muted">{t('developer.subtitle')}</p>
      </div>

      {/* Generate Token */}
      <div className="oneui-card mb-6">
        <div className="oneui-card-header">
          <div className="flex items-center justify-between w-full">
            <div className="flex items-center gap-3">
              <div className="oneui-stat-icon oneui-stat-icon-primary">
                <Key className="w-5 h-5" />
              </div>
              <h3 className="oneui-card-title">{t('developer.generateToken')}</h3>
            </div>
            <button
              onClick={() => setShowGenerateForm(!showGenerateForm)}
              className="oneui-btn oneui-btn-primary flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              {t('developer.generateToken')}
            </button>
          </div>
        </div>

        {showGenerateForm && (
          <div className="space-y-4 pt-4 border-t" style={{ borderColor: 'var(--oneui-border)' }}>
            <div>
              <label className="block text-sm font-medium mb-2" style={{ color: 'var(--oneui-text)' }}>
                {t('developer.tokenName')}
              </label>
              <input
                type="text"
                value={newTokenName}
                onChange={(e) => setNewTokenName(e.target.value)}
                placeholder="My API Token"
                className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                style={{
                  backgroundColor: 'var(--oneui-bg-alt)',
                  borderColor: 'var(--oneui-border)',
                  color: 'var(--oneui-text)',
                }}
              />
            </div>
            <button 
              onClick={generateToken} 
              className="oneui-btn oneui-btn-primary"
              disabled={generating || !newTokenName.trim()}
            >
              {generating ? t('common.saving') : t('developer.generateToken')}
            </button>
          </div>
        )}

        {generatedToken && (
          <div className="mt-4 p-4 rounded-lg border-l-4" style={{
            backgroundColor: 'rgba(16, 185, 129, 0.1)',
            borderLeftColor: 'var(--oneui-success)',
          }}>
            <div className="flex items-start gap-3 mb-3">
              <AlertCircle className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-sm font-medium mb-2" style={{ color: 'var(--oneui-text)' }}>
                  {t('developer.warning')}
                </p>
                <div className="flex items-center gap-2 p-3 rounded bg-gray-100 dark:bg-gray-800">
                  <code className="flex-1 font-mono text-sm" style={{ color: 'var(--oneui-text)' }}>
                    {generatedToken}
                  </code>
                  <button
                    onClick={() => copyToken(generatedToken)}
                    className="oneui-btn oneui-btn-secondary text-sm"
                  >
                    <Copy className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* My Tokens */}
      <div className="oneui-card mb-6">
        <div className="oneui-card-header">
          <h3 className="oneui-card-title">{t('developer.myTokens')}</h3>
        </div>
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <div className="oneui-spinner"></div>
          </div>
        ) : tokens.length === 0 ? (
          <div className="text-center py-8 text-sm oneui-text-muted">
            {t('developer.noTokens')}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="oneui-table min-w-full">
              <thead>
                <tr>
                  <th>{t('developer.tokenName')}</th>
                  <th>{t('developer.created')}</th>
                  <th>{t('developer.lastUsed')}</th>
                  <th>{t('developer.actions')}</th>
                </tr>
              </thead>
              <tbody>
                {tokens.map((token) => (
                <tr key={token.id}>
                  <td className="font-medium" style={{ color: 'var(--oneui-text)' }}>
                    {token.name}
                  </td>
                  <td className="oneui-text-muted">{token.created}</td>
                  <td className="oneui-text-muted">
                    {token.lastUsed ? new Date(token.lastUsed).toLocaleString() : t('common.never')}
                  </td>
                  <td>
                    <div className="flex gap-2">
                      {generatedToken && token.token === generatedToken && (
                        <button
                          onClick={() => copyToken(token.token!)}
                          className="oneui-btn oneui-btn-secondary text-sm"
                          title={t('developer.copyToken')}
                        >
                          <Copy className="w-4 h-4" />
                        </button>
                      )}
                      <button
                        onClick={() => revokeToken(token.id)}
                        className="oneui-btn oneui-btn-secondary text-sm"
                        title={t('developer.revokeToken')}
                      >
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

      {/* API Documentation */}
      <div className="oneui-card">
        <div className="oneui-card-header">
          <div className="flex items-center justify-between w-full">
            <div className="flex items-center gap-3">
              <div className="oneui-stat-icon oneui-stat-icon-primary">
                <ExternalLink className="w-5 h-5" />
              </div>
              <h3 className="oneui-card-title">{t('developer.apiDocs')}</h3>
            </div>
            <a
              href="/api/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="oneui-btn oneui-btn-primary flex items-center gap-2"
            >
              <ExternalLink className="w-4 h-4" />
              {t('developer.openDocs')}
            </a>
          </div>
        </div>
        <p className="text-sm oneui-text-muted">
          Полная документация API доступна в Swagger UI. Используйте ваши токены для аутентификации.
        </p>
      </div>
    </div>
  );
};

