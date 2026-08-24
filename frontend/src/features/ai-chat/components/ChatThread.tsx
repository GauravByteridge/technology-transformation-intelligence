import { useEffect, useRef } from 'react';
import type { ChatMessage } from '@/types';
import { MessageBubble } from './MessageBubble';

interface ChatThreadProps {
  messages: ChatMessage[];
}

/**
 * ChatThread — Renders message bubbles in conversation order.
 * Auto-scrolls to the bottom when new messages arrive.
 * Shows an empty state when no messages exist.
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
        <MessageBubble key={message.id} message={message} />
      ))}
      <div ref={bottomRef} aria-hidden="true" />
    </div>
  );
}
