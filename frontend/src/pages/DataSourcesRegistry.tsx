import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useDataSources } from '@/hooks';
import { LoadingState, ErrorState, EmptyState } from '@/components/common';
import { triggerDiscovery } from '@/features/catalog/services/catalogService';
import { AddSourceModal } from '@/features/data-sources';
import type { DataSourceResponse } from '@/types';
import type { DiscoveryResult } from '@/features/catalog/types';
import {
  Database,
  RefreshCw,
  Eye,
  BookOpen,
  CheckCircle2,
  AlertCircle,
  Loader2,
  FileText,
  Upload,
} from 'lucide-react';

// ─── Helpers ────────────────────────────────────────────────────────────────

function getSourceIcon(sourceType: string): string {
  switch (sourceType.toLowerCase()) {
    case 'postgresql':
      return '🐘';
    case 'mongodb':
      return '🍃';
    case 'document':
    case 'files':
      return '📄';
    default:
      return '🔌';
  }
}

function formatTimestamp(isoTimestamp: string | null): string {
  if (!isoTimestamp) return '—';
  const date = new Date(isoTimestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMinutes = Math.floor(diffMs / (1000 * 60));

  if (diffMinutes < 1) return 'just now';
  if (diffMinutes < 60) return `${diffMinutes} min ago`;
  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) return `${diffHours} hours ago`;
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

// ─── Sub-components ─────────────────────────────────────────────────────────

function ConnectionBadge({ status }: { status: string }) {
  const isConnected = status.toLowerCase() === 'connected';
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
        isConnected
          ? 'bg-green-500/15 text-green-400'
          : 'bg-red-500/15 text-red-400'
      }`}
    >
      {isConnected ? <CheckCircle2 size={12} /> : <AlertCircle size={12} />}
      {isConnected ? 'CONNECTED ✓' : status.toUpperCase()}
    </span>
  );
}

interface SourceCardProps {
  source: DataSourceResponse;
  onRefreshDiscovery: (sourceId: string) => void;
  isRefreshing: boolean;
}

function SourceCard({ source, onRefreshDiscovery, isRefreshing }: SourceCardProps) {
  const navigate = useNavigate();
  const icon = getSourceIcon(source.source_type);

  return (
    <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-6 hover:border-teal-500/30 transition-colors">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <span className="text-2xl">{icon}</span>
          <div>
            <h3 className="text-base font-semibold text-white">{source.name}</h3>
            <p className="text-xs text-gray-400 capitalize">{source.source_type}</p>
          </div>
        </div>
        <ConnectionBadge status={source.connection_status} />
      </div>

      {/* Metadata */}
      {source.source_type.toLowerCase() === 'postgresql' && (
        <div className="text-sm text-gray-400 mb-4">
          <p>Database: {(source.connection_config as { database?: string })?.database || 'TechnologyTransformation'}</p>
        </div>
      )}

      {/* Stats */}
      {source.objects_discovered > 0 && (
        <div className="flex items-center gap-6 mb-4 text-sm">
          <span className="text-gray-300">
            <span className="font-semibold text-white">{source.objects_discovered}</span>{' '}
            {source.source_type === 'postgresql' ? 'Tables' : 'Collections'}
          </span>
          <span className="text-gray-300">
            <span className="font-semibold text-white">{source.fields_discovered}</span> Fields
          </span>
        </div>
      )}

      {/* Last Discovery */}
      <p className="text-xs text-gray-500 mb-4">
        Last Discovery: {formatTimestamp(source.last_discovery_at)}
      </p>

      {/* Actions */}
      <div className="flex items-center gap-2 flex-wrap">
        <button
          onClick={() => navigate(`/catalog`)}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md bg-gray-700 text-gray-300 hover:bg-gray-600 transition-colors"
        >
          <Eye size={12} />
          View Schema
        </button>
        <button
          onClick={() => navigate('/catalog')}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md bg-gray-700 text-gray-300 hover:bg-gray-600 transition-colors"
        >
          <BookOpen size={12} />
          View Catalog
        </button>
        <button
          onClick={() => onRefreshDiscovery(source.id)}
          disabled={isRefreshing || source.connection_status.toLowerCase() !== 'connected'}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md bg-teal-600/20 text-teal-300 hover:bg-teal-600/30 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isRefreshing ? (
            <Loader2 size={12} className="animate-spin" />
          ) : (
            <RefreshCw size={12} />
          )}
          Refresh Discovery
        </button>
      </div>
    </div>
  );
}

function DocumentsCard() {
  const navigate = useNavigate();

  return (
    <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-6 hover:border-teal-500/30 transition-colors">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <span className="text-2xl">📄</span>
          <div>
            <h3 className="text-base font-semibold text-white">Enterprise Documents</h3>
            <p className="text-xs text-gray-400">RAG-indexed documents</p>
          </div>
        </div>
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-green-500/15 text-green-400">
          <CheckCircle2 size={12} />
          READY ✓
        </span>
      </div>

      {/* Stats */}
      <div className="flex items-center gap-6 mb-4 text-sm">
        <span className="text-gray-300">
          <span className="font-semibold text-white">4</span> Documents
        </span>
        <span className="text-gray-300">
          <span className="font-semibold text-white">2</span> Datasets
        </span>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => navigate('/datasets')}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md bg-gray-700 text-gray-300 hover:bg-gray-600 transition-colors"
        >
          <FileText size={12} />
          Browse
        </button>
        <button
          onClick={() => navigate('/upload')}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md bg-teal-600/20 text-teal-300 hover:bg-teal-600/30 transition-colors"
        >
          <Upload size={12} />
          Upload Files
        </button>
      </div>
    </div>
  );
}

// ─── Main Component ─────────────────────────────────────────────────────────

export default function DataSourcesRegistry() {
  const queryClient = useQueryClient();
  const { data: sources, isLoading, isError, refetch } = useDataSources();
  const [showAddModal, setShowAddModal] = useState(false);
  const [refreshingId, setRefreshingId] = useState<string | null>(null);

  const discoveryMutation = useMutation<DiscoveryResult, Error, string>({
    mutationFn: (id: string) => triggerDiscovery(id),
    onSuccess: () => {
      setRefreshingId(null);
      void queryClient.invalidateQueries({ queryKey: ['data-sources'] });
    },
    onError: () => {
      setRefreshingId(null);
    },
  });

  const handleRefreshDiscovery = (sourceId: string) => {
    setRefreshingId(sourceId);
    discoveryMutation.mutate(sourceId);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-white">Data Sources</h1>
          <p className="mt-1 text-sm text-gray-400">
            Connect enterprise data sources and make them AI-queryable.
          </p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-teal-600 text-white hover:bg-teal-500 transition-colors"
        >
          <Database size={16} />
          + Add Source
        </button>
      </div>

      <AddSourceModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        onSuccess={() => {
          setShowAddModal(false);
          void queryClient.invalidateQueries({ queryKey: ['data-sources'] });
        }}
      />

      {isLoading && <LoadingState variant="full-page" message="Loading data sources..." />}

      {isError && (
        <ErrorState
          message="Failed to load data sources. Please try again."
          onRetry={() => refetch()}
        />
      )}

      {sources && sources.length === 0 && (
        <EmptyState message="No data sources configured yet. Click '+ Add Source' to connect your first enterprise data source." />
      )}

      {/* Source cards */}
      {sources && sources.length > 0 && (
        <div className="space-y-4">
          {sources.map((source: DataSourceResponse) => (
            <SourceCard
              key={source.id}
              source={source}
              onRefreshDiscovery={handleRefreshDiscovery}
              isRefreshing={refreshingId === source.id}
            />
          ))}

          {/* Static documents card */}
          <DocumentsCard />
        </div>
      )}

      {/* Show documents card even when no sources are connected */}
      {sources && sources.length === 0 && <DocumentsCard />}
    </div>
  );
}
