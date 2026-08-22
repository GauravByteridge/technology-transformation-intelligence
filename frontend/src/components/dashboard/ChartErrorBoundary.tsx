import React from 'react';

interface ChartErrorBoundaryProps {
  children: React.ReactNode;
}

interface ChartErrorBoundaryState {
  hasError: boolean;
}

export class ChartErrorBoundary extends React.Component<
  ChartErrorBoundaryProps,
  ChartErrorBoundaryState
> {
  constructor(props: ChartErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(): ChartErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Chart render error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex items-center justify-center h-64 bg-gray-50 border border-gray-200 rounded-lg">
          <p className="text-gray-500 text-sm">Chart unavailable</p>
        </div>
      );
    }

    return this.props.children;
  }
}
