/**
 * Typed API client — the single point of HTTP communication for the frontend.
 * Components NEVER import axios or fetch directly; they use this client.
 */

import axios from 'axios';
import type { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios';
import { API_BASE_URL } from '@/config/environment';

// ─── Types ──────────────────────────────────────────────────────────────────

export interface ApiResponse<T> {
  data: T;
  status: number;
}

export interface ApiError {
  error_code: string;
  message: string;
  request_id?: string;
  detail?: string;
}

export interface RequestOptions {
  timeout?: number;
  headers?: Record<string, string>;
  params?: Record<string, unknown>;
}

export interface ApiClient {
  get<T>(path: string, options?: RequestOptions): Promise<ApiResponse<T>>;
  post<T>(path: string, body?: unknown, options?: RequestOptions): Promise<ApiResponse<T>>;
  put<T>(path: string, body?: unknown, options?: RequestOptions): Promise<ApiResponse<T>>;
  delete<T>(path: string, options?: RequestOptions): Promise<ApiResponse<T>>;
}

// ─── Constants ──────────────────────────────────────────────────────────────

const DEFAULT_TIMEOUT_MS = 30_000;
const REQUEST_ID_HEADER = 'x-request-id';

// ─── Implementation ─────────────────────────────────────────────────────────

function isAxiosError(error: unknown): error is { response?: AxiosResponse; message?: string } {
  return typeof error === 'object' && error !== null && 'isAxiosError' in error;
}

/**
 * Transforms HTTP or network failures into a structured ApiError.
 * Extracts request_id from response headers when available.
 */
function transformError(error: unknown): ApiError {
  if (isAxiosError(error)) {
    const response = error.response;

    if (response) {
      // HTTP error — server responded with a non-2xx status
      const requestId = response.headers?.[REQUEST_ID_HEADER] as string | undefined;
      const responseData = response.data as Record<string, unknown> | undefined;

      return {
        error_code: (responseData?.error_code as string) || `HTTP_${String(response.status)}`,
        message: (responseData?.message as string) || error.message || 'Request failed',
        request_id: requestId,
        detail: responseData?.detail as string | undefined,
      };
    }

    // Network error — no response received
    return {
      error_code: 'NETWORK_ERROR',
      message: error.message || 'Network error occurred',
    };
  }

  // Unknown error shape
  return {
    error_code: 'UNKNOWN_ERROR',
    message: error instanceof Error ? error.message : 'An unexpected error occurred',
  };
}

function buildAxiosConfig(options?: RequestOptions): AxiosRequestConfig {
  const config: AxiosRequestConfig = {};
  if (options?.timeout) config.timeout = options.timeout;
  if (options?.headers) config.headers = options.headers;
  if (options?.params) config.params = options.params;
  return config;
}

function createApiClient(baseURL: string = API_BASE_URL): ApiClient {
  const instance: AxiosInstance = axios.create({
    baseURL,
    timeout: DEFAULT_TIMEOUT_MS,
    headers: {
      'Content-Type': 'application/json',
    },
  });

  async function request<T>(
    method: 'get' | 'post' | 'put' | 'delete',
    path: string,
    body?: unknown,
    options?: RequestOptions,
  ): Promise<ApiResponse<T>> {
    const config = buildAxiosConfig(options);

    try {
      let response: AxiosResponse<T>;

      if (method === 'get' || method === 'delete') {
        response = await instance[method]<T>(path, config);
      } else {
        response = await instance[method]<T>(path, body, config);
      }

      return {
        data: response.data,
        status: response.status,
      };
    } catch (error: unknown) {
      throw transformError(error);
    }
  }

  return {
    get<T>(path: string, options?: RequestOptions): Promise<ApiResponse<T>> {
      return request<T>('get', path, undefined, options);
    },

    post<T>(path: string, body?: unknown, options?: RequestOptions): Promise<ApiResponse<T>> {
      return request<T>('post', path, body, options);
    },

    put<T>(path: string, body?: unknown, options?: RequestOptions): Promise<ApiResponse<T>> {
      return request<T>('put', path, body, options);
    },

    delete<T>(path: string, options?: RequestOptions): Promise<ApiResponse<T>> {
      return request<T>('delete', path, undefined, options);
    },
  };
}

// ─── Exports ────────────────────────────────────────────────────────────────

/** Default API client instance using the configured base URL */
export const apiClient: ApiClient = createApiClient();

/** Factory for creating custom API client instances (e.g., for testing) */
export { createApiClient };
