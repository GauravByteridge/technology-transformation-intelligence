import { useCallback } from 'react';
import { Sparkles } from 'lucide-react';
import {
  useAIChat,
  ChatThread,
  ChatInput,
  EvidencePanel,
  VisualizationRenderer,
  SourcesUsedPanel,
  PartialFailureWarning,
  DataLineagePanel,
} from '@/features/ai-chat';
import type { SourceReference, EvidenceItem, LineageTrace, PartialFailureInfo } from '@/features/ai-chat/types';

interface ProjectAITabProps {
  projectId: string;
  projectName: string;
}

/**
 * ProjectAITab — embedded AI chat scoped to a specific project.
 *
 * Uses useAIChat(projectId) which automatically includes project_id in all queries.
 * The user does NOT need to specify the project — it's implicit from tab context.
 * Evidence panel shows after each AI response that has evidence/sources.
 * Visualization renders when response has table/chart data.
 *
 * Validates: Requirements 12.13
 */
export function ProjectAITab({ projectId, projectName }: ProjectAITabProps) {
  const { sendMessage, isLoading, messages, latestResponse } = useAIChat(projectId);

  const handleSubmit = useCallback(
    (question: string) => {
      sendMessage(question);
    },
    [sendMessage],
  );

  const hasVisualization =
    latestResponse &&
    (latestResponse.response_type === 'table' || latestResponse.response_type === 'chart');

  // Phase 8 — parse typed fields from the latest response
  const sourcesConsulted: SourceReference[] =
    (latestResponse?.sources as unknown as SourceReference[]) ?? [];
  const evidenceItems: EvidenceItem[] =
    (latestResponse?.evidence as unknown as EvidenceItem[]) ?? [];
  const lineageTrace: LineageTrace | null =
    (latestResponse?.lineage_trace as unknown as LineageTrace) ?? null;
  const failedSources: PartialFailureInfo[] =
    (latestResponse?.failed_sources as unknown as PartialFailureInfo[]) ?? [];
  const isPartial = latestResponse?.is_partial ?? false;

  return (
    <div className="flex flex-col h-[600px] rounded-lg border border-gray-200 bg-white overflow-hidden">
      {/* Header — project context indicator */}
      <div className="flex-shrink-0 flex items-center gap-2 px-4 py-3 border-b border-gray-200 bg-gray-50">
        <Sparkles className="w-4 h-4 text-blue-600" aria-hidden="true" />
        <h2 className="text-sm font-semibold text-gray-900">
          Ask about {projectName}
        </h2>
      </div>

      {/* Main content area: chat thread + sidebar panels */}
      <div className="flex flex-1 overflow-hidden">
        {/* Chat thread — primary conversation area */}
        <div className="flex flex-1 flex-col min-w-0">
          <div className="flex-1 overflow-y-auto">
            <ChatThread messages={messages} />

            {/* Phase 8 — Partial Failure Warning */}
            {isPartial && failedSources.length > 0 && (
              <div className="px-4 pb-3">
                <PartialFailureWarning failedSources={failedSources} />
              </div>
            )}

            {/* Phase 8 — Sources Used Panel */}
            {sourcesConsulted.length > 0 && (
              <div className="px-4 pb-3">
                <SourcesUsedPanel sources={sourcesConsulted} />
              </div>
            )}

            {/* Phase 8 — Evidence Panel (typed) */}
            {evidenceItems.length > 0 && (
              <div className="px-4 pb-3">
                <EvidencePanel evidence={evidenceItems} />
              </div>
            )}

            {/* Phase 8 — Data Lineage Panel */}
            {lineageTrace && (
              <div className="px-4 pb-3">
                <DataLineagePanel lineage={lineageTrace} />
              </div>
            )}
          </div>
          <ChatInput onSubmit={handleSubmit} isLoading={isLoading} />
        </div>

        {/* Visualization sidebar — shown after responses with visualization data */}
        {hasVisualization && latestResponse && (
          <aside
            className="w-80 flex-shrink-0 border-l border-gray-200 overflow-y-auto p-3 space-y-3 bg-gray-50"
            aria-label="Visualization panel"
          >
            <VisualizationRenderer
              responseType={latestResponse.response_type}
              visualizationSpec={latestResponse.visualization_spec}
              isPartial={latestResponse.is_partial}
              failedSources={latestResponse.failed_sources}
            />
          </aside>
        )}
      </div>
    </div>
  );
}
