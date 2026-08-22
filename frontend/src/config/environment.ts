/**
 * Centralized environment configuration for the frontend application.
 * All environment-specific values are read from VITE_* env vars with sensible defaults.
 */

export type Environment = 'development' | 'production';

/**
 * API base URL for backend communication.
 * Empty string default allows the Vite dev proxy to handle /api routes in development.
 */
export const API_BASE_URL: string =
  import.meta.env.VITE_API_BASE_URL || '';

/**
 * Feature flags controlling optional capabilities.
 * Each flag reads from a VITE_* env var, defaulting to enabled.
 */
export const FEATURE_FLAGS = {
  enableAiChat: import.meta.env.VITE_ENABLE_AI_CHAT !== 'false',
  enableDocumentUpload: import.meta.env.VITE_ENABLE_DOCUMENT_UPLOAD !== 'false',
  enableDataSources: import.meta.env.VITE_ENABLE_DATA_SOURCES !== 'false',
} as const;

/**
 * Current application environment.
 * Reads VITE_APP_ENV first, falls back to Vite's built-in MODE.
 */
export const ENVIRONMENT: Environment =
  (import.meta.env.VITE_APP_ENV as Environment) || (import.meta.env.MODE as Environment) || 'development';

/** Whether the app is running in development mode */
export const IS_DEVELOPMENT: boolean = ENVIRONMENT === 'development';

/** Whether the app is running in production mode */
export const IS_PRODUCTION: boolean = ENVIRONMENT === 'production';
