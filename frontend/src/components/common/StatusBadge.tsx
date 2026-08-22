import type { DataSourceStatusValue } from '../../types';

interface StatusBadgeProps {
  /** The status value to display */
  status: DataSourceStatusValue;
}

const statusConfig: Record<DataSourceStatusValue, { label: string; className: string }> = {
  Connected: {
    label: 'Connected',
    className: 'bg-green-100 text-green-800 border-green-200',
  },
  Syncing: {
    label: 'Syncing',
    className: 'bg-amber-100 text-amber-800 border-amber-200',
  },
  Error: {
    label: 'Error',
    className: 'bg-red-100 text-red-800 border-red-200',
  },
};

/**
 * StatusBadge — color-coded badge for data source status.
 * - Green for Connected
 * - Amber for Syncing
 * - Red for Error
 */
export function StatusBadge({ status }: StatusBadgeProps) {
  const config = statusConfig[status];

  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${config.className}`}
      role="status"
      aria-label={`Status: ${config.label}`}
    >
      <span
        className={`mr-1.5 h-2 w-2 rounded-full ${
          status === 'Connected'
            ? 'bg-green-500'
            : status === 'Syncing'
              ? 'bg-amber-500'
              : 'bg-red-500'
        }`}
        aria-hidden="true"
      />
      {config.label}
    </span>
  );
}
