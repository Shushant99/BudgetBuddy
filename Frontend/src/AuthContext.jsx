import { createContext, useContext, useState } from 'react';
import { api, setToken } from './api';

const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => JSON.parse(localStorage.getItem('bb_user') || 'null'));

  const saveSession = ({ token, user }) => {
    setToken(token);
    localStorage.setItem('bb_user', JSON.stringify(user));
    setUser(user);
  };

  const login = async (email, password) =>
    saveSession(await api('/login/', { method: 'POST', body: { email, password } }));

  const signup = async (form) =>
    saveSession(await api('/signup/', { method: 'POST', body: form }));

  const logout = async () => {
    try {
      await api('/logout/', { method: 'POST' });
    } catch {
      /* token was already invalid */
    }
    setToken(null);
    localStorage.removeItem('bb_user');
    setUser(null);
  };

  return <AuthContext.Provider value={{ user, login, signup, logout }}>{children}</AuthContext.Provider>;
}