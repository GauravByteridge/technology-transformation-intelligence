import { useParams } from 'react-router-dom';
import { FileText, Download, RefreshCw, Loader2 } from 'lucide-react';
import { useGenerateBrief, useExportBriefPDF } from '../hooks';
import { ErrorState } from '../components/common/ErrorState';
import type { ExecutiveBrief as ExecutiveBriefType } from '../types';

/** Section configuration for the 9-section executive brief */
const BRIEF_SECTIONS: { key: keyof Omit<ExecutiveBriefType, 'generated_at' | 'supporting_sources'>; label: string }[] = [
  { key: 'executive_summary', label: 'Executive Summary' },
  { key: 'overall_health', label: 'Overall Health' },
  { key: 'financial_position', label: 'Financial Position' },
  { key: 'schedule', label: 'Schedule' },
  { key: 'resource_position', label: 'Resource Position' },
  { key: 'top_risks', label: 'Top Risks' },
  { key: 'audit_and_controls', label: 'Audit and Controls' },
  { key: 'recommended_actions', label: 'Recommended Actions' },
];

export default function ExecutiveBrief() {
  const { projectId } = useParams<{ projectId: string }>();

  const generateBrief = useGenerateBrief();
  const exportPDF = useExportBriefPDF();

  const brief = generateBrief.data;
  const isGenerating = generateBrief.isPending;
  const generateError = generateBrief.error;

  const handleGenerate = () => {
    if (!projectId) return;
    generateBrief.mutate(projectId);
  };

  const handleExportPDF = () => {
    if (!projectId) return;
    exportPDF.mutate(projectId, {
      onSuccess: (blob) => {
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `executive-brief-${projectId}.pdf`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
      },
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Executive Brief</h1>
          <p className="mt-1 text-sm text-gray-500">
            Project: <span className="font-mono text-gray-700">{projectId}</span>
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Generate / Regenerate button */}
          <button
            onClick={handleGenerate}
            disabled={isGenerating}
            className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isGenerating ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : brief ? (
              <RefreshCw className="h-4 w-4" />
            ) : (
              <FileText className="h-4 w-4" />
            )}
            {brief ? 'Regenerate Brief' : 'Generate Brief'}
          </button>

          {/* Export PDF button - only visible when brief is available */}
          {brief && (
            <button
              onClick={handleExportPDF}
              disabled={exportPDF.isPending}
              className="inline-flex items-center gap-2 rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {exportPDF.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Download className="h-4 w-4" />
              )}
              Export PDF
            </button>
          )}
        </div>
      </div>

      {/* Loading indicator during generation */}
      {isGenerating && (
        <div
          className="flex flex-col items-center justify-center gap-3 rounded-lg border border-blue-200 bg-blue-50 px-6 py-12"
          role="status"
          aria-live="polite"
          aria-label="Generating executive brief"
        >
          <Loader2 className="h-10 w-10 animate-spin text-blue-600" />
          <p className="text-sm font-medium text-blue-700">Generating executive brief...</p>
          <p className="text-xs text-blue-500">This may take up to 60 seconds</p>
        </div>
      )}

      {/* Error state with retry */}
      {generateError && !isGenerating && (
        <ErrorState
          message={generateError.message || 'Failed to generate executive brief. Please try again.'}
          onRetry={handleGenerate}
        />
      )}

      {/* PDF export error */}
      {exportPDF.error && !exportPDF.isPending && (
        <div
          className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3"
          role="alert"
        >
          <p className="text-sm text-amber-700">
            Failed to export PDF: {exportPDF.error.message || 'Unknown error'}
          </p>
        </div>
      )}

      {/* Brief content - display all 9 sections */}
      {brief && !isGenerating && (
        <div className="space-y-6">
          {/* Generated timestamp */}
          <p className="text-xs text-gray-400">
            Generated at: {new Date(brief.generated_at).toLocaleString()}
          </p>

          {/* 8 text sections */}
          {BRIEF_SECTIONS.map(({ key, label }) => (
            <section
              key={key}
              className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm"
            >
              <h2 className="mb-3 text-lg font-semibold text-gray-900">{label}</h2>
              <div className="prose prose-sm max-w-none text-gray-700 whitespace-pre-wrap">
                {brief[key] || 'No data available'}
              </div>
            </section>
          ))}

          {/* Section 9: Supporting Sources */}
          <section className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
            <h2 className="mb-3 text-lg font-semibold text-gray-900">Supporting Sources</h2>
            {brief.supporting_sources && brief.supporting_sources.length > 0 ? (
              <ul className="list-disc space-y-1 pl-5 text-sm text-gray-700">
                {brief.supporting_sources.map((source, index) => (
                  <li key={index}>{source}</li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-gray-500">No sources available</p>
            )}
          </section>
        </div>
      )}

      {/* Initial empty state - before generation */}
      {!brief && !isGenerating && !generateError && (
        <div className="flex flex-col items-center justify-center gap-4 rounded-lg border border-dashed border-gray-300 bg-gray-50 px-6 py-16">
          <FileText className="h-12 w-12 text-gray-400" />
          <div className="text-center">
            <p className="text-sm font-medium text-gray-700">No brief generated yet</p>
            <p className="mt-1 text-xs text-gray-500">
              Click "Generate Brief" to create a comprehensive executive brief for this project.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
