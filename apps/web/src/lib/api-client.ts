const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface ApiError {
  status: number;
  message: string;
  detail?: string;
}

let getAccessTokenFn: (() => string | null) | null = null;
let refreshTokensFn: (() => Promise<string | null>) | null = null;
let onAuthFailedFn: (() => void) | null = null;

export function registerAuthHandlers(handlers: {
  getAccessToken: () => string | null;
  refreshTokens: () => Promise<string | null>;
  onAuthFailed: () => void;
}) {
  getAccessTokenFn = handlers.getAccessToken;
  refreshTokensFn = handlers.refreshTokens;
  onAuthFailedFn = handlers.onAuthFailed;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const error: ApiError = {
      status: response.status,
      message: body?.detail || response.statusText,
      detail: typeof body?.detail === "string" ? body.detail : undefined,
    };
    throw error;
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}

export async function apiClient<T>(
  endpoint: string,
  options: RequestInit = {},
  skipAuth = false,
): Promise<T> {
  const headers = new Headers(options.headers);

  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  if (!skipAuth) {
    const token = getAccessTokenFn?.();
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }
  }

  let response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  // On 401, attempt token refresh and retry once
  if (response.status === 401 && !skipAuth && refreshTokensFn) {
    const newToken = await refreshTokensFn().catch(() => null);
    if (newToken) {
      headers.set("Authorization", `Bearer ${newToken}`);
      response = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers,
      });
    } else {
      onAuthFailedFn?.();
    }
  }

  return handleResponse<T>(response);
}

export async function apiFormPost<T>(
  endpoint: string,
  data: Record<string, string>,
): Promise<T> {
  const body = new URLSearchParams(data);
  return apiClient<T>(
    endpoint,
    {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body,
    },
    true,
  );
}

/**
 * Download a binary file from the API (e.g. export endpoints).
 *
 * Uses the same auth/401-retry logic as apiClient but returns a Blob
 * instead of parsed JSON. Error responses are still parsed as JSON.
 *
 * @param endpoint - API endpoint path.
 * @param options - Fetch options (method, body, etc.).
 * @returns Object with blob data and extracted filename.
 */
export async function apiDownload(
  endpoint: string,
  options: RequestInit = {},
): Promise<{ blob: Blob; filename: string }> {
  const headers = new Headers(options.headers);

  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const token = getAccessTokenFn?.();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  let response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (response.status === 401 && refreshTokensFn) {
    const newToken = await refreshTokensFn().catch(() => null);
    if (newToken) {
      headers.set("Authorization", `Bearer ${newToken}`);
      response = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers,
      });
    } else {
      onAuthFailedFn?.();
    }
  }

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const error: ApiError & { blockedInvoices?: unknown[] } = {
      status: response.status,
      message: body?.detail?.message || body?.detail || response.statusText,
      detail: typeof body?.detail === "string" ? body.detail : undefined,
    };
    if (response.status === 422 && body?.detail?.blocked_invoices) {
      error.blockedInvoices = body.detail.blocked_invoices;
    }
    throw error;
  }

  const blob = await response.blob();

  const disposition = response.headers.get("Content-Disposition") || "";
  const filenameMatch = disposition.match(/filename="?([^";\n]+)"?/);
  const filename = filenameMatch?.[1] || "fakture_izvoz";

  return { blob, filename };
}
