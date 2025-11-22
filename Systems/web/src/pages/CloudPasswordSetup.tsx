import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Shield, Zap, Lock } from 'lucide-react';

export const CloudPasswordSetup = () => {
  const { setupCloudPassword } = useAuth();
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (password.length < 8) {
      setError('Пароль должен содержать минимум 8 символов');
      return;
    }

    if (password !== confirmPassword) {
      setError('Пароли не совпадают');
      return;
    }

    setLoading(true);

    try {
      await setupCloudPassword(password);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ошибка установки пароля');
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 py-8" style={{ backgroundColor: 'var(--oneui-bg-alt)', width: '100%', maxWidth: '100vw', overflowX: 'hidden' }}>
      <div className="w-full max-w-md mx-auto" style={{ width: '100%', maxWidth: 'min(100% - 2rem, 28rem)' }}>
        <div className="oneui-card" style={{ width: '100%' }}>
          <div className="flex flex-col items-center mb-6 sm:mb-8">
            <div className="w-14 h-14 sm:w-16 sm:h-16 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center mb-3 sm:mb-4">
              <Zap className="w-7 h-7 sm:w-8 sm:h-8 text-white" />
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold mb-2" style={{ color: 'var(--oneui-text)' }}>SwiftDevBot</h1>
            <p className="oneui-text-muted text-xs sm:text-sm text-center px-4">Настройка безопасности</p>
          </div>

          <div className="mb-4 sm:mb-6 p-3 sm:p-4 rounded-lg border-l-4" style={{ 
            backgroundColor: 'rgba(99, 102, 241, 0.1)',
            borderLeftColor: 'var(--oneui-primary)',
          }}>
            <div className="flex items-start gap-2 sm:gap-3">
              <Shield className="w-4 h-4 sm:w-5 sm:h-5 text-indigo-500 mt-0.5 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-xs sm:text-sm font-medium mb-1" style={{ color: 'var(--oneui-text)' }}>
                  Установите облачный пароль
                </p>
                <p className="text-xs oneui-text-muted leading-relaxed">
                  Это дополнительный уровень защиты для доступа к веб-панели. 
                  Пароль будет запрашиваться при каждом входе через токен-ссылку.
                </p>
              </div>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4 sm:space-y-5">
            <div>
              <label className="block text-xs sm:text-sm font-medium mb-2" style={{ color: 'var(--oneui-text)' }}>
                Облачный пароль
              </label>
              <div className="relative">
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Минимум 8 символов"
                  required
                  minLength={8}
                  className="w-full px-3 sm:px-4 py-2.5 sm:py-2 text-sm sm:text-base border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  style={{
                    backgroundColor: 'var(--oneui-bg-alt)',
                    borderColor: 'var(--oneui-border)',
                    color: 'var(--oneui-text)',
                  }}
                />
                <Lock className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 oneui-text-muted pointer-events-none" />
              </div>
            </div>

            <div>
              <label className="block text-xs sm:text-sm font-medium mb-2" style={{ color: 'var(--oneui-text)' }}>
                Подтвердите пароль
              </label>
              <div className="relative">
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Повторите пароль"
                  required
                  minLength={8}
                  className="w-full px-3 sm:px-4 py-2.5 sm:py-2 text-sm sm:text-base border rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  style={{
                    backgroundColor: 'var(--oneui-bg-alt)',
                    borderColor: 'var(--oneui-border)',
                    color: 'var(--oneui-text)',
                  }}
                />
                <Lock className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 oneui-text-muted pointer-events-none" />
              </div>
            </div>

            {error && (
              <div className="p-3 rounded-lg border-l-4 text-xs sm:text-sm" style={{
                backgroundColor: 'rgba(239, 68, 68, 0.1)',
                borderLeftColor: 'var(--oneui-danger)',
                color: 'var(--oneui-danger)',
              }}>
                {error}
              </div>
            )}

            <button
              type="submit"
              className="oneui-btn oneui-btn-primary w-full flex items-center justify-center gap-2 py-2.5 sm:py-2 text-sm sm:text-base"
              disabled={loading}
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  Установка...
                </span>
              ) : (
                <>
                  <Lock className="w-4 h-4" />
                  Установить пароль
                </>
              )}
            </button>
          </form>
        </div>

        <div className="text-center mt-6 sm:mt-8">
          <p className="text-xs sm:text-sm oneui-text-muted">
            SwiftDevBot — created by <span className="font-semibold">SoverX</span>
          </p>
        </div>
      </div>
    </div>
  );
};
