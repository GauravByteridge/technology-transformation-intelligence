import { useState } from 'react';

// --- Types ---

interface LineageNode {
  id: string;
  label: string;
  stage: string;
  path: 'structured' | 'unstructured' | 'both';
  metadata: {
    sourceName: string;
    type: string;
    detail: string;
  };
}

interface StageGroup {
  id: string;
  label: string;
  nodes: LineageNode[];
}

// --- Data ---

const stages: StageGroup[] = [
  {
    id: 'data-sources',
    label: 'Data Sources',
    nodes: [
      {
        id: 'ds-projects',
        label: 'Project Management',
        stage: 'Data Sources',
        path: 'structured',
        metadata: { sourceName: 'Project Management', type: 'Database (PostgreSQL)', detail: '12 projects tracked' },
      },
      {
        id: 'ds-finance',
        label: 'Finance',
        stage: 'Data Sources',
        path: 'structured',
        metadata: { sourceName: 'Finance', type: 'Database (PostgreSQL)', detail: '48 cost records' },
      },
      {
        id: 'ds-jira',
        label: 'JIRA',
        stage: 'Data Sources',
        path: 'structured',
        metadata: { sourceName: 'JIRA', type: 'Database (PostgreSQL)', detail: '156 issues indexed' },
      },
      {
        id: 'ds-resources',
        label: 'Resource Mgmt',
        stage: 'Data Sources',
        path: 'structured',
        metadata: { sourceName: 'Resource Management', type: 'Database (PostgreSQL)', detail: '32 team members' },
      },
      {
        id: 'ds-audit',
        label: 'Audit',
        stage: 'Data Sources',
        path: 'structured',
        metadata: { sourceName: 'Audit', type: 'Database (PostgreSQL)', detail: '18 findings recorded' },
      },
      {
        id: 'ds-controls',
        label: 'IT Controls',
        stage: 'Data Sources',
        path: 'structured',
        metadata: { sourceName: 'IT Controls', type: 'Database (PostgreSQL)', detail: 'Last assessed: Jun 2025' },
      },
      {
        id: 'ds-documents',
        label: 'Documents',
        stage: 'Data Sources',
        path: 'unstructured',
        metadata: { sourceName: 'Documents', type: 'Document Store (Vector)', detail: '24 documents indexed' },
      },
      {
        id: 'ds-meetings',
        label: 'Meeting Notes',
        stage: 'Data Sources',
        path: 'unstructured',
        metadata: { sourceName: 'Meeting Notes', type: 'Document Store (Vector)', detail: 'Last processed: Jun 18, 2025' },
      },
    ],
  },
  {
    id: 'data-ingestion',
    label: 'Data Ingestion',
    nodes: [
      {
        id: 'ing-etl',
        label: 'ETL Pipeline',
        stage: 'Data Ingestion',
        path: 'structured',
        metadata: { sourceName: 'ETL Pipeline', type: 'Batch Processing', detail: 'Runs every 6 hours' },
      },
      {
        id: 'ing-embed',
        label: 'Embedding Pipeline',
        stage: 'Data Ingestion',
        path: 'unstructured',
        metadata: { sourceName: 'Embedding Pipeline', type: 'Vector Embedding', detail: 'Processes new documents on ingest' },
      },
    ],
  },
  {
    id: 'unified-data-layer',
    label: 'Unified Data Layer',
    nodes: [
      {
        id: 'udl-pg',
        label: 'PostgreSQL',
        stage: 'Unified Data Layer',
        path: 'structured',
        metadata: { sourceName: 'PostgreSQL', type: 'Relational Database', detail: '10 entity tables, 280+ records' },
      },
      {
        id: 'udl-vector',
        label: 'Vector Store',
        stage: 'Unified Data Layer',
        path: 'unstructured',
        metadata: { sourceName: 'Vector Store', type: 'ChromaDB', detail: '1,200 document chunks embedded' },
      },
    ],
  },
  {
    id: 'retrieval',
    label: 'Retrieval Services',
    nodes: [
      {
        id: 'ret-struct',
        label: 'Structured Retrieval',
        stage: 'Retrieval Services',
        path: 'structured',
        metadata: { sourceName: 'Structured Retrieval Service', type: 'SQL Query Engine', detail: 'Queries via Data Access Layer (ABCs)' },
      },
      {
        id: 'ret-unstruct',
        label: 'Unstructured Retrieval',
        stage: 'Retrieval Services',
        path: 'unstructured',
        metadata: { sourceName: 'Unstructured Retrieval Service', type: 'Similarity Search', detail: 'Top-k vector similarity (k=10)' },
      },
    ],
  },
  {
    id: 'ai-orchestration',
    label: 'AI Orchestration',
    nodes: [
      {
        id: 'orch-query',
        label: 'Query Orchestrator',
        stage: 'AI Orchestration',
        path: 'both',
        metadata: { sourceName: 'Query Orchestrator', type: 'Service Layer', detail: 'Parallel retrieval with 15s timeout' },
      },
    ],
  },
  {
    id: 'llm',
    label: 'LLM',
    nodes: [
      {
        id: 'llm-provider',
        label: 'LLM Provider',
        stage: 'LLM',
        path: 'both',
        metadata: { sourceName: 'LLM Provider', type: 'OpenAI / Mock', detail: 'GPT-4 (configurable via env)' },
      },
    ],
  },
  {
    id: 'business-answer',
    label: 'Business Answer',
    nodes: [
      {
        id: 'ba-response',
        label: 'AI Response',
        stage: 'Business Answer',
        path: 'both',
        metadata: { sourceName: 'AI Response', type: 'Generated Output', detail: 'Answer + findings + evidence + confidence' },
      },
    ],
  },
];

// --- Helper Components ---

function PathLabel({ path }: { path: 'structured' | 'unstructured' | 'both' }) {
  if (path === 'structured') {
    return (
      <span className="inline-flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide text-blue-700">
        <span className="w-2 h-2 rounded-sm bg-blue-500 border border-blue-700" aria-hidden="true" />
        Structured
      </span>
    );
  }
  if (path === 'unstructured') {
    return (
      <span className="inline-flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide text-purple-700">
        <span className="w-2 h-2 rounded-full bg-purple-500 border border-purple-700" aria-hidden="true" />
        Unstructured
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide text-teal-700">
      <span className="w-2 h-2 bg-teal-500 border border-teal-700" style={{ clipPath: 'polygon(50% 0%, 100% 100%, 0% 100%)' }} aria-hidden="true" />
      Combined
    </span>
  );
}

function getNodeStyles(path: 'structured' | 'unstructured' | 'both', isSelected: boolean) {
  const base = 'rounded-lg px-3 py-2 text-xs font-medium cursor-pointer transition-all duration-150 border-2 text-center min-w-[110px]';
  const selectedRing = isSelected ? 'ring-2 ring-offset-2' : '';

  if (path === 'structured') {
    return `${base} bg-blue-50 border-blue-400 text-blue-900 hover:bg-blue-100 hover:border-blue-600 ${isSelected ? 'ring-blue-500' : ''} ${selectedRing}`;
  }
  if (path === 'unstructured') {
    return `${base} bg-purple-50 border-purple-400 border-dashed text-purple-900 hover:bg-purple-100 hover:border-purple-600 ${isSelected ? 'ring-purple-500' : ''} ${selectedRing}`;
  }
  return `${base} bg-teal-50 border-teal-400 text-teal-900 hover:bg-teal-100 hover:border-teal-600 ${isSelected ? 'ring-teal-500' : ''} ${selectedRing}`;
}

function ArrowConnector() {
  return (
    <div className="flex items-center justify-center px-1 flex-shrink-0" aria-hidden="true">
      <svg width="28" height="20" viewBox="0 0 28 20" fill="none" xmlns="http://www.w3.org/2000/svg">
        <line x1="0" y1="10" x2="20" y2="10" stroke="#9CA3AF" strokeWidth="2" />
        <polygon points="20,5 28,10 20,15" fill="#9CA3AF" />
      </svg>
    </div>
  );
}

// --- Metadata Panel ---

function MetadataPanel({ node, onClose }: { node: LineageNode; onClose: () => void }) {
  return (
    <div
      className="fixed bottom-4 right-4 z-50 w-80 rounded-xl border border-gray-200 bg-white shadow-xl p-5 animate-in fade-in slide-in-from-bottom-2"
      role="dialog"
      aria-label={`Metadata for ${node.metadata.sourceName}`}
    >
      <div className="flex items-start justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-900">{node.metadata.sourceName}</h3>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600 transition-colors"
          aria-label="Close metadata panel"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
      <dl className="space-y-2 text-sm">
        <div>
          <dt className="text-gray-500 text-xs uppercase tracking-wide">Source Name</dt>
          <dd className="text-gray-900 font-medium">{node.metadata.sourceName}</dd>
        </div>
        <div>
          <dt className="text-gray-500 text-xs uppercase tracking-wide">Type</dt>
          <dd className="text-gray-900">{node.metadata.type}</dd>
        </div>
        <div>
          <dt className="text-gray-500 text-xs uppercase tracking-wide">Detail</dt>
          <dd className="text-gray-900">{node.metadata.detail}</dd>
        </div>
        <div>
          <dt className="text-gray-500 text-xs uppercase tracking-wide">Path</dt>
          <dd><PathLabel path={node.path} /></dd>
        </div>
      </dl>
      <div className="mt-3 pt-3 border-t border-gray-100">
        <span className="text-xs text-gray-400">Stage: {node.stage}</span>
      </div>
    </div>
  );
}

// --- Main Component ---

export default function DataLineage() {
  const [selectedNode, setSelectedNode] = useState<LineageNode | null>(null);

  function handleNodeClick(node: LineageNode) {
    setSelectedNode((prev) => (prev?.id === node.id ? null : node));
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">Data Lineage</h1>
        <p className="text-sm text-gray-500 mt-1">
          Visual representation of data flow from enterprise sources to AI-generated business answers
        </p>
      </div>

      {/* Legend */}
      <div className="flex flex-wrap items-center gap-4 rounded-lg border border-gray-200 bg-white px-4 py-3 shadow-sm" aria-label="Path legend">
        <span className="text-xs font-medium text-gray-600">Path Types:</span>
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-sm bg-blue-50 border-2 border-blue-400" aria-hidden="true" />
          <span className="text-xs text-gray-700">Structured (solid border)</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-sm bg-purple-50 border-2 border-dashed border-purple-400" aria-hidden="true" />
          <span className="text-xs text-gray-700">Unstructured (dashed border)</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-sm bg-teal-50 border-2 border-teal-400" aria-hidden="true" />
          <span className="text-xs text-gray-700">Combined (solid border)</span>
        </div>
        <span className="text-xs text-gray-500 ml-auto">Click any node for details</span>
      </div>

      {/* Flow Diagram */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm overflow-x-auto">
        <div className="flex items-start gap-0 min-w-[1100px]">
          {stages.map((stage, stageIndex) => (
            <div key={stage.id} className="flex items-start">
              {/* Stage Column */}
              <div className="flex flex-col items-center gap-2 min-w-[130px]">
                {/* Stage Header */}
                <div className="text-[11px] font-semibold text-gray-600 uppercase tracking-wide text-center whitespace-nowrap mb-2 px-1">
                  {stage.label}
                </div>

                {/* Nodes */}
                <div className="flex flex-col items-center gap-2">
                  {stage.nodes.map((node) => (
                    <button
                      key={node.id}
                      onClick={() => handleNodeClick(node)}
                      className={getNodeStyles(node.path, selectedNode?.id === node.id)}
                      aria-pressed={selectedNode?.id === node.id}
                      aria-label={`${node.label} — ${node.path} path. Click for details.`}
                      title={`${node.label} (${node.path})`}
                    >
                      <div>{node.label}</div>
                      <div className="mt-1">
                        <PathLabel path={node.path} />
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Arrow between stages */}
              {stageIndex < stages.length - 1 && (
                <div className="flex items-center self-center mt-8">
                  <ArrowConnector />
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Architecture Description */}
      <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 shadow-sm">
        <h2 className="text-sm font-semibold text-gray-700 mb-2">How It Works</h2>
        <ol className="text-xs text-gray-600 space-y-1 list-decimal list-inside">
          <li><strong>Data Sources</strong> — Enterprise systems feed structured data (databases) and unstructured data (documents, notes).</li>
          <li><strong>Data Ingestion</strong> — ETL pipelines load structured data; embedding pipelines vectorize documents.</li>
          <li><strong>Unified Data Layer</strong> — PostgreSQL stores relational data; ChromaDB stores vector embeddings.</li>
          <li><strong>Retrieval Services</strong> — Structured Retrieval queries via the Data Access Layer; Unstructured Retrieval performs similarity search.</li>
          <li><strong>AI Orchestration</strong> — The Query Orchestrator runs both retrievals in parallel (15s timeout), combines results, and builds context.</li>
          <li><strong>LLM</strong> — The language model generates a grounded response from the combined context.</li>
          <li><strong>Business Answer</strong> — The final response includes findings, metrics, evidence, and confidence scoring.</li>
        </ol>
      </div>

      {/* Metadata Panel */}
      {selectedNode && (
        <MetadataPanel node={selectedNode} onClose={() => setSelectedNode(null)} />
      )}
    </div>
  );
}
