import { useState, useEffect } from 'react';
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
  Mail,
} from 'lucide-react';

// ─── Helpers ────────────────────────────────────────────────────────────────

function getSourceIcon(sourceType: string): string {
  switch (sourceType.toLowerCase()) {
    case 'postgresql':
      return '/icons/postgresql.png';
    case 'mongodb':
      return '/icons/mongodb.png';
    case 'jira':
      return '/icons/jira.png';
    case 'gmail':
      return '/icons/gmail.png';
    case 'outlook':
      return '/icons/outlook.png';
    case 'document':
    case 'files':
      return '/icons/document.png';
    default:
      return '/icons/document.png';
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
    <div className="bg-white dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700/50 rounded-lg p-6 hover:border-teal-500/30 transition-colors flex flex-col">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <img src={icon} alt={source.source_type} className="w-8 h-8 object-contain" />
          <div>
            <h3 className="text-base font-semibold text-gray-900 dark:text-white">{source.name}</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400 capitalize">{source.source_type}</p>
          </div>
        </div>
        <ConnectionBadge status={source.connection_status} />
      </div>

      {/* Metadata */}
      {source.source_type.toLowerCase() === 'postgresql' && (
        <div className="text-sm text-gray-500 dark:text-gray-400 mb-4">
          <p>Database: {(source.connection_config as { database?: string })?.database || 'TechnologyTransformation'}</p>
        </div>
      )}

      {/* Stats */}
      {source.objects_discovered > 0 && (
        <div className="flex items-center gap-6 mb-4 text-sm">
          <span className="text-gray-600 dark:text-gray-300">
            <span className="font-semibold text-gray-900 dark:text-white">{source.objects_discovered}</span>{' '}
            {source.source_type === 'postgresql' ? 'Tables' : 'Collections'}
          </span>
          <span className="text-gray-600 dark:text-gray-300">
            <span className="font-semibold text-gray-900 dark:text-white">{source.fields_discovered}</span> Fields
          </span>
        </div>
      )}

      {/* Last Discovery */}
      <p className="text-xs text-gray-500 mb-4">
        Last Discovery: {formatTimestamp(source.last_discovery_at)}
      </p>

      {/* Actions */}
      <div className="flex items-center gap-2 flex-wrap mt-auto">
        <button
          onClick={() => navigate(`/catalog`)}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md bg-gray-200 text-gray-700 hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600 transition-colors"
        >
          <Eye size={12} />
          View Schema
        </button>
        <button
          onClick={() => navigate('/catalog')}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md bg-gray-200 text-gray-700 hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600 transition-colors"
        >
          <BookOpen size={12} />
          View Catalog
        </button>
        <button
          onClick={() => onRefreshDiscovery(source.id)}
          disabled={isRefreshing || source.connection_status.toLowerCase() !== 'connected'}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md bg-teal-700 text-white hover:bg-teal-600 dark:bg-teal-600/20 dark:text-teal-300 dark:hover:bg-teal-600/30 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
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
    <div className="bg-white dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700/50 rounded-lg p-6 hover:border-teal-500/30 transition-colors flex flex-col">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <span className="text-2xl">📄</span>
          <div>
            <h3 className="text-base font-semibold text-gray-900 dark:text-white">Enterprise Documents</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">RAG-indexed documents</p>
          </div>
        </div>
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-green-500/15 text-green-400">
          <CheckCircle2 size={12} />
          READY ✓
        </span>
      </div>

      {/* Stats */}
      <div className="flex items-center gap-6 mb-4 text-sm">
        <span className="text-gray-600 dark:text-gray-300">
          <span className="font-semibold text-gray-900 dark:text-white">4</span> Documents
        </span>
        <span className="text-gray-600 dark:text-gray-300">
          <span className="font-semibold text-gray-900 dark:text-white">2</span> Datasets
        </span>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2 mt-auto">
        <button
          onClick={() => navigate('/datasets')}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md bg-gray-200 text-gray-700 hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600 transition-colors"
        >
          <FileText size={12} />
          Browse
        </button>
        <button
          onClick={() => navigate('/upload')}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md bg-teal-700 text-white hover:bg-teal-600 dark:bg-teal-600/20 dark:text-teal-300 dark:hover:bg-teal-600/30 transition-colors"
        >
          <Upload size={12} />
          Upload Files
        </button>
      </div>
    </div>
  );
}

function GmailCard({ onFetchEmails }: { onFetchEmails: () => void }) {
  const navigate = useNavigate();

  return (
    <div className="bg-white dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700/50 rounded-lg p-6 hover:border-teal-500/30 transition-colors flex flex-col">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <img src="/icons/gmail.png" alt="Gmail" className="w-8 h-8 object-contain" />
          <div>
            <h3 className="text-base font-semibold text-gray-900 dark:text-white">Gmail</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">Email integration</p>
          </div>
        </div>
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-green-500/15 text-green-400">
          <CheckCircle2 size={12} />
          CONNECTED ✓
        </span>
      </div>

      {/* Stats */}
      <div className="flex items-center gap-6 mb-4 text-sm">
        <span className="text-gray-600 dark:text-gray-300">
          <span className="font-semibold text-gray-900 dark:text-white">12</span> Emails indexed
        </span>
        <span className="text-gray-600 dark:text-gray-300">
          <span className="font-semibold text-gray-900 dark:text-white">3</span> Attachments
        </span>
      </div>

      {/* Last Sync */}
      <p className="text-xs text-gray-500 mb-4">
        Last Sync: just now
      </p>

      {/* Actions */}
      <div className="flex items-center gap-2 mt-auto">
        <button
          onClick={onFetchEmails}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md bg-gray-200 text-gray-700 hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600 transition-colors"
        >
          <Mail size={12} />
          Fetch Emails
        </button>
        <button
          onClick={() => navigate('/sources')}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md bg-teal-700 text-white hover:bg-teal-600 dark:bg-teal-600/20 dark:text-teal-300 dark:hover:bg-teal-600/30 transition-colors"
        >
          <RefreshCw size={12} />
          Sync Now
        </button>
      </div>
    </div>
  );
}

function OutlookCard({ onConnect, onFetchEmails }: { onConnect: () => void; onFetchEmails: () => void }) {
  const [status, setStatus] = useState<{ connected: boolean; email?: string } | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch('http://localhost:8000/api/v1/outlook/status')
      .then((res) => res.json())
      .then((data) => { if (!cancelled) setStatus(data); })
      .catch(() => { if (!cancelled) setStatus({ connected: false }); });
    return () => { cancelled = true; };
  }, []);

  const isConnected = Boolean(status?.connected);

  return (
    <div className="bg-white dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700/50 rounded-lg p-6 hover:border-teal-500/30 transition-colors flex flex-col">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <img src="/icons/outlook.png" alt="Outlook" className="w-8 h-8 object-contain" />
          <div>
            <h3 className="text-base font-semibold text-gray-900 dark:text-white">Outlook</h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">Email integration (Microsoft Graph)</p>
          </div>
        </div>
        {isConnected && (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-green-500/15 text-green-400">
            <CheckCircle2 size={12} />
            CONNECTED ✓
          </span>
        )}
      </div>

      {isConnected ? (
        <>
          <div className="text-sm text-gray-600 dark:text-gray-300 mb-4">
            Connected via Microsoft Graph{status?.email ? <> as <span className="font-semibold text-gray-900 dark:text-white">{status.email}</span></> : ''}.
          </div>
          <p className="text-xs text-gray-500 mb-4">Delegated Mail.Read access authorized</p>
          {/* Actions */}
          <div className="flex items-center gap-2 mt-auto">
            <button
              onClick={onFetchEmails}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md bg-gray-200 text-gray-700 hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600 transition-colors"
            >
              <Mail size={12} />
              Fetch Emails
            </button>
          </div>
        </>
      ) : (
        <>
          {/* Description */}
          <div className="text-sm text-gray-600 dark:text-gray-300 mb-4">
            Connect with Microsoft using delegated <span className="font-semibold text-gray-900 dark:text-white">Mail.Read</span> access.
          </div>
          <p className="text-xs text-gray-500 mb-4">
            Sign in with your Microsoft account to authorize
          </p>
          {/* Actions */}
          <div className="flex items-center gap-2 mt-auto">
            <button
              onClick={onConnect}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md bg-teal-700 text-white hover:bg-teal-600 dark:bg-teal-600/20 dark:text-teal-300 dark:hover:bg-teal-600/30 transition-colors"
            >
              <Mail size={12} />
              Connect Outlook
            </button>
          </div>
        </>
      )}
    </div>
  );
}

// ─── Main Component ─────────────────────────────────────────────────────────

export default function DataSourcesRegistry() {
  const queryClient = useQueryClient();
  const { data: sources, isLoading, isError, refetch } = useDataSources();
  const [showAddModal, setShowAddModal] = useState(false);
  const [modalInitialType, setModalInitialType] = useState<'gmail' | 'outlook' | undefined>(undefined);
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
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">Data Sources</h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
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
        onClose={() => { setShowAddModal(false); setModalInitialType(undefined); }}
        onSuccess={() => {
          setShowAddModal(false);
          setModalInitialType(undefined);
          void queryClient.invalidateQueries({ queryKey: ['data-sources'] });
        }}
        initialSourceType={modalInitialType}
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
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
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
          {/* Gmail card */}
          <GmailCard onFetchEmails={() => { setModalInitialType('gmail'); setShowAddModal(true); }} />
          {/* Outlook card */}
          <OutlookCard
            onConnect={() => { setModalInitialType('outlook'); setShowAddModal(true); }}
            onFetchEmails={() => { setModalInitialType('outlook'); setShowAddModal(true); }}
          />
        </div>
      )}

      {/* Show documents card even when no sources are connected */}
      {sources && sources.length === 0 && <DocumentsCard />}
    </div>
  );
}
