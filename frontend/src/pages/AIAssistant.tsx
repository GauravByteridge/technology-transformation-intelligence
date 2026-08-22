import { useState, useRef, useEffect } from 'react';
import { Send, Loader2 } from 'lucide-react';
import { useAIAsk } from '../hooks';
import { ChatMessage, type ChatMessageData } from '../components/ai/ChatMessage';
import { SuggestedQuestions } from '../components/ai/SuggestedQuestions';

const MAX_QUESTION_LENGTH = 500;

export default function AIAssistant() {
  const [messages, setMessages] = useState<ChatMessageData[]>([]);
  const [input, setInput] = useState('');
  const [validationError, setValidationError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const { mutate: askQuestion, isPending } = useAIAsk();

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

    const userMessage: ChatMessageData = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: trimmed,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');

    askQuestion(
      { question: trimmed },
      {
        onSuccess: (response) => {
          const assistantMessage: ChatMessageData = {
            id: `assistant-${Date.now()}`,
            role: 'assistant',
            content: response.answer,
          };
          setMessages((prev) => [...prev, assistantMessage]);
        },
        onError: (error) => {
          const errorMessage: ChatMessageData = {
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

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      {/* Header */}
      <div className="flex-shrink-0 px-6 py-4 border-b border-gray-200">
        <h1 className="text-2xl font-semibold text-gray-900">AI Assistant</h1>
        <p className="text-sm text-gray-500 mt-1">
          Ask questions about your technology transformation portfolio
        </p>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <SuggestedQuestions onSelectQuestion={handleSelectQuestion} />
          </div>
        ) : (
          <div className="space-y-4 max-w-3xl mx-auto">
            {messages.map((message) => (
              <ChatMessage key={message.id} message={message} />
            ))}
            {isPending && (
              <div className="flex items-center gap-2 text-sm text-gray-500" role="status" aria-live="polite">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Processing your question...</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input area */}
      <div className="flex-shrink-0 border-t border-gray-200 px-6 py-4 bg-white">
        <div className="max-w-3xl mx-auto">
          {validationError && (
            <p className="text-sm text-red-600 mb-2" role="alert">
              {validationError}
            </p>
          )}
          <div className="flex items-center gap-2">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question about your portfolio..."
              disabled={isPending}
              maxLength={MAX_QUESTION_LENGTH + 50}
              className="flex-1 px-4 py-2.5 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
              aria-label="Ask a question"
              aria-invalid={!!validationError}
              aria-describedby={validationError ? 'validation-error' : undefined}
            />
            <button
              type="button"
              onClick={() => handleSubmit()}
              disabled={isPending}
              className="flex items-center justify-center w-10 h-10 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              aria-label="Send question"
            >
              {isPending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
            </button>
          </div>
          <p className="mt-1.5 text-xs text-gray-400">
            {input.trim().length}/{MAX_QUESTION_LENGTH} characters
          </p>
        </div>
      </div>
    </div>
  );
}
