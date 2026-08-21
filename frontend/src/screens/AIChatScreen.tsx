import { useState, useRef, useEffect } from 'react';
import { sendChatMessage } from '../api/client';
import type { ChatMessage } from '../types';

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column' as const,
    height: 'calc(100vh - 120px)',
    maxWidth: '800px',
    margin: '0 auto',
    padding: '1rem',
  },
  header: {
    marginBottom: '1rem',
  },
  title: {
    fontSize: '1.5rem',
    fontWeight: 600,
    margin: 0,
  },
  messageList: {
    flex: 1,
    overflowY: 'auto' as const,
    padding: '1rem 0',
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '1rem',
  },
  emptyState: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100%',
    color: '#6b7280',
    fontSize: '0.95rem',
  },
  messageBubble: {
    maxWidth: '80%',
    padding: '0.75rem 1rem',
    borderRadius: '0.75rem',
    lineHeight: 1.5,
    fontSize: '0.95rem',
  },
  userMessage: {
    alignSelf: 'flex-end' as const,
    backgroundColor: '#2563eb',
    color: '#ffffff',
  },
  assistantMessage: {
    alignSelf: 'flex-start' as const,
    backgroundColor: '#f3f4f6',
    color: '#1f2937',
  },
  errorMessage: {
    alignSelf: 'flex-start' as const,
    backgroundColor: '#fef2f2',
    color: '#991b1b',
    border: '1px solid #fecaca',
  },
  sources: {
    marginTop: '0.5rem',
    paddingTop: '0.5rem',
    borderTop: '1px solid #e5e7eb',
  },
  sourcesLabel: {
    fontSize: '0.75rem',
    fontWeight: 600,
    color: '#6b7280',
    marginBottom: '0.25rem',
  },
  sourceItem: {
    fontSize: '0.8rem',
    color: '#4b5563',
    padding: '0.1rem 0',
  },
  timestamp: {
    fontSize: '0.7rem',
    color: '#9ca3af',
    marginTop: '0.25rem',
  },
  inputArea: {
    display: 'flex',
    gap: '0.5rem',
    padding: '1rem 0',
    borderTop: '1px solid #e5e7eb',
  },
  input: {
    flex: 1,
    padding: '0.75rem 1rem',
    border: '1px solid #d1d5db',
    borderRadius: '0.5rem',
    fontSize: '0.95rem',
    outline: 'none',
  },
  sendButton: {
    padding: '0.75rem 1.5rem',
    backgroundColor: '#2563eb',
    color: '#ffffff',
    border: 'none',
    borderRadius: '0.5rem',
    fontSize: '0.95rem',
    fontWeight: 500,
    cursor: 'pointer',
  },
  sendButtonDisabled: {
    backgroundColor: '#93c5fd',
    cursor: 'not-allowed',
  },
  loadingIndicator: {
    alignSelf: 'flex-start' as const,
    padding: '0.75rem 1rem',
    backgroundColor: '#f3f4f6',
    borderRadius: '0.75rem',
    color: '#6b7280',
    fontSize: '0.9rem',
    fontStyle: 'italic' as const,
  },
};

export default function AIChatScreen() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const messageListRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (messageListRef.current) {
      messageListRef.current.scrollTop = messageListRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    const trimmed = inputText.trim();
    if (!trimmed || isLoading) return;

    // Add user message to history
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: trimmed,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputText('');
    setIsLoading(true);

    try {
      const assistantMessage = await sendChatMessage(trimmed);
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error: unknown) {
      // Determine error message based on error type
      let errorContent = 'An unexpected error occurred. Please try again.';

      if (error && typeof error === 'object' && 'response' in error) {
        const axiosError = error as { response?: { status?: number; data?: { detail?: string } } };
        const status = axiosError.response?.status;
        const detail = axiosError.response?.data?.detail;

        if (status === 503) {
          errorContent = 'The AI service is currently unavailable. Please try again later.';
        } else if (status === 404 || (detail && detail.toLowerCase().includes('no relevant'))) {
          errorContent = 'No relevant information was found in the project data. Try uploading more files or rephrasing your question.';
        } else if (detail) {
          errorContent = detail;
        }
      } else if (error instanceof Error) {
        if (error.message.includes('Network Error') || error.message.includes('ERR_NETWORK')) {
          errorContent = 'Unable to reach the server. Please check your connection and try again.';
        }
      }

      const errorMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: errorContent,
        timestamp: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  }

  function formatTimestamp(isoString: string): string {
    return new Date(isoString).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h1 style={styles.title}>AI Chat</h1>
      </div>

      <div ref={messageListRef} style={styles.messageList} aria-live="polite" aria-label="Chat messages">
        {messages.length === 0 && !isLoading && (
          <div style={styles.emptyState}>
            Ask a question about your project data to get started.
          </div>
        )}

        {messages.map((msg) => {
          const isError =
            msg.role === 'assistant' &&
            (msg.content.includes('unavailable') ||
              msg.content.includes('error') ||
              msg.content.includes('Unable to reach') ||
              msg.content.includes('No relevant information'));

          const bubbleStyle = {
            ...styles.messageBubble,
            ...(msg.role === 'user'
              ? styles.userMessage
              : isError
                ? styles.errorMessage
                : styles.assistantMessage),
          };

          return (
            <div key={msg.id} style={bubbleStyle}>
              <div>{msg.content}</div>

              {msg.role === 'assistant' && msg.sources && msg.sources.length > 0 && (
                <div style={styles.sources}>
                  <div style={styles.sourcesLabel}>Sources:</div>
                  {msg.sources.map((source, idx) => (
                    <div key={idx} style={styles.sourceItem}>
                      • {source}
                    </div>
                  ))}
                </div>
              )}

              <div style={styles.timestamp}>{formatTimestamp(msg.timestamp)}</div>
            </div>
          );
        })}

        {isLoading && (
          <div style={styles.loadingIndicator} aria-label="Loading response">
            Thinking...
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} style={styles.inputArea}>
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder="Ask a question about your project data..."
          style={styles.input}
          disabled={isLoading}
          aria-label="Chat input"
        />
        <button
          type="submit"
          disabled={isLoading || !inputText.trim()}
          style={{
            ...styles.sendButton,
            ...(isLoading || !inputText.trim() ? styles.sendButtonDisabled : {}),
          }}
          aria-label="Send message"
        >
          Send
        </button>
      </form>
    </div>
  );
}
