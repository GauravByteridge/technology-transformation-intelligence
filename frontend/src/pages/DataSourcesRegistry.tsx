import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useDataSources } from '@/hooks';
import { LoadingState, ErrorState, EmptyState } from '@/components/common';
import { triggerDiscovery } from '@/features/catalog/services/catalogService';
import type { DataSourceResponse } from '@/types';
import type { DiscoveryResult } from '@/features/catalog/types';

// ─── Discovery Status ───────────────────────────────────────────────────────

type DiscoveryPhase = 'connecting' | 'discovering' | 'cataloging' | 'ready' | 'error' | 'pending';

const DISCOVERY_STATUS_LABELS: Record<DiscoveryPhase, string> = {
  connecting: 'Connecting',
  discovering: 'Discovering',
  cataloging: 'Cataloging',
  ready: 'Ready',
  error: 'Error',
  pending: 'Pending',
};

const DISCOVERY_STATUS_STYLES: Record<DiscoveryPhase, string> = {
  connecting: 'bg-blue-100 text-blue-800',
  discovering: 'bg-indigo-100 text-indigo-800',
  cataloging: 'bg-purple-100 text-purple-800',
  ready: 'bg-green-100 text-green-800',
  error: 'bg-red-100 text-red-800',
  pending: 'bg-gray-100 text-gray-800',
};

/** Ordered discovery phases for the progress indicator */
const DISCOVERY_PROGRESS_STEPS: DiscoveryPhase[] = ['connecting', 'discovering', 'cataloging', 'ready'];

// ─── Connection Status ──────────────────────────────────────────────────────

const STATUS_BADGE_STYLES: Record<string, string> = {
  connected: 'bg-green-100 text-green-800',
  syncing: 'bg-yellow-100 text-yellow-800',
  error: 'bg-red-100 text-red-800',
};

const DEFAULT_BADGE_STYLE = 'bg-gray-100 text-gray-800';

// ─── Helpers ────────────────────────────────────────────────────────────────

/**
 * Format a timestamp as relative time (e.g. "2 hours ago") if within 24 hours,
 * or as an absolute date string for older timestamps.
 */
function formatTimestamp(isoTimestamp: string | null): string {
  if (!isoTimestamp) return '—';

  const date = new Date(isoTimestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMinutes = Math.floor(diffMs / (1000 * 60));

  if (diffMinutes < 1) return 'just now';
  if (diffMinutes < 60) {
    return diffMinutes === 1 ? '1 minute ago' : `${diffMinutes} minutes ago`;
  }

  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) {
    return diffHours === 1 ? '1 hour ago' : `${diffHours} hours ago`;
  }

  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
}

function normalizeDiscoveryStatus(status: string): DiscoveryPhase {
  const normalized = status.toLowerCase();
  if (normalized in DISCOVERY_STATUS_LABELS) {
    return normalized as DiscoveryPhase;
  }
  return 'pending';
}

// ─── Sub-components ─────────────────────────────────────────────────────────

function ConnectionStatusBadge({ status }: { status: string }) {
  const normalizedStatus = status.toLowerCase();
  const badgeStyle = STATUS_BADGE_STYLES[normalizedStatus] ?? DEFAULT_BADGE_STYLE;

  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${badgeStyle}`}>
      {status}
    </span>
  );
}

function DiscoveryStatusBadge({ status }: { status: string }) {
  const phase = normalizeDiscoveryStatus(status);
  const style = DISCOVERY_STATUS_STYLES[phase];
  const label = DISCOVERY_STATUS_LABELS[phase];

  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${style}`}>
      {label}
    </span>
  );
}

/** Visual progress indicator showing the discovery pipeline steps */
function DiscoveryProgressIndicator({ currentStatus }: { currentStatus: string }) {
  const currentPhase = normalizeDiscoveryStatus(currentStatus);
  const currentIndex = DISCOVERY_PROGRESS_STEPS.indexOf(currentPhase);

  // Only show progress when actively discovering
  const isActive = currentIndex >= 0 && currentPhase !== 'pending' && currentPhase !== 'error';

  if (!isActive) return null;

  return (
    <div className="flex items-center gap-1 mt-1" role="progressbar" aria-label="Discovery progress">
      {DISCOVERY_PROGRESS_STEPS.map((step, index) => {
        const isCompleted = index < currentIndex;
        const isCurrent = index === currentIndex;

        return (
          <div key={step} className="flex items-center">
            <div
              className={`h-2 w-2 rounded-full transition-colors ${
                isCompleted
                  ? 'bg-green-500'
                  : isCurrent
                    ? 'bg-blue-500 animate-pulse'
                    : 'bg-gray-300'
              }`}
              title={DISCOVERY_STATUS_LABELS[step]}
            />
            {index < DISCOVERY_PROGRESS_STEPS.length - 1 && (
              <div
                className={`h-0.5 w-3 ${
                  isCompleted ? 'bg-green-500' : 'bg-gray-300'
                }`}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

interface DiscoverButtonProps {
  sourceId: string;
  connectionStatus: string;
  onDiscoveryComplete: () => void;
}

function DiscoverButton({ sourceId, connectionStatus, onDiscoveryComplete }: DiscoverButtonProps) {
  const [lastResult, setLastResult] = useState<DiscoveryResult | null>(null);

  const mutation = useMutation<DiscoveryResult, Error, string>({
    mutationFn: (id: string) => triggerDiscovery(id),
    onSuccess: (result) => {
      setLastResult(result);
      onDiscoveryComplete();
    },
  });

  const isConnected = connectionStatus.toLowerCase() === 'connected';

  return (
    <div className="flex flex-col items-start gap-1">
      <button
        type="button"
        onClick={() => mutation.mutate(sourceId)}
        disabled={mutation.isPending || !isConnected}
        className={`inline-flex items-center rounded-md px-3 py-1.5 text-xs font-medium transition-colors
          ${
            mutation.isPending
              ? 'bg-indigo-100 text-indigo-600 cursor-wait'
              : !isConnected
                ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                : 'bg-indigo-600 text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-1'
          }`}
        aria-label={`Discover schema for this data source`}
      >
        {mutation.isPending ? (
          <>
            <svg className="animate-spin -ml-0.5 mr-1.5 h-3 w-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" aria-hidden="true">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Discovering…
          </>
        ) : (
          'Discover Schema'
        )}
      </button>

      {mutation.isError && (
        <p className="text-xs text-red-600" role="alert">
          Discovery failed. Please retry.
        </p>
      )}

      {lastResult && lastResult.success && (
        <p className="text-xs text-green-700">
          Found {lastResult.objects_discovered} objects, {lastResult.fields_discovered} fields
        </p>
      )}

      {lastResult && !lastResult.success && lastResult.error && (
        <p className="text-xs text-red-600" role="alert">
          {lastResult.error}
        </p>
      )}
    </div>
  );
}

// ─── Main Component ─────────────────────────────────────────────────────────

export default function DataSourcesRegistry() {
  const queryClient = useQueryClient();
  const { data: sources, isLoading, isError, refetch } = useDataSources();

  const handleDiscoveryComplete = () => {
    void queryClient.invalidateQueries({ queryKey: ['data-sources'] });
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">Data Sources</h1>
        <p className="mt-1 text-sm text-gray-500">
          Connected enterprise data sources, discovery status, and schema catalog.
        </p>
      </div>

      {isLoading && <LoadingState variant="full-page" message="Loading data sources..." />}

      {isError && (
        <ErrorState
          message="Failed to load data sources. Please try again."
          onRetry={() => refetch()}
        />
      )}

      {sources && sources.length === 0 && (
        <EmptyState message="No data sources configured yet." />
      )}

      {sources && sources.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-gray-200 shadow-sm">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Name
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Connection
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Discovery
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Last Discovery
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Objects
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white">
              {sources.map((source: DataSourceResponse) => (
                <tr key={source.id} className="hover:bg-gray-50">
                  <td className="whitespace-nowrap px-6 py-4 text-sm font-medium text-gray-900">
                    {source.name}
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-600 capitalize">
                    {source.source_type}
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-sm">
                    <ConnectionStatusBadge status={source.connection_status} />
                  </td>
                  <td className="px-6 py-4 text-sm">
                    <DiscoveryStatusBadge status={source.discovery_status} />
                    <DiscoveryProgressIndicator currentStatus={source.discovery_status} />
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-600">
                    {formatTimestamp(source.last_discovery_at)}
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-600">
                    {source.objects_discovered > 0 ? (
                      <span title={`${source.fields_discovered} fields discovered`}>
                        {source.objects_discovered} objects
                      </span>
                    ) : (
                      '—'
                    )}
                  </td>
                  <td className="px-6 py-4 text-sm">
                    <DiscoverButton
                      sourceId={source.id}
                      connectionStatus={source.connection_status}
                      onDiscoveryComplete={handleDiscoveryComplete}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
