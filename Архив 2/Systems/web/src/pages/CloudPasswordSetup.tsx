import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { GlassCard } from '../components/ui/GlassCard';
import { GlassButton } from '../components/ui/GlassButton';
import { GlassInput } from '../components/ui/GlassInput';
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
    <div className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden">
      <div className="w-full max-w-md relative z-10">
        <GlassCard className="p-8" glow>
          <div className="flex flex-col items-center mb-8">
            <div className="logo-container mb-4">
              <Zap className="w-16 h-16" />
            </div>
            <h1 className="logo-text text-4xl font-bold mb-2">SwiftDevBot</h1>
            <p className="text-glass-text-secondary text-sm">
              Настройка безопасности
            </p>
          </div>

          <div className="mb-6 p-4 rounded-xl bg-cyan-500/10 border border-cyan-400/30">
            <div className="flex items-start gap-3">
              <Shield className="w-5 h-5 text-cyan-400 mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-sm font-medium text-glass-text mb-1">
                  Установите облачный пароль
                </p>
                <p className="text-xs text-glass-text-secondary">
                  Это дополнительный уровень защиты для доступа к веб-панели. 
                  Пароль будет запрашиваться при каждом входе через токен-ссылку.
                </p>
              </div>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            <GlassInput
              label="Облачный пароль"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Минимум 8 символов"
              required
              minLength={8}
            />

            <GlassInput
              label="Подтвердите пароль"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Повторите пароль"
              required
              minLength={8}
            />

            {error && (
              <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
                {error}
              </div>
            )}

            <GlassButton
              type="submit"
              variant="primary"
              size="lg"
              className="w-full"
              disabled={loading}
            >
              {loading ? (
                'Установка...'
              ) : (
                <>
                  <Lock className="w-4 h-4 mr-2" />
                  Установить пароль
                </>
              )}
            </GlassButton>
          </form>
        </GlassCard>

        <div className="text-center mt-8">
          <p className="footer-text text-sm">
            SwiftDevBot — created by <span className="font-semibold">SoverX</span>
          </p>
        </div>
      </div>
    </div>
  );
};

