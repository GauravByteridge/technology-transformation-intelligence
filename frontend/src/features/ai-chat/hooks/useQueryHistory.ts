import { useMemo } from 'react';
import { useChatSessionStore } from '../stores/chatSessionStore';
import type { QueryHistoryEntry } from '@/types';

/**
 * Provides session-based query history derived from chat conversations.
 * Returns history entries sorted by timestamp descending (most recent first)
 * and a helper to retrieve entries for a specific conversation.
 *
 * This is in-memory only — no backend persistence.
 */
export function useQueryHistory(): {
  history: QueryHistoryEntry[];
  getConversationEntries: (conversationId: string) => QueryHistoryEntry[];
} {
  const conversations = useChatSessionStore((state) => state.conversations);

  const history = useMemo<QueryHistoryEntry[]>(() => {
    const entries: QueryHistoryEntry[] = [];

    for (const conversation of conversations) {
      for (const message of conversation.messages) {
        if (message.role === 'user') {
          entries.push({
            question: message.content,
            timestamp: message.timestamp,
            conversation_id: conversation.id,
          });
        }
      }
    }

    // Sort descending by timestamp (most recent first)
    entries.sort(
      (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    );

    return entries;
  }, [conversations]);

  const getConversationEntries = useMemo(() => {
    // Pre-group entries by conversation_id for efficient lookup
    const grouped = new Map<string, QueryHistoryEntry[]>();

    for (const entry of history) {
      const existing = grouped.get(entry.conversation_id);
      if (existing) {
        existing.push(entry);
      } else {
        grouped.set(entry.conversation_id, [entry]);
      }
    }

    return (conversationId: string): QueryHistoryEntry[] => {
      return grouped.get(conversationId) ?? [];
    };
  }, [history]);

  return { history, getConversationEntries };
}
