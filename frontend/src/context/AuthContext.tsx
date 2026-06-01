import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import type { AuthUser, UserRole } from "../types";
import { getCurrentUser, hydrateAuthToken, login as loginRequest, register as registerRequest, setAuthToken } from "../services/api";

interface AuthContextValue {
  user: AuthUser | null;
  booting: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string, role: UserRole) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [booting, setBooting] = useState(true);

  useEffect(() => {
    const token = hydrateAuthToken();
    if (!token) {
      setBooting(false);
      return;
    }

    getCurrentUser()
      .then(setUser)
      .catch(() => setAuthToken(null))
      .finally(() => setBooting(false));
  }, []);

  const value = useMemo<AuthContextValue>(() => ({
    user,
    booting,
    login: async (email, password) => {
      const response = await loginRequest(email, password);
      setUser(response.user);
    },
    register: async (name, email, password, role) => {
      await registerRequest(name, email, password, role);
    },
    logout: () => {
      setAuthToken(null);
      setUser(null);
    }
  }), [booting, user]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
