import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Send, Loader2, FileText, Sparkles } from 'lucide-react';
import { useMutation } from '@tanstack/react-query';
import { apiClient } from '../../api/client';
import { ChatMessage, type ChatMessageData } from '../ai/ChatMessage';
import { EvidencePanel } from '../ai/EvidencePanel';
import type { AIResponse, SourceEvidence } from '../../types';

const MAX_QUESTION_LENGTH = 500;

/** Project-scoped suggested questions for the AI tab */
const PROJECT_SUGGESTED_QUESTIONS = [
  'Why is this project at risk?',
  'What actions should the project manager prioritize?',
  'What is the current budget status and variance?',
  'Are there any overdue JIRA issues?',
  'What audit findings need attention?',
];

interface ProjectAITabProps {
  projectId: string;
  projectName: string;
}

interface MessageWithEvidence extends ChatMessageData {
  evidence?: SourceEvidence[];
}

/**
 * ProjectAITab — embedded AI chat interface scoped to a specific project.
 *
 * Shows project-specific suggested questions, passes projectId to the AI endpoint,
 * and displays responses with the EvidencePanel for source attribution.
 * Includes a "Generate Brief" button for navigation to the executive brief page.
 *
 * Validates: Requirements 15.1, 15.2, 15.3
 */
export function ProjectAITab({ projectId, projectName }: ProjectAITabProps) {
  const navigate = useNavigate();
  const [messages, setMessages] = useState<MessageWithEvidence[]>([]);
  const [input, setInput] = useState('');
  const [validationError, setValidationError] = useState<string | null>(null);
  const [lastEvidence, setLastEvidence] = useState<SourceEvidence[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const { mutate: askQuestion, isPending } = useMutation<AIResponse, Error, { question: string; project_id?: string }>({
    mutationFn: (request) => apiClient.askQuestion(request),
  });

  // Scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  function validateInput(value: string): string | null {
    const trimmed = value.trim();
    if (!trimmed) {
      return 'Please enter a question before submitting.';
    }
    if (trimmed.length > MAX_QUESTION_LENGTH) {
      return `Question must be ${MAX_QUESTION_LENGTH} characters or fewer. Currently: ${trimmed.length} characters.`;
    }
    return null;
  }

  function handleSubmit(questionText?: string) {
    const text = questionText ?? input;
    const error = validateInput(text);

    if (error) {
      setValidationError(error);
      return;
    }

    setValidationError(null);
    const trimmed = text.trim();

    const userMessage: MessageWithEvidence = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: trimmed,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');

    // Pass project_id to scope the AI query to this project
    askQuestion(
      { question: trimmed, project_id: projectId },
      {
        onSuccess: (response) => {
          const assistantMessage: MessageWithEvidence = {
            id: `assistant-${Date.now()}`,
            role: 'assistant',
            content: response.answer,
            evidence: response.evidence,
          };
          setMessages((prev) => [...prev, assistantMessage]);
          setLastEvidence(response.evidence);
        },
        onError: (error) => {
          const errorMessage: MessageWithEvidence = {
            id: `error-${Date.now()}`,
            role: 'assistant',
            content: `Sorry, I encountered an error processing your question. ${error.message || 'Please try again.'}`,
          };
          setMessages((prev) => [...prev, errorMessage]);
        },
      }
    );
  }

  function handleSelectQuestion(question: string) {
    handleSubmit(question);
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  }

  function handleInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    setInput(e.target.value);
    if (validationError) {
      setValidationError(null);
    }
  }

  function handleGenerateBrief() {
    navigate(`/projects/${projectId}/brief`);
  }

  return (
    <div className="flex flex-col h-[600px] rounded-lg border border-gray-200 bg-white overflow-hidden">
      {/* Header */}
      <div className="flex-shrink-0 flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-blue-600" />
          <h2 className="text-sm font-semibold text-gray-900">
            AI Assistant — {projectName}
          </h2>
        </div>
        <button
          type="button"
          onClick={handleGenerateBrief}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-blue-600 border border-blue-200 rounded-md hover:bg-blue-50 transition-colors"
          aria-label="Generate executive brief for this project"
        >
          <FileText className="w-3.5 h-3.5" />
          Generate Brief
        </button>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-4">
            <div className="text-center">
              <p className="text-sm text-gray-600 mb-3">
                Ask questions about <span className="font-medium">{projectName}</span>
              </p>
            </div>
            <div className="flex flex-wrap justify-center gap-2">
              {PROJECT_SUGGESTED_QUESTIONS.map((question) => (
                <button
                  key={question}
                  type="button"
                  onClick={() => handleSelectQuestion(question)}
                  className="px-3 py-2 text-sm text-left text-gray-700 bg-white border border-gray-200 rounded-lg hover:bg-blue-50 hover:border-blue-300 hover:text-blue-700 transition-colors"
                >
                  {question}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {messages.map((message) => (
              <div key={message.id}>
                <ChatMessage message={message} />
                {/* Show evidence panel for assistant messages that have evidence */}
                {message.role === 'assistant' && message.evidence && message.evidence.length > 0 && (
                  <div className="mt-3 ml-11">
                    <EvidencePanel evidence={message.evidence} />
                  </div>
                )}
              </div>
            ))}
            {isPending && (
              <div className="flex items-center gap-2 text-sm text-gray-500" role="status" aria-live="polite">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Analyzing project data...</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Evidence summary when available */}
      {lastEvidence.length > 0 && messages.length > 0 && (
        <div className="flex-shrink-0 border-t border-gray-100 px-4 py-2 bg-gray-50">
          <p className="text-xs text-gray-500">
            Last response used {lastEvidence.length} source{lastEvidence.length !== 1 ? 's' : ''}
          </p>
        </div>
      )}

      {/* Input area */}
      <div className="flex-shrink-0 border-t border-gray-200 px-4 py-3 bg-white">
        {validationError && (
          <p className="text-xs text-red-600 mb-2" role="alert">
            {validationError}
          </p>
        )}
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={input}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            placeholder={`Ask about ${projectName}...`}
            disabled={isPending}
            maxLength={MAX_QUESTION_LENGTH + 50}
            className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label="Ask a project-specific question"
            aria-invalid={!!validationError}
          />
          <button
            type="button"
            onClick={() => handleSubmit()}
            disabled={isPending}
            className="flex items-center justify-center w-9 h-9 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            aria-label="Send question"
          >
            {isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </button>
        </div>
        <p className="mt-1 text-xs text-gray-400">
          {input.trim().length}/{MAX_QUESTION_LENGTH} characters
        </p>
      </div>
    </div>
  );
}
