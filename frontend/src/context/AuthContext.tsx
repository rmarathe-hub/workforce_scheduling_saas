import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { clearToken, getToken, setToken } from "../shared/auth";
import { authApi, orgApi } from "../shared/services";
import type { MembershipRole, Organization, User } from "../types";

interface AuthContextValue {
  user: User | null;
  organization: Organization | null;
  role: MembershipRole | null;
  token: string | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (input: {
    email: string;
    password: string;
    full_name: string;
    organization_name: string;
  }) => Promise<void>;
  logout: () => void;
  refreshSession: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [organization, setOrganization] = useState<Organization | null>(null);
  const [role, setRole] = useState<MembershipRole | null>(null);
  const [token, setTokenState] = useState<string | null>(getToken());
  const [isLoading, setIsLoading] = useState(() => getToken() !== null);

  const loadSession = useCallback(async (activeToken: string) => {
    const [me, memberships] = await Promise.all([
      authApi.me(activeToken),
      orgApi.myOrganizations(activeToken),
    ]);
    setUser(me);
    const primary = memberships[0];
    setOrganization(primary?.organization ?? null);
    setRole(primary?.role ?? null);
  }, []);

  const refreshSession = useCallback(async () => {
    const activeToken = getToken();
    if (!activeToken) {
      setUser(null);
      setOrganization(null);
      setRole(null);
      setTokenState(null);
      return;
    }
    await loadSession(activeToken);
    setTokenState(activeToken);
  }, [loadSession]);

  useEffect(() => {
    const activeToken = getToken();
    if (!activeToken) {
      return;
    }

    let cancelled = false;
    const init = async () => {
      try {
        await loadSession(activeToken);
        if (!cancelled) {
          setTokenState(activeToken);
        }
      } catch {
        if (!cancelled) {
          clearToken();
          setUser(null);
          setOrganization(null);
          setRole(null);
          setTokenState(null);
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };
    void init();
    return () => {
      cancelled = true;
    };
  }, [loadSession]);

  const login = useCallback(
    async (email: string, password: string) => {
      const { access_token } = await authApi.login({ email, password });
      setToken(access_token);
      setTokenState(access_token);
      await loadSession(access_token);
    },
    [loadSession],
  );

  const register = useCallback(
    async (input: {
      email: string;
      password: string;
      full_name: string;
      organization_name: string;
    }) => {
      await authApi.register(input);
      await login(input.email, input.password);
    },
    [login],
  );

  const logout = useCallback(() => {
    clearToken();
    setTokenState(null);
    setUser(null);
    setOrganization(null);
    setRole(null);
  }, []);

  const value = useMemo(
    () => ({
      user,
      organization,
      role,
      token,
      isLoading,
      login,
      register,
      logout,
      refreshSession,
    }),
    [user, organization, role, token, isLoading, login, register, logout, refreshSession],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
