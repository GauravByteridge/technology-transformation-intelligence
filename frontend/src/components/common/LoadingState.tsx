import { Loader2 } from 'lucide-react';

type LoadingVariant = 'inline' | 'skeleton' | 'full-page';

interface LoadingStateProps {
  /** Display variant: inline spinner, skeleton placeholders, or full-page centered */
  variant?: LoadingVariant;
  /** Optional message displayed alongside the loading indicator */
  message?: string;
  /**
   * @deprecated Use variant instead. Kept for backward compatibility.
   * 'sm' maps to inline, 'lg' maps to full-page.
   */
  size?: 'sm' | 'md' | 'lg';
}

/**
 * LoadingState — configurable loading indicator with accessibility support.
 * Supports three display modes for different layout contexts:
 * - inline: Small spinner for cards/sections
 * - skeleton: Placeholder blocks for table/list loading
 * - full-page: Centered spinner taking full container height
 */
export function LoadingState({ variant, message, size }: LoadingStateProps) {
  // Resolve variant from deprecated size prop if variant not explicitly set
  const resolvedVariant: LoadingVariant = variant ?? (size === 'lg' ? 'full-page' : 'inline');

  if (resolvedVariant === 'skeleton') {
    return (
      <div
        className="w-full space-y-3 py-4"
        role="status"
        aria-busy="true"
        aria-label={message || 'Loading content'}
      >
        <div className="h-4 w-3/4 animate-pulse rounded bg-gray-200" />
        <div className="h-4 w-1/2 animate-pulse rounded bg-gray-200" />
        <div className="h-4 w-5/6 animate-pulse rounded bg-gray-200" />
        <div className="h-4 w-2/3 animate-pulse rounded bg-gray-200" />
        <span className="sr-only">{message || 'Loading content'}</span>
      </div>
    );
  }

  if (resolvedVariant === 'full-page') {
    return (
      <div
        className="flex min-h-[400px] w-full flex-col items-center justify-center gap-3"
        role="status"
        aria-busy="true"
        aria-label={message || 'Loading'}
      >
        <Loader2 className="h-10 w-10 animate-spin text-blue-600" />
        {message && <p className="text-sm text-gray-500">{message}</p>}
      </div>
    );
  }

  // Default: inline variant
  return (
    <div
      className="flex items-center justify-center gap-2 py-4"
      role="status"
      aria-busy="true"
      aria-label={message || 'Loading'}
    >
      <Loader2 className="h-5 w-5 animate-spin text-blue-600" />
      {message && <p className="text-sm text-gray-500">{message}</p>}
    </div>
  );
}
