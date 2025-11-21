import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { GlassCard } from '../components/ui/GlassCard';
import { GlassButton } from '../components/ui/GlassButton';
import { GlassInput } from '../components/ui/GlassInput';
import { Lock, Zap, Shield } from 'lucide-react';

export const CloudPasswordPrompt = () => {
  const { verifyCloudPassword } = useAuth();
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (!password || password.trim() === '') {
      setError('Введите пароль');
      return;
    }
    
    setError('');
    setLoading(true);

    try {
      console.log('Verifying cloud password...');
      await verifyCloudPassword(password);
      console.log('Cloud password verified successfully');
      // State will be updated by verifyCloudPassword, which will trigger App re-render
      // Don't set loading to false here - let the component re-render naturally
      setPassword('');
    } catch (err) {
      console.error('Cloud password verification error:', err);
      const errorMessage = err instanceof Error ? err.message : 'Неверный пароль';
      setError(errorMessage);
      setPassword('');
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
              Введите облачный пароль
            </p>
          </div>

          <div className="mb-6 p-4 rounded-xl bg-purple-500/10 border border-purple-400/30">
            <div className="flex items-start gap-3">
              <Shield className="w-5 h-5 text-purple-400 mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-sm font-medium text-glass-text mb-1">
                  Дополнительная защита
                </p>
                <p className="text-xs text-glass-text-secondary">
                  Для доступа к панели требуется ввести ваш облачный пароль.
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
              placeholder="Введите ваш пароль"
              required
              autoFocus
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
              disabled={loading || !password}
            >
              {loading ? (
                'Проверка...'
              ) : (
                <>
                  <Lock className="w-4 h-4 mr-2" />
                  Войти
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

