/**
 * Typed API Client for FastAPI Backend.
 * 
 * Centralizes all network requests made by the frontend.
 * Automatically attaches:
 * - Supabase JWT bearer tokens for trainer requests.
 * - Error formatting with user-friendly error messages.
 */

/**
 * Chooses the backend URL once for every API request in this module.
 *
 * Local development stays convenient, but a production build stops immediately
 * when its public API URL is missing so a deployed browser can never call localhost.
 */
function resolveApiBaseUrl(): string {
  const configuredUrl = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (configuredUrl) {
    return configuredUrl.replace(/\/+$/, "");
  }

  if (process.env.NODE_ENV === "production") {
    throw new Error(
      "Missing required production configuration: NEXT_PUBLIC_API_URL must point to the backend /api/v1 URL.",
    );
  }

  return "http://localhost:8000/api/v1";
}

const API_BASE_URL = resolveApiBaseUrl();

/** An error response from the API, keeping the HTTP status so callers can react to it. */
export class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
  }
}

interface FetchOptions extends RequestInit {
  token?: string;
}

export async function apiFetch<T>(endpoint: string, options: FetchOptions = {}): Promise<T> {
  const { token, headers = {}, ...customConfig } = options;

  const defaultHeaders: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (token) {
    defaultHeaders["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...customConfig,
    headers: {
      ...defaultHeaders,
      ...(headers as Record<string, string>),
    },
  });

  if (!response.ok) {
    let errorDetail = "An unexpected server error occurred.";
    try {
      const errorJson = await response.json();
      errorDetail = errorJson.detail || errorDetail;
    } catch {
      // Fallback to HTTP status text if response is not JSON
      errorDetail = response.statusText || errorDetail;
    }
    throw new ApiError(errorDetail, response.status);
  }

  return response.json() as Promise<T>;
}
