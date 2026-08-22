import { useState, useEffect, useRef } from 'react';
import { Loader2, Check } from 'lucide-react';

const PROCESSING_STEPS = [
  'Understanding question',
  'Searching project data',
  'Checking financial information',
  'Reviewing relevant documents',
  'Analyzing results',
  'Generating response',
] as const;

/** Interval between step advances in milliseconds (≤5 seconds per requirement 5.3) */
const STEP_INTERVAL_MS = 3500;

interface ProcessingIndicatorProps {
  /** Whether the processing indicator is visible/active */
  isVisible: boolean;
}

/**
 * ProcessingIndicator — displays sequential processing steps while the AI generates a response.
 * Steps advance every ~3.5 seconds (≤5s per requirement).
 * Past steps show a green checkmark, current step shows an animated spinner, future steps are gray.
 */
export function ProcessingIndicator({ isVisible }: ProcessingIndicatorProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!isVisible) {
      setCurrentStep(0);
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      return;
    }

    // Reset step when becoming visible
    setCurrentStep(0);

    intervalRef.current = setInterval(() => {
      setCurrentStep((prev) => {
        if (prev >= PROCESSING_STEPS.length - 1) {
          // Stay on last step (don't advance past the end)
          if (intervalRef.current) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
          }
          return prev;
        }
        return prev + 1;
      });
    }, STEP_INTERVAL_MS);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [isVisible]);

  if (!isVisible) {
    return null;
  }

  return (
    <div
      className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm"
      role="status"
      aria-live="polite"
      aria-label="Processing your question"
    >
      <ul className="space-y-3">
        {PROCESSING_STEPS.map((step, index) => {
          const isPast = index < currentStep;
          const isCurrent = index === currentStep;

          return (
            <li
              key={step}
              className={`flex items-center gap-3 text-sm ${
                isPast
                  ? 'text-green-700'
                  : isCurrent
                    ? 'text-blue-700 font-medium'
                    : 'text-gray-400'
              }`}
            >
              <span className="flex-shrink-0 w-5 h-5 flex items-center justify-center">
                {isPast && (
                  <Check className="w-4 h-4 text-green-600" aria-hidden="true" />
                )}
                {isCurrent && (
                  <Loader2 className="w-4 h-4 text-blue-600 animate-spin" aria-hidden="true" />
                )}
                {!isPast && !isCurrent && (
                  <span
                    className="w-2 h-2 rounded-full bg-gray-300"
                    aria-hidden="true"
                  />
                )}
              </span>
              <span>{step}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
