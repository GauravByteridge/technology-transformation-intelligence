import type { ChatMessage } from '@/types';

interface MessageBubbleProps {
  message: ChatMessage;
}

/**
 * MessageBubble — Individual message display with role-based styling.
 * User messages are right-aligned with blue background.
 * Assistant messages are left-aligned with gray background.
 * Messages starting with "Error:" render in a warning/red style.
 */
export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const isError = message.content.startsWith('Error:');

  const formattedTime = formatTimestamp(message.timestamp);

  const bubbleStyles = getBubbleStyles(isUser, isError);
  const alignmentStyles = isUser ? 'ml-auto' : 'mr-auto';

  return (
    <div
      className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
      role="listitem"
      aria-label={`${isUser ? 'You' : 'Assistant'} said`}
    >
      <div className={`max-w-[75%] rounded-lg px-4 py-2.5 ${alignmentStyles} ${bubbleStyles}`}>
        <p className="whitespace-pre-wrap text-sm leading-relaxed">
          {message.content}
        </p>
        <time
          dateTime={message.timestamp}
          className={`mt-1 block text-xs ${isUser ? 'text-blue-200' : isError ? 'text-red-400' : 'text-gray-400'}`}
        >
          {formattedTime}
        </time>
      </div>
    </div>
  );
}

function getBubbleStyles(isUser: boolean, isError: boolean): string {
  if (isError) {
    return 'bg-red-50 border border-red-200 text-red-800';
  }
  if (isUser) {
    return 'bg-blue-600 text-white';
  }
  return 'bg-gray-100 text-gray-900 border border-gray-200';
}

function formatTimestamp(timestamp: string): string {
  try {
    const date = new Date(timestamp);
    return date.toLocaleTimeString(undefined, {
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return '';
  }
}
