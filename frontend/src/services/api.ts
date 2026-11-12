import axios from "axios";
import type { ApiError } from "../types";

let getToken: () => string | null = () => null;
let onUnauthorized: () => void = () => undefined;

/** Registered once by the auth store; kept here to avoid import cycles. */
export function configureAuth(token: () => string | null, unauthorized: () => void): void {
  getToken = token;
  onUnauthorized = unauthorized;
}

/** Turn anything thrown by axios into the app's error shape. */
export function toApiError(error: unknown): ApiError {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as { detail?: unknown; code?: unknown } | undefined;
    return {
      status: error.response?.status ?? 0,
      code: typeof data?.code === "string" ? data.code : null,
      message: typeof data?.detail === "string" ? data.detail : error.message,
    };
  }
  return { status: 0, code: null, message: String(error) };
}

export const api = axios.create({ baseURL: "/api", headers: { "Content-Type": "application/json" } });

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.set("Authorization", `Bearer ${token}`);
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    const apiError = toApiError(error);
    const url = axios.isAxiosError(error) ? error.config?.url : undefined;
    if (apiError.status === 401 && url !== "/auth/login") {
      onUnauthorized();
    }
    return Promise.reject(apiError);
  },
);
