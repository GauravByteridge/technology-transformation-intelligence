import type { ReactNode } from 'react';
import { Inbox } from 'lucide-react';

interface EmptyStateProps {
  /** Message to display when no data is available */
  message?: string;
  /** Optional custom icon to replace the default inbox icon */
  icon?: ReactNode;
  /**
   * @deprecated Use message prop directly. Kept for backward compatibility.
   * When provided without message, generates "No {dataType} found".
   */
  dataType?: string;
  /** Optional children for custom call-to-action buttons or links */
  children?: ReactNode;
}

/**
 * EmptyState — displays a centered no-data message with muted styling.
 * Used when a successful API response contains zero items.
 */
export function EmptyState({
  message,
  icon,
  dataType,
  children,
}: EmptyStateProps) {
  // Resolve display message: explicit message takes priority, then dataType fallback
  const displayMessage = message ?? (dataType ? `No ${dataType} found` : 'No data available');

  return (
    <div
      className="flex flex-col items-center justify-center gap-3 rounded-lg border border-gray-200 bg-gray-50 px-6 py-8"
      role="status"
      aria-live="polite"
    >
      {icon ? (
        <span aria-hidden="true">{icon}</span>
      ) : (
        <Inbox className="h-10 w-10 text-gray-400" aria-hidden="true" />
      )}
      <p className="text-sm text-gray-500 text-center">{displayMessage}</p>
      {children && <div className="mt-2">{children}</div>}
    </div>
  );
}
