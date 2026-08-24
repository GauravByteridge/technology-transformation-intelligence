import { AlertTriangle } from 'lucide-react';
import type { PartialFailureInfo } from '../types';

interface PartialFailureWarningProps {
  failedSources: PartialFailureInfo[];
}

/**
 * PartialFailureWarning — displays an amber warning banner when an AI response
 * was generated with partial data due to one or more source failures.
 *
 * Renders nothing if failedSources is empty.
 *
 * Validates: Requirements 13.6, 10.2
 */
export function PartialFailureWarning({ failedSources }: PartialFailureWarningProps) {
  if (!failedSources || failedSources.length === 0) {
    return null;
  }

  return (
    <div
      role="alert"
      className="rounded-lg border border-amber-300 bg-amber-50 px-4 py-3"
    >
      <div className="flex items-start gap-3">
        <AlertTriangle
          className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5"
          aria-hidden="true"
        />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-amber-800">
            Partial results — some sources were unavailable
          </p>
          <ul className="mt-2 space-y-1">
            {failedSources.map((failure, index) => (
              <li
                key={`${failure.source}-${index}`}
                className="text-sm text-amber-700 flex items-start gap-2"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 flex-shrink-0 mt-1.5" />
                <span>
                  <span className="font-medium">{failure.source}</span>
                  {failure.error && (
                    <span className="text-amber-600"> — {failure.error}</span>
                  )}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
