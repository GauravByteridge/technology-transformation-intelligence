import { useParams } from 'react-router-dom';
import { FileText, Info } from 'lucide-react';

/**
 * Executive Brief page — currently backend-dependent.
 * The endpoint POST /api/v1/briefs/generate does NOT exist in the active backend.
 * This page displays an informational state until the endpoint is implemented.
 */
export default function ExecutiveBrief() {
  const { projectId } = useParams<{ projectId: string }>();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">Executive Brief</h1>
        <p className="mt-1 text-sm text-gray-500">
          AI-generated executive summary for project stakeholders
        </p>
      </div>

      {/* Project context — kept for future use when backend support is added */}
      {projectId && (
        <div className="rounded-lg border border-gray-200 bg-white px-4 py-3 shadow-sm">
          <p className="text-sm text-gray-600">
            Project: <span className="font-mono font-medium text-gray-800">{projectId}</span>
          </p>
        </div>
      )}

      {/* Backend-dependent informational card */}
      <div
        className="rounded-lg border border-blue-200 bg-blue-50 p-6"
        role="status"
        aria-label="Feature not available"
      >
        <div className="flex items-start gap-4">
          <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-blue-100">
            <Info className="h-5 w-5 text-blue-600" aria-hidden="true" />
          </div>
          <div className="space-y-2">
            <h2 className="text-base font-semibold text-blue-900">
              Backend Support Required
            </h2>
            <p className="text-sm text-blue-800">
              Executive Brief generation requires a backend endpoint that is not yet available.
              This feature will be enabled when{' '}
              <code className="rounded bg-blue-100 px-1.5 py-0.5 font-mono text-xs text-blue-900">
                POST /api/v1/briefs/generate
              </code>{' '}
              is implemented.
            </p>
            <p className="text-sm text-blue-700">
              Once available, this page will generate a comprehensive 9-section executive brief
              including health summary, financial position, risks, and recommended actions.
            </p>
          </div>
        </div>
      </div>

      {/* Brief section outline — shows what the page will contain when backend is ready */}
      <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="mb-4 text-lg font-semibold text-gray-900">Planned Brief Sections</h2>
        <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {[
            'Executive Summary',
            'Overall Health',
            'Financial Position',
            'Schedule',
            'Resource Position',
            'Top Risks',
            'Audit and Controls',
            'Recommended Actions',
            'Supporting Sources',
          ].map((section) => (
            <li key={section} className="flex items-center gap-2 text-sm text-gray-500">
              <FileText className="h-4 w-4 text-gray-300" aria-hidden="true" />
              {section}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
