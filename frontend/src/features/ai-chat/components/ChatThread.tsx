import { useEffect, useRef } from 'react';
import type { ChatMessage } from '@/types';
import { MessageBubble } from './MessageBubble';
import { VisualizationRenderer } from './VisualizationRenderer';

interface ChatThreadProps {
  messages: ChatMessage[];
}

/**
 * ChatThread — Renders message bubbles with inline charts when available.
 */
export function ChatThread({ messages }: ChatThreadProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length]);

  if (messages.length === 0) {
    return (
      <div
        className="flex flex-1 items-center justify-center p-8 text-center"
        role="status"
        aria-label="No messages yet"
      >
        <div className="max-w-sm">
          <p className="text-lg font-medium text-gray-600">No messages yet</p>
          <p className="mt-1 text-sm text-gray-400">
            Ask a question to get started with the AI assistant.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      className="flex-1 space-y-3 overflow-y-auto p-4"
      role="list"
      aria-label="Chat messages"
    >
      {messages.map((message) => (
        <div key={message.id}>
          <MessageBubble message={message} />
          {message.visualizationSpec && message.responseType === 'chart' && (
            <div className="mt-2 max-w-lg">
              <VisualizationRenderer
                responseType="chart"
                visualizationSpec={message.visualizationSpec}
                isPartial={false}
                failedSources={[]}
              />
            </div>
          )}
        </div>
      ))}
      <div ref={bottomRef} aria-hidden="true" />
    </div>
  );
}
