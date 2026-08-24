import { AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';

type ErrorVariant = 'inline' | 'full-page';

interface ErrorStateProps {
  /** Error message to display */
  message?: string;
  /** Callback for retry action — renders a "Try Again" button when provided */
  onRetry?: () => void;
  /** Display variant: inline for cards/sections, full-page for full container height */
  variant?: ErrorVariant;
}

/**
 * ErrorState — error display with optional retry action and accessibility support.
 * Use inline variant within cards/sections, full-page for route-level errors.
 */
export function ErrorState({
  message = 'Something went wrong. Please try again.',
  onRetry,
  variant = 'inline',
}: ErrorStateProps) {
  const containerClass =
    variant === 'full-page'
      ? 'flex min-h-[400px] w-full flex-col items-center justify-center gap-3 px-6'
      : 'flex flex-col items-center justify-center gap-3 rounded-lg border border-red-200 bg-red-50 px-6 py-8';

  return (
    <div className={containerClass} role="alert" aria-live="assertive">
      <AlertTriangle className="h-8 w-8 text-red-500" aria-hidden="true" />
      <p className="text-sm font-medium text-red-700 text-center">{message}</p>
      {onRetry && (
        <Button
          variant="destructive"
          size="sm"
          onClick={onRetry}
          className="mt-2"
        >
          Try Again
        </Button>
      )}
    </div>
  );
}
