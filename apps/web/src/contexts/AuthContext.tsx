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
  type AuthUser,
  clearTokens,
  extractUserFromToken,
  getAccessToken,
  hasRefreshToken,
  refreshAccessToken,
  setTokens,
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

  // Register auth handlers for the API client
  useEffect(() => {
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

      // Redirect based on whether user has an organization
      if (loggedInUser?.organizationId && loggedInUser?.orgSlug) {
        router.push(`/${loggedInUser.orgSlug}/dashboard`);
      } else {
        router.push("/register/organization");
      }
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
      const slug = createdUser?.orgSlug;
      if (slug) {
        router.push(`/${slug}/dashboard`);
      }
    },
    [router],
  );

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
