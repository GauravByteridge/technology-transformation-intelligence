import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';

export interface ChartErrorBoundaryProps {
  children: React.ReactNode;
  /** Optional custom fallback UI. When provided, overrides the default error display. */
  fallback?: React.ReactNode;
}

interface ChartErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * ChartErrorBoundary — React class component implementing componentDidCatch
 * to catch rendering errors in chart children. Shows a fallback UI with an
 * error message and retry button, or a custom fallback if provided.
 */
export class ChartErrorBoundary extends React.Component<
  ChartErrorBoundaryProps,
  ChartErrorBoundaryState
> {
  constructor(props: ChartErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ChartErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Chart render error:', error, errorInfo);
  }

  private handleRetry = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div
          className="flex flex-col items-center justify-center gap-3 h-64 bg-gray-50 border border-gray-200 rounded-lg"
          role="alert"
        >
          <AlertCircle className="h-6 w-6 text-red-400" aria-hidden="true" />
          <p className="text-gray-600 text-sm">
            Something went wrong rendering this chart.
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
