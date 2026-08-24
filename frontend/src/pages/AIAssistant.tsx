import { useState } from 'react';
import { Bot, Send, ChevronDown, ChevronUp, Database, FileText, GitBranch } from 'lucide-react';
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
import { useProjects } from '@/hooks';

// ---------------------------------------------------------------------------
// Suggested Questions
// ---------------------------------------------------------------------------

const SUGGESTED_QUESTIONS = [
  'Why is this project at risk?',
  'What is causing the budget variance?',
  'What are the biggest unresolved issues?',
  'What should the project manager prioritize?',
];

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ProjectSelector({
  selectedProject,
  onSelect,
}: {
  selectedProject: string | null;
  onSelect: (id: string | null) => void;
}) {
  const { data: projects } = useProjects();
  const [open, setOpen] = useState(false);

  const selectedLabel = selectedProject
    ? projects?.items.find((p) => p.id === selectedProject)?.name ?? 'Select Project'
    : 'All Projects';

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="inline-flex items-center gap-2 px-3 py-1.5 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-300 hover:border-gray-600 transition-colors"
      >
        Project Context: <span className="text-white font-medium">{selectedLabel}</span>
        <ChevronDown size={14} />
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute left-0 top-full mt-1 z-20 w-64 bg-gray-800 border border-gray-700 rounded-lg shadow-xl py-1 max-h-64 overflow-y-auto">
            <button
              onClick={() => { onSelect(null); setOpen(false); }}
              className={`w-full text-left px-4 py-2 text-sm hover:bg-gray-700 transition-colors ${
                !selectedProject ? 'text-teal-400' : 'text-gray-300'
              }`}
            >
              All Projects
            </button>
            {projects?.items.map((p) => (
              <button
                key={p.id}
                onClick={() => { onSelect(p.id); setOpen(false); }}
                className={`w-full text-left px-4 py-2 text-sm hover:bg-gray-700 transition-colors ${
                  selectedProject === p.id ? 'text-teal-400' : 'text-gray-300'
                }`}
              >
                {p.name}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function ExecutionStatus({ isVisible }: { isVisible: boolean }) {
  if (!isVisible) return null;

  return (
    <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-4 space-y-2 animate-pulse">
      <p className="text-sm text-gray-400">Analyzing your question...</p>
      <div className="space-y-1.5">
        <StatusStep label="Understanding project context" done />
        <StatusStep label="Finding relevant enterprise information" done />
        <StatusStep label="Consulting PostgreSQL — Finance" active />
        <StatusStep label="Consulting MongoDB — Project Risks" pending />
        <StatusStep label="Searching Project Documents" pending />
        <StatusStep label="Correlating evidence" pending />
      </div>
    </div>
  );
}

function StatusStep({ label, done, active, pending }: {
  label: string;
  done?: boolean;
  active?: boolean;
  pending?: boolean;
}) {
  return (
    <div className={`flex items-center gap-2 text-xs ${done ? 'text-green-400' : active ? 'text-teal-400' : 'text-gray-500'}`}>
      {done && <span>✓</span>}
      {active && <span className="animate-spin">⟳</span>}
      {pending && <span className="opacity-30">○</span>}
      <span>{label}</span>
    </div>
  );
}

function SourcesConsultedPanel({ sources }: { sources: SourceReference[] }) {
  const [expanded, setExpanded] = useState(false);

  if (sources.length === 0) return null;

  return (
    <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-700/30 transition-colors"
      >
        <span className="text-sm font-medium text-gray-300">
          Sources Consulted ({sources.length})
        </span>
        {expanded ? <ChevronUp size={14} className="text-gray-400" /> : <ChevronDown size={14} className="text-gray-400" />}
      </button>
      {expanded && (
        <div className="px-4 pb-3 space-y-2 border-t border-gray-700/50">
          {sources.map((source, idx) => (
            <div key={idx} className="flex items-center gap-2 text-sm text-gray-300 py-1">
              <SourceIcon type={source.source_type} />
              <span>✓ {source.source_name} — {source.object_name}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function SourceIcon({ type }: { type: string }) {
  switch (type) {
    case 'postgresql':
      return <Database size={14} className="text-blue-400" />;
    case 'mongodb':
      return <Database size={14} className="text-green-400" />;
    case 'document':
    case 'rag':
      return <FileText size={14} className="text-amber-400" />;
    default:
      return <Database size={14} className="text-gray-400" />;
  }
}

function LineagePanel({ lineage }: { lineage: LineageTrace | null }) {
  const [expanded, setExpanded] = useState(false);

  if (!lineage) return null;

  return (
    <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-700/30 transition-colors"
      >
        <span className="text-sm font-medium text-gray-300 flex items-center gap-2">
          <GitBranch size={14} />
          Data Lineage
        </span>
        {expanded ? <ChevronUp size={14} className="text-gray-400" /> : <ChevronDown size={14} className="text-gray-400" />}
      </button>
      {expanded && (
        <div className="px-4 pb-4 border-t border-gray-700/50">
          <DataLineagePanel lineage={lineage} />
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function AIAssistant() {
  const [selectedProject, setSelectedProject] = useState<string | null>(null);

  const { sendMessage, isLoading, messages, latestResponse, startNewConversation } =
    useAIChat(selectedProject ?? undefined);
  const { history } = useQueryHistory();
  const setActiveConversation = useChatSessionStore(
    (state) => state.setActiveConversation,
  );

  // Phase 8 — typed fields from latest response
  const sourcesConsulted: SourceReference[] =
    (latestResponse?.sources as unknown as SourceReference[]) ?? [];
  const evidenceItems: EvidenceItem[] =
    (latestResponse?.evidence as unknown as EvidenceItem[]) ?? [];
  const lineageTrace: LineageTrace | null =
    (latestResponse?.lineage_trace as unknown as LineageTrace) ?? null;
  const failedSources: PartialFailureInfo[] =
    (latestResponse?.failed_sources as unknown as PartialFailureInfo[]) ?? [];
  const isPartial = latestResponse?.is_partial ?? false;

  const hasVisualization =
    latestResponse &&
    latestResponse.visualization_spec &&
    latestResponse.response_type !== 'text';

  const handleSuggestedQuestion = (question: string) => {
    sendMessage(question);
  };

  return (
    <div className="flex h-[calc(100vh-4rem)]">
      {/* Sidebar — Query History */}
      <aside className="hidden lg:flex w-72 flex-shrink-0 flex-col border-r border-gray-700/50 bg-gray-900/50">
        <div className="flex items-center gap-2 border-b border-gray-700/50 px-4 py-3">
          <button
            type="button"
            onClick={startNewConversation}
            className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-teal-600 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-teal-500"
            aria-label="Start new conversation"
          >
            + New Conversation
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
        <header className="flex-shrink-0 border-b border-gray-700/50 px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-semibold text-white flex items-center gap-2">
                <Bot size={22} className="text-teal-400" />
                AI Enterprise Intelligence
              </h1>
              <p className="mt-0.5 text-sm text-gray-400">
                Ask questions across your connected enterprise information.
              </p>
            </div>
            <ProjectSelector
              selectedProject={selectedProject}
              onSelect={setSelectedProject}
            />
          </div>
        </header>

        {/* Chat Thread + Response */}
        <div className="flex flex-1 flex-col overflow-hidden">
          <div className="flex-1 overflow-y-auto px-4 py-4">
            <div className="mx-auto max-w-3xl space-y-4">
              {messages.length === 0 && !isLoading && (
                /* Empty state with suggested questions */
                <div className="py-12 text-center space-y-8">
                  <div>
                    <Bot size={48} className="mx-auto text-teal-400/50 mb-4" />
                    <h2 className="text-lg font-medium text-white">
                      What would you like to know?
                    </h2>
                    <p className="text-sm text-gray-400 mt-1">
                      Ask questions about your technology transformation portfolio.
                    </p>
                  </div>

                  {/* Suggested questions */}
                  <div className="space-y-2 max-w-md mx-auto">
                    <p className="text-xs text-gray-500 uppercase tracking-wider">Suggested questions</p>
                    {SUGGESTED_QUESTIONS.map((q, idx) => (
                      <button
                        key={idx}
                        onClick={() => handleSuggestedQuestion(q)}
                        className="w-full text-left px-4 py-3 bg-gray-800/50 border border-gray-700/50 rounded-lg text-sm text-gray-300 hover:border-teal-500/30 hover:text-white transition-colors"
                      >
                        • {q}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {messages.length > 0 && <ChatThread messages={messages} />}

              {/* Execution Status */}
              <ExecutionStatus isVisible={isLoading} />

              {/* Partial Failure Warning */}
              {isPartial && failedSources.length > 0 && (
                <PartialFailureWarning failedSources={failedSources} />
              )}

              {/* Sources Consulted */}
              {sourcesConsulted.length > 0 && (
                <SourcesConsultedPanel sources={sourcesConsulted} />
              )}

              {/* Evidence Panel */}
              {evidenceItems.length > 0 && (
                <EvidencePanel evidence={evidenceItems} />
              )}

              {/* Data Lineage */}
              <LineagePanel lineage={lineageTrace} />

              {/* Visualization */}
              {hasVisualization && (
                <div className="mt-3">
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
          <div className="flex-shrink-0 border-t border-gray-700/50 px-4 py-4">
            <div className="mx-auto max-w-3xl">
              <ChatInput onSubmit={sendMessage} isLoading={isLoading} />
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
