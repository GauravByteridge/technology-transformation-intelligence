import { useState } from 'react';
import { Info } from 'lucide-react';
import type { PartialFailureInfo } from '../types';

interface PartialFailureWarningProps {
  failedSources: PartialFailureInfo[];
}

/**
 * PartialFailureWarning — compact info icon with tooltip/popover showing
 * which sources were unavailable during the AI response.
 */
export function PartialFailureWarning({ failedSources }: PartialFailureWarningProps) {
  const [showDetails, setShowDetails] = useState(false);

  if (!failedSources || failedSources.length === 0) {
    return null;
  }

  return (
    <div className="relative inline-block">
      <button
        onClick={() => setShowDetails(!showDetails)}
        className="flex items-center gap-1.5 text-xs text-amber-400/80 hover:text-amber-400 transition-colors"
        aria-label="Some sources were unavailable"
        title="Some sources were unavailable"
      >
        <Info size={14} />
        <span>{failedSources.length} source{failedSources.length > 1 ? 's' : ''} unavailable</span>
      </button>

      {showDetails && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setShowDetails(false)} />
          <div className="absolute bottom-full left-0 mb-2 z-20 w-72 bg-gray-800 border border-gray-700 rounded-lg shadow-xl p-3">
            <p className="text-xs font-medium text-gray-300 mb-2">Unavailable sources:</p>
            <ul className="space-y-1">
              {failedSources.map((failure, index) => (
                <li key={index} className="text-xs text-gray-400">
                  <span className="text-gray-300">{failure.source}</span>
                  {failure.error && <span className="text-gray-500"> — {failure.error}</span>}
                </li>
              ))}
            </ul>
          </div>
        </>
      )}
    </div>
  );
}
