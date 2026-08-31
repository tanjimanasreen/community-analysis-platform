import { useContext } from 'react';
import { AuthContext, defaultLocalAuth, type AuthContextType } from './authContext';

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  return context ?? defaultLocalAuth;
}
