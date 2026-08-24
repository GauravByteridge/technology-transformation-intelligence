import { AlertCircle } from 'lucide-react';
import type { ReactNode } from 'react';

export type KPIFormat = 'number' | 'currency' | 'percent';

export interface KPICardProps {
  /** Label displayed above the value */
  label: string;
  /** Numeric value or null/undefined for missing data */
  value: number | null | undefined;
  /** How to format the value */
  format?: KPIFormat;
  /** Icon element rendered in the card */
  icon?: ReactNode;
  /** Accent color class applied to the icon background */
  color?: string;
  /** Whether the card is in a loading state */
  isLoading?: boolean;
  /** Whether the card is in an error state */
  isError?: boolean;
  /** Retry handler for error state */
  onRetry?: () => void;
}

function formatValue(value: number, format: KPIFormat): string {
  const num = Number(value) || 0;
  switch (format) {
    case 'currency':
      if (num >= 1_000_000) {
        return `$${(num / 1_000_000).toFixed(1)}M`;
      }
      if (num >= 1_000) {
        return `$${(num / 1_000).toFixed(0)}K`;
      }
      return `$${num.toLocaleString()}`;
    case 'percent':
      return `${num.toFixed(1)}%`;
    case 'number':
    default:
      return num.toLocaleString();
  }
}

/**
 * KPICard — displays a single KPI metric with loading, error, and empty states.
 * Shows a loading skeleton shimmer while fetching.
 * Shows "—" placeholder when value is null/undefined (never shows zero for missing data).
 * Shows an error indicator with optional retry on failure.
 */
export function KPICard({
  label,
  value,
  format = 'number',
  icon,
  color = 'bg-blue-100 text-blue-600',
  isLoading = false,
  isError = false,
  onRetry,
}: KPICardProps) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm transition-shadow hover:shadow-md">
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-500 truncate">{label}</p>
          <div className="mt-2">
            {isLoading && <LoadingSkeleton />}
            {isError && !isLoading && <ErrorIndicator onRetry={onRetry} />}
            {!isLoading && !isError && (
              <p className="text-2xl font-bold text-gray-900" aria-label={`${label}: ${value == null ? 'No data available' : formatValue(value, format)}`}>
                {value == null ? '—' : formatValue(value, format)}
              </p>
            )}
          </div>
        </div>
        {icon && (
          <div className={`flex-shrink-0 rounded-lg p-2.5 ${color}`} aria-hidden="true">
            {icon}
          </div>
        )}
      </div>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="h-4 w-16 rounded bg-gray-200 animate-pulse" role="status" aria-label="Loading">
      <span className="sr-only">Loading...</span>
    </div>
  );
}

function ErrorIndicator({ onRetry }: { onRetry?: () => void }) {
  return (
    <div className="flex items-center gap-2" role="alert">
      <AlertCircle className="h-4 w-4 text-red-500" />
      <span className="text-sm text-red-600">Failed</span>
      {onRetry && (
        <button
          onClick={onRetry}
          className="ml-1 text-xs text-red-600 underline hover:text-red-800 focus:outline-none focus:ring-1 focus:ring-red-500 rounded"
        >
          Retry
        </button>
      )}
    </div>
  );
}
