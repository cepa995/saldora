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
  organizationName?: string;
}

interface UserResponse {
  id: string;
  email: string;
  first_name: string | null;
  last_name: string | null;
  organization_id: string;
  role: string;
  email_verified: boolean;
}

interface AuthContextType {
  user: AuthUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => Promise<void>;
  requestPasswordReset: (email: string) => Promise<string>;
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
      setUser(extractUserFromToken(tokens.access_token));
      router.push("/dashboard");
    },
    [router],
  );

  const register = useCallback(
    async (data: RegisterData) => {
      await apiClient<UserResponse>("/api/v1/auth/register", {
        method: "POST",
        body: JSON.stringify({
          email: data.email,
          password: data.password,
          first_name: data.firstName,
          last_name: data.lastName,
          organization_name: data.organizationName,
        }),
      });
      router.push("/login?registered=true");
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

  const value = useMemo(
    () => ({
      user,
      isLoading,
      isAuthenticated: !!user,
      login,
      register,
      logout,
      requestPasswordReset,
    }),
    [user, isLoading, login, register, logout, requestPasswordReset],
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
