import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';

export interface SectionErrorBoundaryProps {
  children: React.ReactNode;
  /** Name of the section displayed in the fallback error message */
  sectionName?: string;
}

interface SectionErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * SectionErrorBoundary — Generic error boundary for independent page sections.
 * Isolates failures so sibling sections continue rendering normally.
 * Shows an inline fallback with a contextual error message and retry button.
 */
export class SectionErrorBoundary extends React.Component<
  SectionErrorBoundaryProps,
  SectionErrorBoundaryState
> {
  constructor(props: SectionErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): SectionErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    const sectionLabel = this.props.sectionName ?? 'this section';
    console.error(`Error in section "${sectionLabel}":`, error, errorInfo);
  }

  private handleRetry = (): void => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      const sectionLabel = this.props.sectionName ?? 'this section';

      return (
        <div
          className="flex flex-col items-center justify-center gap-3 rounded-lg border border-red-200 bg-red-50 p-8"
          role="alert"
          aria-live="assertive"
        >
          <AlertCircle className="h-6 w-6 text-red-400" aria-hidden="true" />
          <p className="text-sm text-gray-700">
            Something went wrong in <span className="font-medium">{sectionLabel}</span>.
          </p>
          <button
            onClick={this.handleRetry}
            className="inline-flex items-center gap-1.5 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
            Retry
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
