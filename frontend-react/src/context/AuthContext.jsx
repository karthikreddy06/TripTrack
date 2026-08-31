import { createContext, useContext, useState, useEffect } from 'react';
import { authAPI } from '../services/api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);

  // Initialize auth state from localStorage on app start
  useEffect(() => {
    try {
      const storedToken = localStorage.getItem('traveltrack_token');
      const storedUser = localStorage.getItem('traveltrack_user');

      if (storedToken && storedUser) {
        setToken(storedToken);
        setUser(JSON.parse(storedUser));
      }
    } catch (err) {
      console.error('Failed to parse stored auth session:', err);
      localStorage.removeItem('traveltrack_token');
      localStorage.removeItem('traveltrack_user');
    } finally {
      setLoading(false);
    }

    // Global listener for automatic logout from API interceptor (e.g. on 401)
    const handleGlobalLogout = () => {
      setUser(null);
      setToken(null);
    };

    window.addEventListener('traveltrack:logout', handleGlobalLogout);
    return () => {
      window.removeEventListener('traveltrack:logout', handleGlobalLogout);
    };
  }, []);

  const login = async (credentials) => {
    const data = await authAPI.login(credentials);
    
    // Response schema: { message, access_token, token_type, user_id, name, email }
    const userInfo = {
      user_id: data.user_id,
      name: data.name,
      email: data.email,
    };

    localStorage.setItem('traveltrack_token', data.access_token);
    localStorage.setItem('traveltrack_user', JSON.stringify(userInfo));

    setToken(data.access_token);
    setUser(userInfo);
    return data;
  };

  const register = async (userData) => {
    return await authAPI.register(userData);
  };

  const logout = () => {
    localStorage.removeItem('traveltrack_token');
    localStorage.removeItem('traveltrack_user');
    setToken(null);
    setUser(null);
  };

  const value = {
    user,
    token,
    isAuthenticated: Boolean(token && user),
    loading,
    login,
    register,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
