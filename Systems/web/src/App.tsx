import { AuthProvider, useAuth } from './contexts/AuthContext';
import { ThemeProvider } from './contexts/ThemeContext';
import { I18nProvider, useI18n } from './contexts/I18nContext';
import { CloudPasswordSetup } from './pages/CloudPasswordSetup';
import { CloudPasswordPrompt } from './pages/CloudPasswordPrompt';
import { Dashboard } from './pages/Dashboard';

const AppContent = () => {
  const { user, loading, cloudPasswordSetup, cloudPasswordVerified } = useAuth();
  const { t } = useI18n();
  
  // Debug logging
  console.log('AppContent render:', { 
    hasUser: !!user, 
    loading, 
    cloudPasswordSetup, 
    cloudPasswordVerified 
  });

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="loading-spinner"></div>
      </div>
    );
  }

  // If user exists but cloud password status is still checking
  if (user && cloudPasswordSetup === null) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="loading-spinner"></div>
      </div>
    );
  }

  // If user is logged in but cloud password not verified
  if (user && !cloudPasswordVerified) {
    if (cloudPasswordSetup === false) {
      // First time - need to setup cloud password
      return <CloudPasswordSetup />;
    } else {
      // Cloud password exists - need to verify
      return <CloudPasswordPrompt />;
    }
  }

  // User is logged in and cloud password verified
  if (user && cloudPasswordVerified) {
    return <Dashboard />;
  }

  // No user - show message that login is only via token
  return (
    <div className="min-h-screen flex items-center justify-center p-4" style={{ backgroundColor: 'var(--oneui-bg-alt)' }}>
      <div className="text-center max-w-md oneui-card">
        <h1 className="text-3xl font-bold mb-4" style={{ color: 'var(--oneui-text)' }}>SwiftDevBot</h1>
        <p className="oneui-text-muted mb-6">
          {t('auth.loginViaTelegram')} <code className="bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded">/login</code>
        </p>
        <p className="text-sm oneui-text-muted">
          {t('auth.loginLink')}
        </p>
      </div>
    </div>
  );
};

function App() {
  return (
    <I18nProvider>
      <ThemeProvider>
        <AuthProvider>
          <AppContent />
        </AuthProvider>
      </ThemeProvider>
    </I18nProvider>
  );
}

export default App;
