import { Loader2 } from 'lucide-react';

interface LoadingStateProps {
  /** Optional message to display below the spinner */
  message?: string;
  /** Size variant for the spinner */
  size?: 'sm' | 'md' | 'lg';
}

const sizeClasses: Record<string, string> = {
  sm: 'h-4 w-4',
  md: 'h-6 w-6',
  lg: 'h-10 w-10',
};

/**
 * LoadingState — standard loading indicator with accessibility support.
 * All API-driven components should use this during data fetching.
 */
export function LoadingState({ message = 'Loading...', size = 'md' }: LoadingStateProps) {
  return (
    <div
      className="flex flex-col items-center justify-center gap-3 py-8"
      role="status"
      aria-busy="true"
      aria-live="polite"
      aria-label={message}
    >
      <Loader2 className={`${sizeClasses[size]} animate-spin text-blue-600`} />
      <p className="text-sm text-gray-500">{message}</p>
    </div>
  );
}
