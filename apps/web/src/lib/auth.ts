import { apiClient } from "./api-client";

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface AuthUser {
  id: string;
  email: string;
  firstName: string | null;
  lastName: string | null;
  organizationId: string | null;
  orgSlug: string | null;
  role: string;
  emailVerified: boolean;
}

// In-memory access token — never persisted to localStorage
let accessToken: string | null = null;

const REFRESH_TOKEN_KEY = "saldora_refresh_token";
const SESSION_COOKIE = "saldora_logged_in";

export function getAccessToken(): string | null {
  return accessToken;
}

export function setTokens(tokens: AuthTokens): void {
  accessToken = tokens.access_token;
  localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
  setSessionCookie();
}

export function clearTokens(): void {
  accessToken = null;
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  clearSessionCookie();
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function hasRefreshToken(): boolean {
  return getRefreshToken() !== null;
}

function setSessionCookie(): void {
  // 7-day cookie, accessible by middleware
  document.cookie = `${SESSION_COOKIE}=true; path=/; max-age=604800; SameSite=Lax`;
}

function clearSessionCookie(): void {
  document.cookie = `${SESSION_COOKIE}=; path=/; max-age=0`;
}

export async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return null;

  try {
    const tokens = await apiClient<AuthTokens>(
      "/api/v1/auth/refresh",
      {
        method: "POST",
        body: JSON.stringify({ refresh_token: refreshToken }),
      },
      true, // skip auth — this IS the auth refresh
    );
    setTokens(tokens);
    return tokens.access_token;
  } catch {
    clearTokens();
    return null;
  }
}

export function parseJwtPayload(token: string): Record<string, unknown> {
  const base64 = token.split(".")[1];
  const json = atob(base64.replace(/-/g, "+").replace(/_/g, "/"));
  return JSON.parse(json);
}

export function extractUserFromToken(token: string): AuthUser | null {
  try {
    const payload = parseJwtPayload(token);
    return {
      id: payload.sub as string,
      email: (payload.email as string) || "",
      firstName: (payload.first_name as string) || null,
      lastName: (payload.last_name as string) || null,
      organizationId: (payload.org as string) || null,
      orgSlug: (payload.org_slug as string) || null,
      role: (payload.role as string) || "member",
      emailVerified: (payload.email_verified as boolean) ?? false,
    };
  } catch {
    return null;
  }
}
