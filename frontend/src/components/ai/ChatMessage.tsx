import { Bot, User } from 'lucide-react';

export interface ChatMessageData {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}

interface ChatMessageProps {
  message: ChatMessageData;
}

/**
 * ChatMessage — renders a user or assistant message bubble.
 * User messages appear on the right with blue styling.
 * Assistant messages appear on the left with gray styling.
 */
export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';

  return (
    <div
      className={`flex items-start gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
      aria-label={`${isUser ? 'Your' : 'Assistant'} message`}
    >
      <div
        className={`flex-shrink-0 flex items-center justify-center w-8 h-8 rounded-full ${
          isUser ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700'
        }`}
      >
        {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
      </div>
      <div
        className={`max-w-[75%] rounded-lg px-4 py-3 text-sm leading-relaxed ${
          isUser
            ? 'bg-blue-600 text-white rounded-br-none'
            : 'bg-gray-100 text-gray-800 rounded-bl-none'
        }`}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>
      </div>
    </div>
  );
}
