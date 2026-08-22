import type { ReactNode } from 'react';
import { Inbox } from 'lucide-react';

interface EmptyStateProps {
  /** The type of data that is expected but not available (e.g., "projects", "documents") */
  dataType: string;
  /** Optional additional message below the main heading */
  message?: string;
  /** Optional children for custom call-to-action buttons or links */
  children?: ReactNode;
}

/**
 * EmptyState — displays a no-data message identifying the expected data type.
 * All API-driven components should use this when a successful response contains zero items.
 */
export function EmptyState({ dataType, message, children }: EmptyStateProps) {
  return (
    <div
      className="flex flex-col items-center justify-center gap-3 rounded-lg border border-gray-200 bg-gray-50 px-6 py-8"
      role="status"
      aria-live="polite"
    >
      <Inbox className="h-10 w-10 text-gray-400" aria-hidden="true" />
      <p className="text-sm font-medium text-gray-600">
        No {dataType} found
      </p>
      {message && (
        <p className="text-xs text-gray-500">{message}</p>
      )}
      {children && (
        <div className="mt-2">{children}</div>
      )}
    </div>
  );
}
