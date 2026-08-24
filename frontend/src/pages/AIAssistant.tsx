import { PlusCircle } from 'lucide-react';
import {
  useAIChat,
  useQueryHistory,
  useChatSessionStore,
  ChatThread,
  ChatInput,
  EvidencePanel,
  VisualizationRenderer,
  QueryHistory,
  SourcesUsedPanel,
  PartialFailureWarning,
  DataLineagePanel,
} from '@/features/ai-chat';
import type { SourceReference, EvidenceItem, LineageTrace, PartialFailureInfo } from '@/features/ai-chat/types';

/**
 * AIAssistant page — portfolio-level AI chat interface.
 *
 * Layout: sidebar with QueryHistory on the left, main chat area on the right.
 * The main chat area contains ChatThread, EvidencePanel/VisualizationRenderer
 * for the latest response, and ChatInput at the bottom.
 *
 * Validates: Requirements 12.13, 12.14
 */
export default function AIAssistant() {
  // Portfolio-level queries — no project_id
  const { sendMessage, isLoading, messages, latestResponse, startNewConversation } =
    useAIChat();
  const { history } = useQueryHistory();
  const setActiveConversation = useChatSessionStore(
    (state) => state.setActiveConversation,
  );

  // Determine if the latest response has visualization to show
  const hasVisualization =
    latestResponse &&
    latestResponse.visualization_spec &&
    latestResponse.response_type !== 'text';

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
    <div className="flex h-[calc(100vh-4rem)]">
      {/* Sidebar — Query History */}
      <aside className="flex w-72 flex-shrink-0 flex-col border-r border-gray-200 bg-gray-50">
        <div className="flex items-center gap-2 border-b border-gray-200 px-4 py-3">
          <button
            type="button"
            onClick={startNewConversation}
            className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            aria-label="Start new conversation"
          >
            <PlusCircle className="h-4 w-4" aria-hidden="true" />
            New Conversation
          </button>
        </div>
        <div className="flex-1 overflow-y-auto">
          <QueryHistory
            history={history}
            onSelectConversation={setActiveConversation}
          />
        </div>
      </aside>

      {/* Main Chat Area */}
      <main className="flex flex-1 flex-col overflow-hidden">
        {/* Header */}
        <header className="flex-shrink-0 border-b border-gray-200 px-6 py-4">
          <h1 className="text-xl font-semibold text-gray-900">AI Assistant</h1>
          <p className="mt-0.5 text-sm text-gray-500">
            Ask questions about your technology transformation portfolio
          </p>
        </header>

        {/* Chat Thread */}
        <div className="flex flex-1 flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto">
            <div className="mx-auto max-w-3xl">
              <ChatThread messages={messages} />

              {/* Phase 8 — Partial Failure Warning (shown when some sources failed) */}
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

              {/* Visualization — shown for the latest response with visualization_spec */}
              {hasVisualization && (
                <div className="px-4 pb-3">
                  <VisualizationRenderer
                    responseType={latestResponse.response_type}
                    visualizationSpec={latestResponse.visualization_spec}
                    isPartial={latestResponse.is_partial}
                    failedSources={latestResponse.failed_sources}
                  />
                </div>
              )}
            </div>
          </div>

          {/* Chat Input */}
          <div className="flex-shrink-0">
            <div className="mx-auto max-w-3xl">
              <ChatInput onSubmit={sendMessage} isLoading={isLoading} />
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
