import { createContext } from 'react';
import type { AuthUser } from 'aws-amplify/auth';
import type { AuthMode } from './authConfig';

export interface AuthContextType {
  authMode: AuthMode;
  isLoading: boolean;
  isAuthenticated: boolean;
  user: AuthUser | { username: string; userId?: string } | null;
  error: Error | null;
  signIn: () => Promise<void>;
  signOut: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const defaultLocalAuth: AuthContextType = {
  authMode: 'local',
  isLoading: false,
  isAuthenticated: true,
  user: null,
  error: null,
  signIn: async () => {},
  signOut: async () => {},
};
