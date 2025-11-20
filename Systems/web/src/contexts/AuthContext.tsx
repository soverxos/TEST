import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { api, User, Profile } from '../api';

type AuthContextType = {
  user: User | null;
  profile: Profile | null;
  isAdmin: boolean;
  loading: boolean;
  cloudPasswordSetup: boolean | null; // null = checking, true = setup, false = not setup
  cloudPasswordVerified: boolean; // true = verified, false = not verified
  signInWithToken: (token: string) => Promise<void>;
  setupCloudPassword: (password: string) => Promise<void>;
  verifyCloudPassword: (password: string) => Promise<void>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [cloudPasswordSetup, setCloudPasswordSetup] = useState<boolean | null>(null);
  const [cloudPasswordVerified, setCloudPasswordVerified] = useState(false);

  const signInWithToken = async (token: string) => {
    try {
      console.log('signInWithToken called with token:', token ? 'present' : 'missing');
      const response = await api.loginWithToken(token);
      console.log('loginWithToken response:', response);
      setUser(response.user);
      const userProfile: Profile = {
        username: response.user.username,
        role: response.user.role,
      };
      setProfile(userProfile);
      localStorage.setItem('sdb_user', JSON.stringify(response.user));
      localStorage.setItem('sdb_token', response.token);
      console.log('Token saved to localStorage:', response.token ? 'yes' : 'no');

      // Check if cloud password is setup (async, don't block)
      api.checkCloudPasswordSetup()
        .then(result => {
          console.log('Cloud password setup check result:', result);
          setCloudPasswordSetup(result.isSetup);
        })
        .catch(error => {
          console.error('Error checking cloud password setup:', error);
          setCloudPasswordSetup(false);
        });
    } catch (error) {
      console.error('Token sign in error:', error);
      throw error;
    }
  };

  const setupCloudPassword = async (password: string) => {
    try {
      console.log('Setting up cloud password...');
      await api.setupCloudPassword(password);
      console.log('Cloud password setup successful');
      setCloudPasswordSetup(true);
      setCloudPasswordVerified(true);
      localStorage.setItem('sdb_cloud_password_setup', 'true');
      localStorage.setItem('sdb_cloud_password_verified', 'true');
      console.log('State updated: cloudPasswordSetup=true, cloudPasswordVerified=true');
    } catch (error) {
      console.error('Cloud password setup error:', error);
      throw error;
    }
  };

  const verifyCloudPassword = async (password: string) => {
    try {
      console.log('Calling api.verifyCloudPassword...');
      await api.verifyCloudPassword(password);
      console.log('API verifyCloudPassword successful, updating state...');
      setCloudPasswordVerified(true);
      localStorage.setItem('sdb_cloud_password_verified', 'true');
      console.log('State updated: cloudPasswordVerified=true');
      // Force a small delay to ensure state update propagates
      await new Promise(resolve => setTimeout(resolve, 100));
      console.log('State update complete, should trigger re-render');
    } catch (error) {
      console.error('Cloud password verification error:', error);
      throw error;
    }
  };

  useEffect(() => {
    // Check for token in URL (from Telegram bot)
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get('token');

    if (token) {
      // Remove token from URL
      const newUrl = window.location.pathname;
      window.history.replaceState({}, '', newUrl);

      // Try to login with token
      signInWithToken(token).catch((error) => {
        console.error('Token login failed:', error);
        setLoading(false);
      }).finally(() => {
        setLoading(false);
      });
      return;
    }

    // Check for saved session
    const savedUser = localStorage.getItem('sdb_user');
    const cloudPasswordVerified = localStorage.getItem('sdb_cloud_password_verified');

    if (savedUser && cloudPasswordVerified === 'true') {
      try {
        const userData = JSON.parse(savedUser);
        setUser(userData);
        setProfile({
          username: userData.username,
          role: userData.role,
        });
        setCloudPasswordVerified(true);

        // Check cloud password setup status
        api.checkCloudPasswordSetup()
          .then(result => setCloudPasswordSetup(result.isSetup))
          .catch(() => {
            setCloudPasswordSetup(false);
            setLoading(false);
          })
          .finally(() => {
            setLoading(false);
          });
      } catch (error) {
        console.error('Error loading saved user:', error);
        localStorage.removeItem('sdb_user');
        localStorage.removeItem('sdb_token');
        localStorage.removeItem('sdb_cloud_password_verified');
        setCloudPasswordSetup(false);
        setLoading(false);
      }
    } else if (savedUser) {
      // User exists but cloud password not verified - need to verify
      try {
        const userData = JSON.parse(savedUser);
        setUser(userData);
        setProfile({
          username: userData.username,
          role: userData.role,
        });

        // Check cloud password setup status
        api.checkCloudPasswordSetup()
          .then(result => setCloudPasswordSetup(result.isSetup))
          .catch(() => {
            setCloudPasswordSetup(false);
            setLoading(false);
          })
          .finally(() => {
            setLoading(false);
          });
      } catch (error) {
        console.error('Error loading saved user:', error);
        localStorage.removeItem('sdb_user');
        localStorage.removeItem('sdb_token');
        setCloudPasswordSetup(false);
        setLoading(false);
      }
    } else {
      // No user - no need to check cloud password
      setCloudPasswordSetup(false);
      setLoading(false);
    }
  }, []);

  const signOut = async () => {
    try {
      await api.logout();
    } catch (error) {
      console.error('Sign out error:', error);
    } finally {
      setUser(null);
      setProfile(null);
      setCloudPasswordVerified(false);
      localStorage.removeItem('sdb_user');
      localStorage.removeItem('sdb_token');
      localStorage.removeItem('sdb_cloud_password_verified');
      localStorage.removeItem('sdb_cloud_password_setup');
    }
  };

  // Check for admin role - handle various cases
  const isAdminValue = profile?.role?.toLowerCase() === 'admin' ||
    profile?.role === 'admin' ||
    profile?.role === 'Admin' ||
    profile?.role === 'SUPERADMIN' ||
    profile?.role?.toLowerCase() === 'superadmin';

  // Debug logging
  console.log('AuthContext - profile:', profile);
  console.log('AuthContext - profile.role:', profile?.role);
  console.log('AuthContext - isAdmin:', isAdminValue);
  console.log('AuthContext - user:', user);

  const value = {
    user,
    profile,
    isAdmin: isAdminValue,
    loading,
    cloudPasswordSetup,
    cloudPasswordVerified,
    signInWithToken,
    setupCloudPassword,
    verifyCloudPassword,
    signOut,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
