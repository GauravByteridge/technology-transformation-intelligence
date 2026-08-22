import { MessageSquare } from 'lucide-react';

const SUGGESTED_QUESTIONS = [
  'Which projects are currently at risk and why?',
  'Show me the budget variance across all projects',
  'What are the overdue JIRA issues impacting delivery?',
  'Are there any unresolved audit findings older than 30 days?',
  'Which IT controls are non-compliant?',
  'Show me the resource utilization forecast for next quarter',
  'What are the top risks across the entire portfolio?',
];

interface SuggestedQuestionsProps {
  onSelectQuestion: (question: string) => void;
}

/**
 * SuggestedQuestions — displays clickable starter questions for the AI Assistant.
 * Covers at-risk projects, budget, JIRA, audit, IT controls, resources, and portfolio risks.
 */
export function SuggestedQuestions({ onSelectQuestion }: SuggestedQuestionsProps) {
  return (
    <div className="space-y-4">
      <div className="text-center">
        <div className="flex items-center justify-center w-12 h-12 mx-auto mb-3 rounded-full bg-blue-50">
          <MessageSquare className="w-6 h-6 text-blue-600" />
        </div>
        <h2 className="text-lg font-medium text-gray-900">
          Technology Transformation Intelligence
        </h2>
        <p className="mt-1 text-sm text-gray-500">
          Ask me anything about your transformation portfolio
        </p>
      </div>
      <div className="flex flex-wrap justify-center gap-2 mt-4">
        {SUGGESTED_QUESTIONS.map((question) => (
          <button
            key={question}
            type="button"
            onClick={() => onSelectQuestion(question)}
            className="px-3 py-2 text-sm text-left text-gray-700 bg-white border border-gray-200 rounded-lg hover:bg-blue-50 hover:border-blue-300 hover:text-blue-700 transition-colors"
          >
            {question}
          </button>
        ))}
      </div>
    </div>
  );
}
