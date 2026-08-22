import { AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface ErrorStateProps {
  /** Error code identifying the failure category */
  error_code?: string;
  /** Error message to display */
  message?: string;
  /** Callback for retry action — renders a "Try again" button when provided */
  onRetry?: () => void;
}

/**
 * ErrorState — inline error display with failure category and optional retry.
 * All API-driven components should use this when requests fail.
 */
export function ErrorState({
  error_code,
  message = 'Something went wrong. Please try again.',
  onRetry,
}: ErrorStateProps) {
  return (
    <div
      className="flex flex-col items-center justify-center gap-3 rounded-lg border border-red-200 bg-red-50 px-6 py-8"
      role="alert"
      aria-live="assertive"
    >
      <AlertCircle className="h-8 w-8 text-red-500" aria-hidden="true" />
      {error_code && (
        <p className="text-xs font-mono text-red-400">{error_code}</p>
      )}
      <p className="text-sm font-medium text-red-700">{message}</p>
      {onRetry && (
        <Button
          variant="destructive"
          size="sm"
          onClick={onRetry}
          className="mt-2"
        >
          Try again
        </Button>
      )}
    </div>
  );
}
