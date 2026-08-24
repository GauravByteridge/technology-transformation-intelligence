import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { sendChatMessage } from '../api/client';
import type { ChatMessage } from '../types';

const SUGGESTED_QUESTIONS = [
  'Which project has the highest budget?',
  'Show me all uploaded files',
  'What is the total project cost?',
  'List all audit findings',
  'What are the key risks in the portfolio?',
  'Summarize the executive report',
];

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

  async function handleSubmit(e?: React.FormEvent) {
    e?.preventDefault();
    const trimmed = inputText.trim();
    if (!trimmed || isLoading) return;
    await sendQuestion(trimmed);
  }

  async function sendQuestion(question: string) {
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: question,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputText('');
    setIsLoading(true);

    try {
      const assistantMessage = await sendChatMessage(question);
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error: unknown) {
      let errorContent = 'An unexpected error occurred. Please try again.';

      if (error && typeof error === 'object' && 'response' in error) {
        const axiosError = error as { response?: { status?: number; data?: { detail?: string } } };
        const status = axiosError.response?.status;
        const detail = axiosError.response?.data?.detail;

        if (status === 503) {
          errorContent = 'The AI service is currently unavailable. Please try again later.';
        } else if (status === 404 || (detail && detail.toLowerCase().includes('no relevant'))) {
          errorContent = 'No relevant information was found. Try uploading more files or rephrasing your question.';
        } else if (detail) {
          errorContent = detail;
        }
      } else if (error instanceof Error) {
        if (error.message.includes('Network Error') || error.message.includes('ERR_NETWORK')) {
          errorContent = 'Unable to reach the server. Please check your connection.';
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

  function handleSuggestedQuestion(question: string) {
    if (isLoading) return;
    setInputText(question);
    sendQuestion(question);
  }

  const hasMessages = messages.length > 0;

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <div style={styles.headerIcon}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
        </div>
        <div>
          <h1 style={styles.title}>AI Chat</h1>
          <p style={styles.subtitle}>
            Ask natural language questions to uncover insights, review trends, and analyze your project data.
          </p>
        </div>
      </div>

      {/* Chat Input Area - Always at top */}
      <div style={styles.inputSection}>
        <form onSubmit={handleSubmit} style={styles.inputForm}>
          <div style={styles.inputWrapper}>
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="Ask your question..."
              style={styles.input}
              disabled={isLoading}
            />
            <div style={styles.inputActions}>
              <button
                type="submit"
                disabled={isLoading || !inputText.trim()}
                style={{
                  ...styles.sendButton,
                  opacity: isLoading || !inputText.trim() ? 0.5 : 1,
                }}
                title="Send"
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" />
                </svg>
              </button>
            </div>
          </div>
        </form>
        <p style={styles.disclaimer}>Always review the accuracy of responses.</p>
      </div>

      {/* Messages or Suggested Questions */}
      {hasMessages ? (
        <div ref={messageListRef} style={styles.messageList}>
          {messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))}
          {isLoading && (
            <div style={styles.loadingMessage}>
              <div style={styles.loadingDots}>
                <span style={styles.dot} />
                <span style={{ ...styles.dot, animationDelay: '0.2s' }} />
                <span style={{ ...styles.dot, animationDelay: '0.4s' }} />
              </div>
              <span style={styles.loadingText}>Analyzing your data...</span>
            </div>
          )}
        </div>
      ) : (
        <div style={styles.suggestionsSection}>
          <h3 style={styles.suggestionsTitle}>Suggested Questions</h3>
          <div style={styles.suggestionsList}>
            {SUGGESTED_QUESTIONS.map((question, idx) => (
              <button
                key={idx}
                onClick={() => handleSuggestedQuestion(question)}
                style={styles.suggestionButton}
                disabled={isLoading}
              >
                {question}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user';
  const isError = !isUser && (
    message.content.includes('unavailable') ||
    message.content.includes('error') ||
    message.content.includes('Unable') ||
    message.content.includes('No relevant')
  );

  return (
    <div style={{ ...styles.messageBubble, ...(isUser ? styles.userBubble : styles.assistantBubble) }}>
      {!isUser && (
        <div style={styles.messageHeader}>
          <span style={styles.assistantIcon}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <path d="M12 16v-4M12 8h.01" />
            </svg>
          </span>
          <span style={styles.assistantLabel}>AI Assistant</span>
        </div>
      )}
      <div style={{ ...(isError ? styles.errorContent : {}) }}>
        {isUser ? (
          <p style={styles.userText}>{message.content}</p>
        ) : (
          <div style={styles.markdownContent}>
            <ReactMarkdown
              components={{
                h3: ({ children }) => <h3 style={styles.mdH3}>{children}</h3>,
                h4: ({ children }) => <h4 style={styles.mdH4}>{children}</h4>,
                p: ({ children }) => <p style={styles.mdP}>{children}</p>,
                ul: ({ children }) => <ul style={styles.mdUl}>{children}</ul>,
                ol: ({ children }) => <ol style={styles.mdOl}>{children}</ol>,
                li: ({ children }) => <li style={styles.mdLi}>{children}</li>,
                strong: ({ children }) => <strong style={styles.mdStrong}>{children}</strong>,
                code: ({ children }) => <code style={styles.mdCode}>{children}</code>,
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        )}
      </div>
      {message.sources && message.sources.length > 0 && (
        <div style={styles.sources}>
          <span style={styles.sourcesLabel}>Sources:</span>
          {message.sources.map((source, idx) => (
            <span key={idx} style={styles.sourceTag}>{source}</span>
          ))}
        </div>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100vh',
    backgroundColor: '#0f172a',
    color: '#e2e8f0',
  },
  header: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '1rem',
    padding: '1.5rem 2rem',
    borderBottom: '1px solid #1e293b',
  },
  headerIcon: {
    fontSize: '2rem',
    width: '48px',
    height: '48px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#1e3a8a',
    borderRadius: '12px',
  },
  title: {
    margin: 0,
    fontSize: '1.5rem',
    fontWeight: 600,
    color: '#f8fafc',
  },
  subtitle: {
    margin: '0.25rem 0 0 0',
    fontSize: '0.875rem',
    color: '#94a3b8',
  },
  inputSection: {
    padding: '1.5rem 2rem',
    borderBottom: '1px solid #1e293b',
  },
  inputForm: {
    width: '100%',
  },
  inputWrapper: {
    display: 'flex',
    alignItems: 'center',
    backgroundColor: '#1e293b',
    borderRadius: '12px',
    border: '1px solid #334155',
    padding: '0.5rem 1rem',
    gap: '0.75rem',
  },
  input: {
    flex: 1,
    backgroundColor: 'transparent',
    border: 'none',
    outline: 'none',
    fontSize: '0.95rem',
    color: '#f8fafc',
    padding: '0.5rem 0',
  },
  inputActions: {
    display: 'flex',
    gap: '0.5rem',
  },
  sendButton: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '36px',
    height: '36px',
    backgroundColor: '#3b82f6',
    border: 'none',
    borderRadius: '8px',
    color: '#ffffff',
    cursor: 'pointer',
    transition: 'background-color 0.15s',
  },
  disclaimer: {
    margin: '0.75rem 0 0 0',
    fontSize: '0.75rem',
    color: '#64748b',
    textAlign: 'center',
  },
  messageList: {
    flex: 1,
    overflowY: 'auto',
    padding: '1.5rem 2rem',
    display: 'flex',
    flexDirection: 'column',
    gap: '1rem',
  },
  messageBubble: {
    maxWidth: '85%',
    padding: '1rem 1.25rem',
    borderRadius: '12px',
  },
  userBubble: {
    alignSelf: 'flex-end',
    backgroundColor: '#1e40af',
    color: '#ffffff',
  },
  assistantBubble: {
    alignSelf: 'flex-start',
    backgroundColor: '#1e293b',
    border: '1px solid #334155',
  },
  messageHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    marginBottom: '0.75rem',
  },
  assistantIcon: {
    fontSize: '1rem',
  },
  assistantLabel: {
    fontSize: '0.8rem',
    fontWeight: 600,
    color: '#94a3b8',
  },
  userText: {
    margin: 0,
    lineHeight: 1.5,
  },
  markdownContent: {
    lineHeight: 1.6,
  },
  errorContent: {
    color: '#fca5a5',
  },
  sources: {
    marginTop: '1rem',
    paddingTop: '0.75rem',
    borderTop: '1px solid #334155',
    display: 'flex',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: '0.5rem',
  },
  sourcesLabel: {
    fontSize: '0.75rem',
    color: '#64748b',
    fontWeight: 600,
  },
  sourceTag: {
    fontSize: '0.7rem',
    backgroundColor: '#0f172a',
    color: '#94a3b8',
    padding: '0.25rem 0.5rem',
    borderRadius: '4px',
    border: '1px solid #334155',
  },
  loadingMessage: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
    padding: '1rem',
    backgroundColor: '#1e293b',
    borderRadius: '12px',
    border: '1px solid #334155',
    alignSelf: 'flex-start',
  },
  loadingDots: {
    display: 'flex',
    gap: '4px',
  },
  dot: {
    width: '8px',
    height: '8px',
    backgroundColor: '#3b82f6',
    borderRadius: '50%',
    animation: 'bounce 1s infinite',
  },
  loadingText: {
    fontSize: '0.875rem',
    color: '#94a3b8',
  },
  suggestionsSection: {
    flex: 1,
    padding: '2rem',
    overflowY: 'auto',
  },
  suggestionsTitle: {
    margin: '0 0 1rem 0',
    fontSize: '0.875rem',
    fontWeight: 600,
    color: '#64748b',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  suggestionsList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.5rem',
  },
  suggestionButton: {
    textAlign: 'left',
    padding: '0.875rem 1rem',
    backgroundColor: 'transparent',
    border: '1px solid #1e293b',
    borderRadius: '8px',
    color: '#e2e8f0',
    fontSize: '0.9rem',
    cursor: 'pointer',
    transition: 'all 0.15s',
  },
  // Markdown styles
  mdH3: {
    fontSize: '1.1rem',
    fontWeight: 600,
    marginTop: '1rem',
    marginBottom: '0.5rem',
    color: '#f8fafc',
  },
  mdH4: {
    fontSize: '1rem',
    fontWeight: 600,
    marginTop: '0.75rem',
    marginBottom: '0.375rem',
    color: '#f8fafc',
  },
  mdP: {
    margin: '0.5rem 0',
    color: '#e2e8f0',
  },
  mdUl: {
    margin: '0.5rem 0',
    paddingLeft: '1.5rem',
  },
  mdOl: {
    margin: '0.5rem 0',
    paddingLeft: '1.5rem',
  },
  mdLi: {
    marginBottom: '0.25rem',
    color: '#e2e8f0',
  },
  mdStrong: {
    fontWeight: 600,
    color: '#f8fafc',
  },
  mdCode: {
    backgroundColor: '#0f172a',
    padding: '0.125rem 0.375rem',
    borderRadius: '4px',
    fontSize: '0.85em',
    color: '#93c5fd',
  },
};
