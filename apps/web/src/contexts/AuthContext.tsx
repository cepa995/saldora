"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { useRouter } from "next/navigation";
import {
  apiClient,
  apiFormPost,
  registerAuthHandlers,
} from "@/lib/api-client";
import {
  type AuthTokens,
  clearTokens,
  extractUserFromToken,
  getAccessToken,
  hasRefreshToken,
  postAuthRoute,
  refreshAccessToken,
  setTokens,
  type AuthUser,
} from "@/lib/auth";

interface RegisterData {
  email: string;
  password: string;
  firstName?: string;
  lastName?: string;
}

const ROLE_HIERARCHY: Record<string, number> = {
  admin: 4,
  manager: 3,
  operator: 2,
  viewer: 1,
};

interface AuthContextType {
  user: AuthUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => Promise<void>;
  requestPasswordReset: (email: string) => Promise<string>;
  confirmPasswordReset: (token: string, newPassword: string) => Promise<string>;
  createOrganization: (name: string, pib?: string) => Promise<void>;
  /**
   * Force a token refresh and update the in-memory user state. The
   * /auth/refresh endpoint re-reads the org's subscription_status from
   * the DB on every call, so this is the polling primitive used by the
   * /awaiting-approval page to detect activation without a hard reload.
   */
  refreshUser: () => Promise<AuthUser | null>;
  hasRole: (minimumRole: string) => boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  const handleAuthFailed = useCallback(() => {
    clearTokens();
    setUser(null);
    router.push("/login");
  }, [router]);

  // Register auth handlers synchronously during render (via useMemo) so they
  // are live before any child component's useEffect fires. Registering in a
  // useEffect caused a race where children (ClientContext, workspace page)
  // would fire fetch calls in their mount effect before the token getter was
  // set, producing 401s on the first request.
  useMemo(() => {
    registerAuthHandlers({
      getAccessToken,
      refreshTokens: refreshAccessToken,
      onAuthFailed: handleAuthFailed,
    });
  }, [handleAuthFailed]);

  // Attempt silent refresh on mount
  useEffect(() => {
    async function initAuth() {
      if (!hasRefreshToken()) {
        setIsLoading(false);
        return;
      }
      try {
        const token = await refreshAccessToken();
        if (token) {
          setUser(extractUserFromToken(token));
        }
      } catch {
        clearTokens();
      } finally {
        setIsLoading(false);
      }
    }
    initAuth();
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      const tokens = await apiFormPost<AuthTokens>("/api/v1/auth/login", {
        username: email,
        password,
      });
      setTokens(tokens);
      const loggedInUser = extractUserFromToken(tokens.access_token);
      setUser(loggedInUser);
      router.push(postAuthRoute(loggedInUser));
    },
    [router],
  );

  const register = useCallback(
    async (data: RegisterData) => {
      const tokens = await apiClient<AuthTokens>("/api/v1/auth/register", {
        method: "POST",
        body: JSON.stringify({
          email: data.email,
          password: data.password,
          first_name: data.firstName,
          last_name: data.lastName,
        }),
      });
      setTokens(tokens);
      setUser(extractUserFromToken(tokens.access_token));
      router.push("/register/organization");
    },
    [router],
  );

  const createOrganization = useCallback(
    async (name: string, pib?: string) => {
      const tokens = await apiClient<AuthTokens>(
        "/api/v1/auth/create-organization",
        {
          method: "POST",
          body: JSON.stringify({ name, pib: pib || null }),
        },
      );
      setTokens(tokens);
      const createdUser = extractUserFromToken(tokens.access_token);
      setUser(createdUser);
      // Fresh orgs land in subscription_status="pending" — postAuthRoute
      // will send them to /awaiting-approval rather than /dashboard.
      router.push(postAuthRoute(createdUser));
    },
    [router],
  );

  const refreshUser = useCallback(async (): Promise<AuthUser | null> => {
    const token = await refreshAccessToken();
    if (!token) {
      setUser(null);
      return null;
    }
    const refreshed = extractUserFromToken(token);
    setUser(refreshed);
    return refreshed;
  }, []);

  const logout = useCallback(async () => {
    try {
      await apiClient("/api/v1/auth/logout", { method: "POST" });
    } catch {
      // Logout even if the API call fails
    }
    clearTokens();
    setUser(null);
    router.push("/login");
  }, [router]);

  const requestPasswordReset = useCallback(async (email: string) => {
    const result = await apiClient<{ message: string }>(
      "/api/v1/auth/password-reset/request",
      {
        method: "POST",
        body: JSON.stringify({ email }),
      },
      true,
    );
    return result.message;
  }, []);

  const confirmPasswordReset = useCallback(
    async (token: string, newPassword: string) => {
      const result = await apiClient<{ message: string }>(
        "/api/v1/auth/password-reset/confirm",
        {
          method: "POST",
          body: JSON.stringify({ token, new_password: newPassword }),
        },
        true,
      );
      return result.message;
    },
    [],
  );

  const hasRole = useCallback(
    (minimumRole: string): boolean => {
      if (!user) return false;
      const userLevel = ROLE_HIERARCHY[user.role] ?? 0;
      const requiredLevel = ROLE_HIERARCHY[minimumRole] ?? 999;
      return userLevel >= requiredLevel;
    },
    [user],
  );

  const value = useMemo(
    () => ({
      user,
      isLoading,
      isAuthenticated: !!user,
      login,
      register,
      logout,
      requestPasswordReset,
      confirmPasswordReset,
      createOrganization,
      refreshUser,
      hasRole,
    }),
    [
      user,
      isLoading,
      login,
      register,
      logout,
      requestPasswordReset,
      confirmPasswordReset,
      createOrganization,
      refreshUser,
      hasRole,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
