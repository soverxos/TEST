import { AuthProvider, useAuth } from './contexts/AuthContext';
import { ThemeProvider } from './contexts/ThemeContext';
import { CloudPasswordSetup } from './pages/CloudPasswordSetup';
import { CloudPasswordPrompt } from './pages/CloudPasswordPrompt';
import { Dashboard } from './pages/Dashboard';
import { AnimatedBackground } from './components/AnimatedBackground';

const AppContent = () => {
  const { user, loading, cloudPasswordSetup, cloudPasswordVerified } = useAuth();
  
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
      return (
        <>
          <AnimatedBackground />
          <div className="relative z-10">
            <CloudPasswordSetup />
          </div>
        </>
      );
    } else {
      // Cloud password exists - need to verify
      return (
        <>
          <AnimatedBackground />
          <div className="relative z-10">
            <CloudPasswordPrompt />
          </div>
        </>
      );
    }
  }

  // User is logged in and cloud password verified
  if (user && cloudPasswordVerified) {
    return (
      <>
        <AnimatedBackground />
        <div className="relative z-10">
          <Dashboard />
        </div>
      </>
    );
  }

  // No user - show message that login is only via token
  return (
    <>
      <AnimatedBackground />
      <div className="relative z-10 min-h-screen flex items-center justify-center p-4">
        <div className="text-center max-w-md">
          <h1 className="logo-text text-4xl font-bold mb-4">SwiftDevBot</h1>
          <p className="text-glass-text-secondary mb-6">
            Для входа в панель используйте команду <code className="bg-white/10 px-2 py-1 rounded">/login</code> в Telegram боте
          </p>
          <p className="text-sm text-glass-text-secondary">
            Вы получите ссылку для входа в веб-панель
          </p>
        </div>
      </div>
    </>
  );
};

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
